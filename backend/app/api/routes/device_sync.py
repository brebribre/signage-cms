"""The device runtime's own routes — `/device/...`, singular, device-token authenticated.

Deliberately a different prefix from `/devices` (plural, session-cookie authenticated,
Phase 8/9). The two must never be reachable with the other's credential, and a shared prefix
would make that boundary easy to blur by accident later.
"""

from fastapi import APIRouter, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.deps import CurrentDevice, DbSession
from app.schemas.device_sync import (
    HeartbeatRequest,
    HeartbeatResponse,
    ManifestDevice,
    ManifestElement,
    ManifestItem,
    ManifestPlaylist,
    ManifestResponse,
    ManifestSlot,
    UpdateInfo,
    UpdateStatusReport,
)
from app.services import device_sync, operations

router = APIRouter(prefix="/device", tags=["device-sync"])


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    """RFC 7232: the header may carry several comma-separated values, or `*`."""
    if not if_none_match:
        return False
    candidates = [c.strip().strip('"') for c in if_none_match.split(",")]
    return "*" in candidates or etag in candidates


@router.get(
    "/manifest",
    # Declared here rather than as `response_model=`, because this route returns raw
    # Response objects (a 304 must carry no body, which response_model cannot express).
    # Without this the manifest — the single most important contract the player depends on —
    # would be entirely absent from /openapi.json and /docs.
    responses={
        200: {"model": ManifestResponse, "description": "The current playlist for this screen."},
        304: {"description": "Content unchanged since the ETag supplied in If-None-Match."},
        401: {"description": "Missing or invalid device token."},
    },
)
def get_manifest(device: CurrentDevice, session: DbSession, request: Request) -> Response:
    """Everything a screen needs to play, and nothing else.

    The version is computed first, unconditionally — that alone answers whether anything
    needs to change. The expensive part (presigning every item's URL) only happens once that
    says yes, so a screen polling every 30s with nothing new costs one hash comparison.
    """
    version = device_sync.compute_version(session, device)
    etag = f'"{version}"'

    if _etag_matches(request.headers.get("if-none-match"), version):
        # A 304 must carry no body — returning the Pydantic model here would violate that,
        # which is why this route builds Response objects by hand instead of using
        # `response_model`.
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

    manifest = device_sync.build_manifest(session, device, version=version)
    body = ManifestResponse(
        version=manifest.version,
        device=ManifestDevice(
            name=manifest.device_name,
            orientation=manifest.device_orientation,
            timezone=manifest.device_timezone,
        ),
        playlist=ManifestPlaylist(**manifest.playlist.__dict__) if manifest.playlist else None,
        # Flattened to the one-element-per-slot shape the player actually deserializes — see
        # `ManifestItem`'s docstring. A slot with no elements has nothing to play and is
        # dropped rather than sent as an empty/broken item.
        items=[
            ManifestItem(
                id=slot.id,
                media_id=slot.elements[0].media_id,
                kind=slot.elements[0].kind,
                url=slot.elements[0].url,
                checksum=slot.elements[0].checksum,
                bytes=slot.elements[0].bytes,
                duration_seconds=slot.duration_seconds,
                fit=slot.elements[0].fit,
                has_audio=slot.elements[0].has_audio,
            )
            for slot in manifest.slots
            # A website can't be flattened into this file-only shape — the players that read
            # it would try to download the page as media.
            if slot.elements and slot.elements[0].kind != "web"
        ],
        # The real, unflattened shape — see `ManifestResponse.slots`'s own docstring for why
        # this rides alongside `items` rather than replacing it.
        slots=[
            ManifestSlot(
                id=slot.id,
                duration_seconds=slot.duration_seconds,
                elements=[
                    ManifestElement(
                        id=el.id,
                        media_id=el.media_id,
                        kind=el.kind,
                        url=el.url,
                        checksum=el.checksum,
                        bytes=el.bytes,
                        z_index=el.z_index,
                        x=el.x,
                        y=el.y,
                        width=el.width,
                        height=el.height,
                        fit=el.fit,
                        has_audio=el.has_audio,
                        rotation_degrees=el.rotation_degrees,
                        crop_x=el.crop_x,
                        crop_y=el.crop_y,
                        crop_zoom=el.crop_zoom,
                        stream_url=el.stream_url,
                        stream_bytes=el.stream_bytes,
                        stream_checksum=el.stream_checksum,
                        stream_mime=el.stream_mime,
                        poster_url=el.poster_url,
                    )
                    for el in slot.elements
                ],
                background=slot.background,
            )
            for slot in manifest.slots
            if slot.elements
        ],
        schedule_name=manifest.schedule_name,
        valid_until=manifest.valid_until,
        settings=manifest.settings,
    )
    return JSONResponse(content=jsonable_encoder(body.model_dump(mode="json")), headers={"ETag": etag})


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(body: HeartbeatRequest, device: CurrentDevice, session: DbSession) -> HeartbeatResponse:
    device_sync.record_heartbeat(
        session,
        device=device,
        app_version=body.app_version,
        screen_width=body.screen.width if body.screen else None,
        screen_height=body.screen.height if body.screen else None,
        current_item_id=body.current_item_id,
        errors=body.errors,
        reported_settings=body.reported_settings,
    )

    if body.plays:
        operations.record_plays(
            session,
            device=device,
            plays=[(p.media_id, p.filename, p.started_at, p.seconds) for p in body.plays],
        )
    update = device_sync.available_update(session, device)
    return HeartbeatResponse(
        version=device_sync.compute_version(session, device),
        update=(
            UpdateInfo(
                version=update.version,
                url=update.url,
                bytes=update.bytes,
                requested_at=update.requested_at,
            )
            if update
            else None
        ),
    )


@router.post("/update-status", status_code=status.HTTP_204_NO_CONTENT)
def update_status(body: UpdateStatusReport, device: CurrentDevice, session: DbSession) -> Response:
    """How the install of a player build is going, in the screen's own words — posted every
    few seconds while it downloads, once when it hands the APK to the installer, and with the
    reason if anything goes wrong. Its own route rather than a field on the heartbeat: a
    heartbeat's response carries the update offer, and a progress report must never be able
    to trigger a second install of the thing it is reporting on."""
    device_sync.record_update_status(
        session,
        device=device,
        version=body.version,
        state=body.state,
        progress_pct=body.progress_pct,
        detail=body.detail,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
