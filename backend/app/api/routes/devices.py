import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, DeviceForUser, RequireOwner
from app.api.review_gate import needs_review, park
from app.models import DeviceOrientation, Playlist, ReviewKind
from app.config import get_settings
from app.schemas.devices import (
    ClaimRequest,
    DeviceLiveWrite,
    DeviceRead,
    DeviceResolutionRead,
    DeviceUpdate,
    DeviceUpdateVersionWrite,
    PairPollResponse,
    PairStartRequest,
    PairStartResponse,
    ProbeResponse,
)
from app.services import devices as device_service
from app.services import scheduling
from app.services.devices import (
    InvalidPlaylist,
    InvalidTimezone,
    NotAnAndroidScreen,
    PairingNotFound,
    SceneNotOnScreen,
    ScreenLimitReached,
    TooManyClaimAttempts,
)
from app.services.player_rollouts import UnknownRelease

router = APIRouter(tags=["devices"])


def _read(device) -> DeviceRead:
    read = DeviceRead.model_validate(device, from_attributes=True)
    # A hold that has run out reads as no hold — the same answer the manifest gives.
    if device_service.effective_live_slot_id(device) is None:
        read.live_slot_id = None
        read.live_started_at = None
    return read


# --- Device-side pairing (unauthenticated) ----------------------------------------------


@router.post("/devices/pair", response_model=PairStartResponse, status_code=status.HTTP_201_CREATED)
def start_pairing(session: DbSession, body: PairStartRequest | None = None) -> PairStartResponse:
    """Called by a screen on first boot. Deliberately unauthenticated — the device has no
    credential yet, and this is how it gets one. The body only says which player is asking;
    the Android player sends none."""
    body = body or PairStartRequest()
    device = device_service.start_pairing(
        session, platform=body.platform, detected_orientation=body.detected_orientation
    )
    return PairStartResponse(
        device_id=device.id,
        pairing_code=device.pairing_code,
        poll_token=device.poll_token,
        expires_at=device.pairing_expires_at,
        poll_seconds=5,
    )


@router.get("/devices/pair/{poll_token}", response_model=PairPollResponse)
def poll_pairing(
    poll_token: str, session: DbSession, detected_orientation: DeviceOrientation | None = None
) -> PairPollResponse:
    """Polled by the screen every few seconds until a human claims it.

    The token comes back exactly once; a second call with the same poll token is a 404,
    because the poll token is destroyed when the plaintext is handed over.
    """
    try:
        device, token, mqtt_password = device_service.poll_pairing(
            session, poll_token=poll_token, detected_orientation=detected_orientation
        )
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
    except ScreenLimitReached as exc:
        # 409, like every other "the account's state won't allow this" answer. Said in plain
        # words with the number in it, since this is what the person pairing actually reads.
        if exc.limit == 0:
            detail = "This account isn't allowed to add screens yet. Ask us for a screen limit."
        else:
            plural = "" if exc.limit == 1 else "s"
            detail = (
                f"This account can have {exc.limit} screen{plural} and is using all of them. "
                "Remove a screen first, or ask us for a higher limit."
            )
        raise HTTPException(status.HTTP_409_CONFLICT, detail) from None
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
):
    if (body.playlist_id is not None or body.clear_playlist) and needs_review(user):
        # Name, location and the rest apply now; what the screen plays waits for the owner.
        device_service.update(
            session, user=user, device=device, name=body.name, location=body.location,
            orientation=body.orientation, timezone=body.timezone,
        )
        playlist = session.get(Playlist, body.playlist_id) if body.playlist_id else None
        if body.playlist_id and (playlist is None or playlist.account_id != user.account_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Playlist not found")
        # What it plays now, kept on the review as Before.
        previous = session.get(Playlist, device.playlist_id) if device.playlist_id else None
        summary = (
            f"Screen “{device.name}”: play “{playlist.name}”" if playlist
            else f"Screen “{device.name}”: play nothing"
        )
        return park(
            session, user=user, kind=ReviewKind.DEVICE_PLAYLIST, target_id=device.id,
            target_name=device.name, summary=summary, screens=[device.name], screen_ids=[device.id],
            before={
                "playlist_id": str(previous.id) if previous else None,
                "playlist_name": previous.name if previous else None,
            },
            playlists=[playlist.name] if playlist else [],
            payload={"playlist_id": str(body.playlist_id) if body.playlist_id else None,
                     "clear_playlist": body.clear_playlist},
        )
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
        updated = device_service.set_forced_update(
            session, device=device, version=body.version, scheduled_at=body.scheduled_at,
        )
    except UnknownRelease:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "That version hasn't been uploaded to R2"
        ) from None
    except NotAnAndroidScreen:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Web screens update themselves when the web player is redeployed"
        ) from None
    return _read(updated)


@router.delete("/devices/{device_id}/update", response_model=DeviceRead)
def cancel_device_update(device: DeviceForUser, user: RequireOwner, session: DbSession) -> DeviceRead:
    """Cancel a single-device update before the screen has picked it up. Owner-only, same
    reasoning as set_device_update above."""
    updated = device_service.clear_forced_update(session, device=device)
    return _read(updated)


@router.put("/devices/{device_id}/live", response_model=DeviceRead)
def set_live(body: DeviceLiveWrite, device: DeviceForUser, session: DbSession) -> DeviceRead:
    """Live control: hold this screen on one scene of the playlist it is playing. Picking
    another scene moves the hold. Anyone who can see the screen may drive it — a hold is
    temporary and ends by itself (services/devices.py LIVE_MAX_SECONDS), so it is not the
    kind of screen-changing save the review gate parks for an owner."""
    try:
        updated = device_service.set_live(session, device=device, slot_id=body.slot_id)
    except SceneNotOnScreen:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "That scene isn't in the playlist this screen is playing right now. Reload the page.",
        ) from None
    return _read(updated)


@router.delete("/devices/{device_id}/live", response_model=DeviceRead)
def end_live(device: DeviceForUser, session: DbSession) -> DeviceRead:
    """Back to the programme."""
    return _read(device_service.end_live(session, device=device))


@router.post("/devices/{device_id}/probe", response_model=ProbeResponse)
def probe_device(device: DeviceForUser, session: DbSession) -> ProbeResponse:
    """Ask a screen to check in right now — see services/devices.py::probe. The frontend
    polls GET /devices/{id} afterward and watches last_seen_at for confirmation; this only
    hands back the baseline to watch for."""
    result = device_service.probe(session, device=device)
    return ProbeResponse(
        probed_at=result.probed_at, previous_last_seen_at=result.previous_last_seen_at,
    )


@router.post("/devices/{device_id}/disconnect", response_model=DeviceRead)
def disconnect_device(device: DeviceForUser, session: DbSession) -> DeviceRead:
    """Tell a screen it is being disconnected, and let it reset itself — the counterpart of
    pairing's handshake. The frontend then polls GET /devices/{id}: 200 while the screen is
    still being told, 404 once it has heard (the row is deleted with that answer — see
    deps.py::get_current_device). A screen that never checks in is removed with DELETE below
    after a grace period, and re-pairs by itself whenever it next connects."""
    return _read(device_service.request_disconnect(session, device=device))


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device: DeviceForUser, session: DbSession) -> None:
    """Remove a screen without waiting for it to hear — the fallback when a disconnect handshake
    times out on a screen that is offline. Its token stops working; it re-pairs when it next
    connects."""
    device_service.remove(session, device=device)
