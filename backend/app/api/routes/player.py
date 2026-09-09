"""Public download of the latest player APK.

Deliberately unauthenticated: the whole point is that it can be opened straight from a fresh
signage device's own browser, before that device has any pairing code, account, or credential
at all — the same "sideload it yourself" model the release APK already assumes (signed with
the debug key, no Play Store). This hands out the binary, nothing account-scoped; a screen
still needs a pairing code minted inside the authenticated CMS to actually join a fleet.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.infra import storage

router = APIRouter(tags=["player"])


@router.get("/player/download")
def download_latest_apk() -> RedirectResponse:
    """Redirects to a fresh presigned URL for whatever `publish_player_apk.py` last uploaded.

    A redirect rather than streaming the file through this process — R2 serves the bytes
    directly, and the presigned URL is generated fresh on every hit rather than cached, so it
    is never stale past its own short TTL.
    """
    settings = get_settings()
    if not settings.player_latest_version or not settings.player_apk_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No player build has been published yet")
    url = storage.presign_get(settings.player_apk_key, settings.device_presign_ttl_seconds)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)
