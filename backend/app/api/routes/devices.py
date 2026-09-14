import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, DeviceForUser, RequireOwner
from app.config import get_settings
from app.schemas.devices import (
    ClaimRequest,
    DeviceRead,
    DeviceResolutionRead,
    DeviceUpdate,
    DeviceUpdateVersionWrite,
    PairPollResponse,
    PairStartResponse,
    ProbeResponse,
)
from app.services import devices as device_service
from app.services import scheduling
from app.services.devices import (
    InvalidPlaylist,
    InvalidTimezone,
    PairingNotFound,
    TooManyClaimAttempts,
)
from app.services.player_rollouts import UnknownRelease

router = APIRouter(tags=["devices"])


def _read(device) -> DeviceRead:
    return DeviceRead.model_validate(device, from_attributes=True)


# --- Device-side pairing (unauthenticated) ----------------------------------------------


@router.post("/devices/pair", response_model=PairStartResponse, status_code=status.HTTP_201_CREATED)
def start_pairing(session: DbSession) -> PairStartResponse:
    """Called by a screen on first boot. Deliberately unauthenticated — the device has no
    credential yet, and this is how it gets one."""
    device = device_service.start_pairing(session)
    return PairStartResponse(
        device_id=device.id,
        pairing_code=device.pairing_code,
        poll_token=device.poll_token,
        expires_at=device.pairing_expires_at,
        poll_seconds=5,
    )


@router.get("/devices/pair/{poll_token}", response_model=PairPollResponse)
def poll_pairing(poll_token: str, session: DbSession) -> PairPollResponse:
    """Polled by the screen every few seconds until a human claims it.

    The token comes back exactly once; a second call with the same poll token is a 404,
    because the poll token is destroyed when the plaintext is handed over.
    """
    try:
        device, token, mqtt_password = device_service.poll_pairing(session, poll_token=poll_token)
    except PairingNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or expired pairing") from None

    if token is None:
        return PairPollResponse(claimed=False, device_id=device.id)
    return PairPollResponse(
        claimed=True, device_id=device.id, device_token=token,
        mqtt_password=mqtt_password, name=device.name
    )


# --- CMS-side management (session cookie) -----------------------------------------------


@router.post("/devices/claim", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def claim_device(body: ClaimRequest, user: CurrentUser, session: DbSession) -> DeviceRead:
    """A human types the code shown on the screen."""
    try:
        device = device_service.claim(
            session,
            user=user,
            pairing_code=body.pairing_code,
            name=body.name,
            location=body.location,
        )
    except TooManyClaimAttempts:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts — wait a minute and retry"
        ) from None
    except PairingNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No screen is waiting with that code. Codes expire after "
            f"{get_settings().pairing_code_ttl_seconds // 60} minutes.",
        ) from None
    return _read(device)


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(user: CurrentUser, session: DbSession) -> list[DeviceRead]:
    """Screens this user may reach. Unclaimed devices belong to nobody and appear for no one."""
    return [_read(d) for d in device_service.list_devices(session, user=user)]


@router.get("/devices/resolved", response_model=list[DeviceResolutionRead])
def resolved_devices(user: CurrentUser, session: DbSession) -> list[DeviceResolutionRead]:
    """What every reachable device is playing right now — one resolve() per device, done here
    so the device list can show it without N round trips. Read-only counterpart to Campaign,
    which is the only place that can change it. Declared ahead of `/devices/{device_id}` so
    it can never be shadowed by it."""
    import datetime as dt

    out: list[DeviceResolutionRead] = []
    for device in device_service.list_devices(session, user=user):
        resolution = scheduling.resolve(session, device)
        zone = scheduling.device_zone(device)
        out.append(DeviceResolutionRead(
            device_id=device.id,
            playlist_id=resolution.playlist_id,
            schedule_id=resolution.schedule_id,
            schedule_name=resolution.schedule_name,
            campaign_id=resolution.campaign_id,
            valid_until=resolution.valid_until,
            timezone=str(zone),
            device_local_time=dt.datetime.now(dt.UTC).astimezone(zone),
        ))
    return out


@router.get("/devices/{device_id}", response_model=DeviceRead)
def get_device(device: DeviceForUser) -> DeviceRead:
    return _read(device)


@router.patch("/devices/{device_id}", response_model=DeviceRead)
def update_device(
    body: DeviceUpdate, device: DeviceForUser, user: CurrentUser, session: DbSession
) -> DeviceRead:
    try:
        updated = device_service.update(
            session,
            user=user,
            device=device,
            name=body.name,
            location=body.location,
            orientation=body.orientation,
            timezone=body.timezone,
            playlist_id=body.playlist_id,
            clear_playlist=body.clear_playlist,
        )
    except InvalidPlaylist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Playlist not found") from None
    except InvalidTimezone as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown timezone: {exc}"
        ) from None
    return _read(updated)


@router.post("/devices/{device_id}/update", response_model=DeviceRead)
def set_device_update(
    body: DeviceUpdateVersionWrite, device: DeviceForUser, user: RequireOwner, session: DbSession
) -> DeviceRead:
    """Pin this one screen to a specific build, independent of the fleet rollout — for trying
    a release on a single device first, or nudging a straggler, without touching anyone else.
    Owner-only, same as the rest of player build management (routes/player_rollouts.py) —
    kept consistent with that existing, deliberate boundary rather than loosened as a side
    effect of adding this. See services/devices.py::set_forced_update."""
    try:
        updated = device_service.set_forced_update(session, device=device, version=body.version)
    except UnknownRelease:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "That version hasn't been uploaded to R2"
        ) from None
    return _read(updated)


@router.delete("/devices/{device_id}/update", response_model=DeviceRead)
def cancel_device_update(device: DeviceForUser, user: RequireOwner, session: DbSession) -> DeviceRead:
    """Cancel a single-device update before the screen has picked it up. Owner-only, same
    reasoning as set_device_update above."""
    updated = device_service.clear_forced_update(session, device=device)
    return _read(updated)


@router.post("/devices/{device_id}/unpair", response_model=PairStartResponse)
def unpair_device(device: DeviceForUser, session: DbSession) -> PairStartResponse:
    """Revoke the token and put the screen back on a pairing code.

    Keeps the row, its name and its playlist, so re-pairing the same hardware is not a
    fresh setup.
    """
    updated = device_service.unpair(session, device=device)
    return PairStartResponse(
        device_id=updated.id,
        pairing_code=updated.pairing_code,
        poll_token=updated.poll_token,
        expires_at=updated.pairing_expires_at,
        poll_seconds=5,
    )


@router.post("/devices/{device_id}/probe", response_model=ProbeResponse)
def probe_device(device: DeviceForUser, session: DbSession) -> ProbeResponse:
    """Ask a screen to check in right now — see services/devices.py::probe. The frontend
    polls GET /devices/{id} afterward and watches last_seen_at for confirmation; this only
    hands back the baseline to watch for."""
    result = device_service.probe(session, device=device)
    return ProbeResponse(
        probed_at=result.probed_at, previous_last_seen_at=result.previous_last_seen_at,
    )


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device: DeviceForUser, session: DbSession) -> None:
    device_service.remove(session, device=device)
