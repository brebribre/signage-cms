"""Public download of the latest player APK.

Deliberately unauthenticated: the whole point is that it can be opened straight from a fresh
signage device's own browser, before that device has any pairing code, account, or credential
at all — the same "sideload it yourself" model the release APK already assumes (signed with
the debug key, no Play Store). This hands out the binary, nothing account-scoped; a screen
still needs a pairing code minted inside the authenticated CMS to actually join a fleet.
"""

import html as html_lib

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api.deps import DbSession
from app.config import get_settings
from app.infra import storage
from app.services import player_releases, player_rollouts

router = APIRouter(tags=["player"])

# The docs site (GitHub Pages, brebribre/paskall-docs) lists releases on its own page by
# fetching the JSON below; this backend-rendered page is the no-JavaScript fallback and the
# place the "Download latest" button lands people who want an older build.
DOCS_RELEASES_URL = "https://docs.marien.co.id/player-releases/"


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
              <td><b>{html_lib.escape(r.version)}</b>{' <span class="muted">· current</span>' if r.is_current else ''}</td>
              <td>{_format_date(r.uploaded_at)}</td>
              <td>{_format_size(r.size_bytes)}</td>
              <td><a class="btn" href="/player/download/{html_lib.escape(r.version)}" download>Download</a></td>
            </tr>"""
            for r in releases
        )
        table = f"""<table>
            <thead><tr><th>Version</th><th>Published</th><th>Size</th><th></th></tr></thead>
            <tbody>{rows}</tbody>
          </table>"""
    else:
        table = '<p class="muted">No player build has been published yet.</p>'

    # Self-contained: no stylesheet to fetch, so this reads the same wherever it is opened —
    # including a signage box's own browser with nothing else reachable.
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Marien Player releases</title>
  <style>
    body {{ margin: 0; background: #f1f3f7; color: #101111; font: 15px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; }}
    .page {{ max-width: 820px; margin: 0 auto; padding: 40px 20px 60px; }}
    a {{ color: #003399; }}
    h1 {{ font-size: 28px; margin: 24px 0 8px; }}
    .muted {{ color: #7d7d7d; font-weight: 400; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; margin-top: 28px; }}
    th, td {{ text-align: left; padding: 12px 16px; border-bottom: 1px solid #e5e5e5; }}
    th {{ font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #7d7d7d; font-weight: 500; }}
    .btn {{ display: inline-block; padding: 6px 14px; border-radius: 999px; background: #003399; color: #fff; text-decoration: none; font-size: 13px; }}
    footer {{ margin-top: 32px; font-size: 13px; color: #7d7d7d; }}
  </style>
</head>
<body>
  <div class="page">
    <a href="{DOCS_RELEASES_URL}" style="font-size:13px;text-decoration:none;">&larr; Marien Docs</a>
    <h1>Marien Player releases</h1>
    <p class="muted">Every build ever published, newest first. "current" is the one every screen is being given right now.</p>
    {table}
    <footer>Install the APK on the screen, open it, and connect it with the code it shows.</footer>
  </div>
</body>
</html>"""


@router.get("/player/versions.json")
def list_player_versions_json(session: DbSession) -> JSONResponse:
    """The same list as JSON, for the docs site's own releases page (GitHub Pages, a different
    origin) — hence the explicit allow-any-origin header: this is public data that
    `/player/versions` already shows to anyone, and download links are plain GETs."""
    rollout = player_rollouts.active_rollout(session)
    current_key = rollout.apk_key if rollout else None
    releases = player_releases.list_releases(current_key=current_key)
    return JSONResponse(
        [
            {
                "version": r.version,
                "published_at": r.uploaded_at,
                "size_bytes": r.size_bytes,
                "is_current": r.is_current,
                "download_url": f"/player/download/{r.version}",
            }
            for r in releases
        ],
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"},
    )


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
