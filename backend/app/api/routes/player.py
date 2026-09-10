"""Public download of the latest player APK.

Deliberately unauthenticated: the whole point is that it can be opened straight from a fresh
signage device's own browser, before that device has any pairing code, account, or credential
at all — the same "sideload it yourself" model the release APK already assumes (signed with
the debug key, no Play Store). This hands out the binary, nothing account-scoped; a screen
still needs a pairing code minted inside the authenticated CMS to actually join a fleet.
"""

import html as html_lib

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.config import get_settings
from app.infra import storage
from app.services import player_releases, player_rollouts

router = APIRouter(tags=["player"])

# docs/ is a separate static site (its own Railway service, no build step, no templating) —
# it always links the one production API regardless of where docs itself is served from, and
# this page returns the favour: it links docs' own stylesheet so a backend-rendered page
# reads as part of the same site. Stylesheet <link>s aren't subject to CORS, unlike fetch(),
# which is why this page is rendered here rather than fetched as JSON from a static page.
DOCS_ORIGIN = "https://docs-production-9a3e.up.railway.app"


@router.get("/player/download")
def download_latest_apk(session: DbSession) -> RedirectResponse:
    """Redirects to a fresh presigned URL for whichever build is currently active — see
    `services/player_rollouts.py::active_rollout`.

    A redirect rather than streaming the file through this process — R2 serves the bytes
    directly, and the presigned URL is generated fresh on every hit rather than cached, so it
    is never stale past its own short TTL.
    """
    rollout = player_rollouts.active_rollout(session)
    if rollout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No player build has been published yet")
    settings = get_settings()
    url = storage.presign_get(rollout.apk_key, settings.device_presign_ttl_seconds)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/player/download/{version}")
def download_apk_version(version: str) -> RedirectResponse:
    """Same as `/player/download`, for a specific past build — every version
    `publish_player_apk.py` has ever uploaded stays in R2, this just serves it by name."""
    release = player_releases.find_release(version)
    if release is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No build published for version {version}")
    settings = get_settings()
    url = storage.presign_get(release.key, settings.device_presign_ttl_seconds)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


def _format_size(size_bytes: int) -> str:
    return f"{size_bytes / 1_048_576:.1f} MB"


def _format_date(iso: str) -> str:
    # "2026-03-05T09:12:00+00:00" → "5 Mar 2026". Trimmed by hand rather than pulled through
    # `datetime.fromisoformat` + strftime for one field — not worth the import for this.
    from datetime import datetime
    return datetime.fromisoformat(iso).strftime("%-d %b %Y")


def _render_versions_page(releases: list[player_releases.PlayerRelease]) -> str:
    if releases:
        rows = "\n".join(
            f"""<tr>
              <td>{html_lib.escape(r.version)}{' <span style="color:var(--color-ink-subtle);font-weight:400;">· current</span>' if r.is_current else ''}</td>
              <td>{_format_date(r.uploaded_at)}</td>
              <td>{_format_size(r.size_bytes)}</td>
              <td><a class="btn" style="padding:6px 14px;font-size:13px;" href="/player/download/{html_lib.escape(r.version)}" download>Download</a></td>
            </tr>"""
            for r in releases
        )
        table = f"""<div class="table-wrap">
          <table class="fact-table">
            <thead><tr><th>Version</th><th>Published</th><th>Size</th><th></th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""
    else:
        table = '<p class="lede">No player build has been published yet.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Player APK Versions — Fortu CMS Docs</title>
  <link rel="stylesheet" href="{DOCS_ORIGIN}/style.css" />
</head>
<body>
  <div class="page" style="max-width: 820px;">
    <a href="{DOCS_ORIGIN}/connecting-a-screen.html"
       style="font-size:13px;color:var(--color-ink-muted);text-decoration:none;">
      &larr; Connecting a Screen
    </a>
    <div class="hero" style="margin-top: 20px;">
      <div class="eyebrow"><b>FORTU</b>&nbsp;PLAYER</div>
      <h1>APK versions</h1>
      <p class="dek">
        Every build ever published, not just the current one — for rolling a screen back to
        a known-good version, or confirming what's actually out there on the wall.
      </p>
    </div>
    <section style="margin-top: 40px;">{table}</section>
    <footer>
      <span>Fortu CMS</span>
      <span>Newest first. "current" is whatever every screen is being pushed right now.</span>
    </footer>
  </div>
</body>
</html>"""


@router.get("/player/versions", response_class=HTMLResponse)
def list_player_versions(session: DbSession) -> HTMLResponse:
    """Every build `publish_player_apk.py` has ever uploaded, not just the one `/player/
    download` currently redirects to — for rolling a screen back, or just seeing the history.

    Rendered here rather than as JSON fetched from a static docs page: docs/ has no build
    step and no JS, and a cross-origin fetch would need CORS wired up in production for no
    real benefit — a plain link works today with nothing to misconfigure.
    """
    rollout = player_rollouts.active_rollout(session)
    current_key = rollout.apk_key if rollout else None
    return HTMLResponse(_render_versions_page(player_releases.list_releases(current_key=current_key)))
