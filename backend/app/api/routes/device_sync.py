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
    ManifestItem,
    ManifestPlaylist,
    ManifestResponse,
)
from app.services import device_sync

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
        device=ManifestDevice(name=manifest.device_name, orientation=manifest.device_orientation),
        playlist=ManifestPlaylist(**manifest.playlist.__dict__) if manifest.playlist else None,
        items=[ManifestItem(**item.__dict__) for item in manifest.items],
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
    )
    return HeartbeatResponse(version=device_sync.compute_version(session, device))
