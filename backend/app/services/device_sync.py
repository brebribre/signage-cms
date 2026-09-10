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
from datetime import datetime

from sqlmodel import Session, select

from app.config import get_settings
from app.models import Device, ItemFit, Media, MediaKind, Playlist, PlaylistItem
from app.models.base import utcnow
from app.infra import storage
from app.services import media as media_service
from app.services import scheduling

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


def compute_version(session: Session, device: Device, now: datetime | None = None) -> str:
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
    # `now` is injectable purely so the schedule-dependent parts of this hash can be tested
    # at a chosen moment. Time-dependent behaviour asserted against the real clock passes or
    # fails depending on when the suite runs, which is worse than not testing it.
    resolution = scheduling.resolve(session, device, now)
    resolved_id = resolution.playlist_id

    if resolved_id is None:
        payload: object = ("none", device.orientation.value)
    else:
        playlist = session.get(Playlist, resolved_id)
        rows = _enabled_items(session, resolved_id)
        payload = (
            str(resolved_id),
            device.orientation.value,
            playlist.shuffle if playlist else False,
            [
                (str(item.id), media.checksum, item.duration_seconds, item.position, item.fit.value)
                for item, media in rows
            ],
        )
    canonical = json.dumps(
        (
            payload,
            str(resolution.schedule_id) if resolution.schedule_id else None,
            # The window boundary is part of the content, not metadata about it. Without it,
            # editing a schedule that is not *currently* active would leave every screen
            # holding a stale `valid_until` — they would wake at the old boundary, and a
            # boundary moved earlier would simply be missed. Including it means any change to
            # when the answer expires is itself a change the device must pick up.
            resolution.valid_until.isoformat() if resolution.valid_until else None,
        ),
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ManifestItem:
    id: uuid.UUID
    media_id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    duration_seconds: int
    fit: ItemFit
    has_audio: bool


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
    #: Name of the schedule currently overriding the default, or None when the device is
    #: playing its default playlist. Surfaced so the debug overlay can answer "why is this
    #: showing?" without anyone opening the CMS.
    schedule_name: str | None = None
    #: When the current answer expires. The device re-polls then rather than waiting for its
    #: next 30s tick, so a daypart boundary is hit on time instead of up to 30s late.
    valid_until: str | None = None


def build_manifest(session: Session, device: Device, *, version: str) -> Manifest:
    """The full payload — only built once a version mismatch says the device actually needs
    it. Presigning N item URLs is cheap (a local HMAC each) but there is no reason to pay it
    on every 30-second poll when nothing has changed; `compute_version` alone answers that."""
    settings = get_settings()
    resolution = scheduling.resolve(session, device)
    valid_until = resolution.valid_until.isoformat() if resolution.valid_until else None

    if resolution.playlist_id is None:
        return Manifest(
            version=version,
            device_name=device.name,
            device_orientation=device.orientation.value,
            playlist=None,
            items=[],
            schedule_name=resolution.schedule_name,
            valid_until=valid_until,
        )

    playlist = session.get(Playlist, resolution.playlist_id)
    rows = _enabled_items(session, resolution.playlist_id)
    items = [
        ManifestItem(
            id=item.id,
            media_id=media.id,
            kind=media.kind,
            # 6 hours, not the CMS's shorter preview TTL: a screen may be pulling a large
            # file over bad venue wifi. The checksum — not this URL — is the device's cache
            # key, so a re-issued URL for unchanged content is never treated as a re-download.
            url=media_service.view_url(media, ttl=settings.device_presign_ttl_seconds),
            checksum=media.checksum,
            bytes=media.size_bytes,
            duration_seconds=item.duration_seconds,
            fit=item.fit,
            has_audio=item.has_audio,
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
        schedule_name=resolution.schedule_name,
        valid_until=valid_until,
    )


@dataclass
class AvailableUpdate:
    version: str
    url: str


def available_update(device: Device) -> AvailableUpdate | None:
    """An APK this screen should install, or None.

    Offered whenever the device's reported version differs from the configured one — **not
    only when it is older**. That makes a deliberate rollback possible by simply pointing
    `PLAYER_LATEST_VERSION` at an earlier build, which matters more for signage than
    preventing downgrades: if a release breaks playback on a wall of screens, the fix has to
    be a config change, not a field visit to every one of them.

    Returns None when updates are unconfigured, which is the default. A blank
    `player_latest_version` cannot accidentally push anything.
    """
    settings = get_settings()
    if not settings.player_latest_version or not settings.player_apk_key:
        return None
    # A device that has never reported its version gets nothing: without knowing what it is
    # running we cannot tell whether an update is needed, and pushing blind risks an install
    # loop on every heartbeat.
    if not device.app_version:
        return None
    if device.app_version == settings.player_latest_version:
        return None

    return AvailableUpdate(
        version=settings.player_latest_version,
        # The same long TTL as media: an APK is a large file over the same bad venue wifi.
        url=storage.presign_get(settings.player_apk_key, settings.device_presign_ttl_seconds),
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

    # Persisted now, not just logged. Logging alone is fine while someone is watching a
    # terminal during setup and useless a week later, which is exactly when a health page has
    # to answer "what went wrong on that screen".
    if errors:
        from app.models import EventLevel
        from app.services import operations

        for message in errors[: operations.MAX_EVENTS_PER_HEARTBEAT]:
            operations.record_event(
                session, device=device, level=EventLevel.ERROR, message=message, commit=False
            )
        session.commit()
        logger.warning(
            "device %s (%s) reported %d error(s): %s",
            device.id, device.name, len(errors), "; ".join(errors[:5]),
        )
    if current_item_id is not None:
        logger.debug("device %s heartbeat, current item %s", device.id, current_item_id)
