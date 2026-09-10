import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, DeviceForUser
from app.config import get_settings
from app.schemas.devices import (
    BulkAssignPlaylistRequest,
    BulkAssignPlaylistResponse,
    ClaimRequest,
    DeviceRead,
    DeviceUpdate,
    PairPollResponse,
    PairStartResponse,
)
from app.services import devices as device_service
from app.services.devices import (
    InvalidPlaylist,
    InvalidTimezone,
    PairingNotFound,
    TooManyClaimAttempts,
)

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


@router.post("/devices/bulk-assign-playlist", response_model=BulkAssignPlaylistResponse)
def bulk_assign_playlist(
    body: BulkAssignPlaylistRequest, user: CurrentUser, session: DbSession
) -> BulkAssignPlaylistResponse:
    """Set (or clear) one playlist across many screens at once, instead of one PATCH per
    device. Declared ahead of `/devices/{device_id}` so it can never be shadowed by it."""
    try:
        updated, skipped_ids = device_service.bulk_assign_playlist(
            session,
            user=user,
            device_ids=body.device_ids,
            playlist_id=body.playlist_id,
            clear_playlist=body.clear_playlist,
        )
    except InvalidPlaylist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Playlist not found") from None
    return BulkAssignPlaylistResponse(
        updated=[_read(d) for d in updated], skipped_ids=skipped_ids
    )


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


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device: DeviceForUser, session: DbSession) -> None:
    device_service.remove(session, device=device)
