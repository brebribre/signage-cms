"""The device runtime's contract: `GET /device/manifest` and `POST /device/heartbeat`.

Kept separate from `services/devices.py`, which is CMS-side management (pairing, claim,
rename). This module is the other half of the device story — what a paired screen actually
polls — and the two have almost no code in common.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass

from sqlmodel import Session, select

from app.config import get_settings
from app.models import Device, ItemFit, Media, MediaKind, Playlist, PlaylistItem
from app.models.base import utcnow
from app.services import media as media_service

logger = logging.getLogger(__name__)


def _enabled_items(session: Session, playlist_id: uuid.UUID) -> list[tuple[PlaylistItem, Media]]:
    """Playable slots only, in play order. A disabled item is not paused — it does not exist
    as far as a screen is concerned."""
    rows = session.exec(
        select(PlaylistItem, Media)
        .join(Media, Media.id == PlaylistItem.media_id)
        .where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.is_enabled.is_(True))
        .order_by(PlaylistItem.position)
    ).all()
    return [(item, media) for item, media in rows]


def compute_version(session: Session, device: Device) -> str:
    """A hash of everything that changes what the screen should show — and nothing else.

    Deliberately excludes the device's own name and the playlist's name: renaming either is
    cosmetic and never changes what plays, so it must not force a redundant re-fetch. Nothing
    has to remember to bump this on every write path that touches content — it is recomputed
    from the current rows every time, so the class of bug where a screen silently keeps
    playing stale content after an edit cannot occur here.

    **Orientation is included, deliberately extending the plan's stated inputs.** A `304`
    carries no body, so if orientation were left out, changing it in the CMS would produce no
    visible effect until some other edit happened to bump the version for an unrelated
    reason. Orientation is a rendering instruction, not a label, so it belongs with content
    rather than with the cosmetic fields excluded above.
    """
    if device.playlist_id is None:
        payload: object = ("none", device.orientation.value)
    else:
        playlist = session.get(Playlist, device.playlist_id)
        rows = _enabled_items(session, device.playlist_id)
        payload = (
            str(device.playlist_id),
            device.orientation.value,
            playlist.shuffle if playlist else False,
            [
                (str(item.id), media.checksum, item.duration_seconds, item.position, item.fit.value)
                for item, media in rows
            ],
        )
    canonical = json.dumps(payload, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ManifestItem:
    id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    duration_seconds: int
    fit: ItemFit


@dataclass
class ManifestPlaylist:
    id: uuid.UUID
    name: str
    shuffle: bool


@dataclass
class Manifest:
    version: str
    device_name: str
    device_orientation: str
    playlist: ManifestPlaylist | None
    items: list[ManifestItem]


def build_manifest(session: Session, device: Device, *, version: str) -> Manifest:
    """The full payload — only built once a version mismatch says the device actually needs
    it. Presigning N item URLs is cheap (a local HMAC each) but there is no reason to pay it
    on every 30-second poll when nothing has changed; `compute_version` alone answers that."""
    settings = get_settings()

    if device.playlist_id is None:
        return Manifest(
            version=version,
            device_name=device.name,
            device_orientation=device.orientation.value,
            playlist=None,
            items=[],
        )

    playlist = session.get(Playlist, device.playlist_id)
    rows = _enabled_items(session, device.playlist_id)
    items = [
        ManifestItem(
            id=item.id,
            kind=media.kind,
            # 6 hours, not the CMS's shorter preview TTL: a screen may be pulling a large
            # file over bad venue wifi. The checksum — not this URL — is the device's cache
            # key, so a re-issued URL for unchanged content is never treated as a re-download.
            url=media_service.view_url(media, ttl=settings.device_presign_ttl_seconds),
            checksum=media.checksum,
            bytes=media.size_bytes,
            duration_seconds=item.duration_seconds,
            fit=item.fit,
        )
        for item, media in rows
    ]
    return Manifest(
        version=version,
        device_name=device.name,
        device_orientation=device.orientation.value,
        playlist=ManifestPlaylist(id=playlist.id, name=playlist.name, shuffle=playlist.shuffle)
        if playlist
        else None,
        items=items,
    )


def record_heartbeat(
    session: Session,
    *,
    device: Device,
    app_version: str | None,
    screen_width: int | None,
    screen_height: int | None,
    current_item_id: uuid.UUID | None,
    errors: list[str],
) -> None:
    """Update liveness. Errors are logged, not stored — Phase 14 gives them a table if a
    device health page is ever built; until then they only need to be visible to whoever is
    watching the logs during setup."""
    device.last_seen_at = utcnow()
    if app_version is not None:
        device.app_version = app_version
    if screen_width is not None:
        device.screen_width = screen_width
    if screen_height is not None:
        device.screen_height = screen_height
    session.add(device)
    session.commit()

    if errors:
        logger.warning(
            "device %s (%s) reported %d error(s): %s",
            device.id, device.name, len(errors), "; ".join(errors[:5]),
        )
    if current_item_id is not None:
        logger.debug("device %s heartbeat, current item %s", device.id, current_item_id)
