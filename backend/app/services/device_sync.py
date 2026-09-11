"""The device runtime's contract: `GET /device/manifest` and `POST /device/heartbeat`.

Kept separate from `services/devices.py`, which is CMS-side management (pairing, claim,
rename). This module is the other half of the device story — what a paired screen actually
polls — and the two have almost no code in common.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlmodel import Session, select

from app.config import get_settings
from app.models import Device, ItemFit, Media, MediaKind, Playlist, PlaylistItem, PlaylistItemElement
from app.models.base import utcnow
from app.infra import storage
from app.services import device_settings
from app.services import media as media_service
from app.services import player_rollouts
from app.services import scheduling

logger = logging.getLogger(__name__)


def _enabled_items(
    session: Session, playlist_id: uuid.UUID
) -> list[tuple[PlaylistItem, list[tuple[PlaylistItemElement, Media]]]]:
    """Playable slots only, in play order, each with its elements (media joined in, paint
    order). A disabled item is not paused — it does not exist as far as a screen is
    concerned."""
    items = session.exec(
        select(PlaylistItem)
        .where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.is_enabled.is_(True))
        .order_by(PlaylistItem.position)
    ).all()
    if not items:
        return []
    item_ids = [i.id for i in items]
    element_rows = session.exec(
        select(PlaylistItemElement, Media)
        .join(Media, Media.id == PlaylistItemElement.media_id)
        .where(PlaylistItemElement.playlist_item_id.in_(item_ids))
        .order_by(PlaylistItemElement.z_index)
    ).all()
    by_item: dict[uuid.UUID, list[tuple[PlaylistItemElement, Media]]] = {i.id: [] for i in items}
    for element, media in element_rows:
        by_item[element.playlist_item_id].append((element, media))
    return [(item, by_item[item.id]) for item in items]


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
                (
                    str(item.id),
                    item.duration_seconds,
                    item.position,
                    [
                        (
                            str(el.id), media.checksum, el.z_index, el.x, el.y, el.width,
                            el.height, el.fit.value, el.crop_x, el.crop_y, el.crop_zoom,
                            el.has_audio, el.rotation_degrees,
                        )
                        for el, media in elements
                    ],
                )
                for item, elements in rows
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
            # Volume, brightness, and the rest of services/device_settings.py's registry: a
            # settings-only change is exactly as much "something the screen must pick up" as a
            # new playlist, so it has to move this hash the same way.
            device_settings.as_dict(session, device_id=device.id),
        ),
        # sort_keys, because the settings dict above is the only non-tuple/list value in this
        # payload — everything else already has a fixed field order for free.
        separators=(",", ":"), sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ManifestElement:
    id: uuid.UUID
    media_id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    z_index: int
    x: float
    y: float
    width: float
    height: float
    fit: ItemFit
    has_audio: bool
    rotation_degrees: int


@dataclass
class ManifestSlot:
    id: uuid.UUID
    duration_seconds: int
    elements: list[ManifestElement]


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
    slots: list[ManifestSlot]
    #: Name of the schedule currently overriding the default, or None when the device is
    #: playing its default playlist. Surfaced so the debug overlay can answer "why is this
    #: showing?" without anyone opening the CMS.
    schedule_name: str | None = None
    #: When the current answer expires. The device re-polls then rather than waiting for its
    #: next 30s tick, so a daypart boundary is hit on time instead of up to 30s late.
    valid_until: str | None = None
    #: Every remotely-configurable value currently set on this device — volume today, more by
    #: the same registry later (services/device_settings.py). A key absent here means "use the
    #: player's own default," not "set to nothing."
    settings: dict = field(default_factory=dict)


def build_manifest(session: Session, device: Device, *, version: str) -> Manifest:
    """The full payload — only built once a version mismatch says the device actually needs
    it. Presigning N element URLs is cheap (a local HMAC each) but there is no reason to pay
    it on every 30-second poll when nothing has changed; `compute_version` alone answers
    that."""
    settings = get_settings()
    resolution = scheduling.resolve(session, device)
    valid_until = resolution.valid_until.isoformat() if resolution.valid_until else None
    device_settings_dict = device_settings.as_dict(session, device_id=device.id)

    if resolution.playlist_id is None:
        return Manifest(
            version=version,
            device_name=device.name,
            device_orientation=device.orientation.value,
            playlist=None,
            slots=[],
            schedule_name=resolution.schedule_name,
            valid_until=valid_until,
            settings=device_settings_dict,
        )

    playlist = session.get(Playlist, resolution.playlist_id)
    rows = _enabled_items(session, resolution.playlist_id)
    slots = [
        ManifestSlot(
            id=item.id,
            duration_seconds=item.duration_seconds,
            elements=[
                ManifestElement(
                    id=el.id,
                    media_id=media.id,
                    kind=media.kind,
                    # 6 hours, not the CMS's shorter preview TTL: a screen may be pulling a
                    # large file over bad venue wifi. The checksum — not this URL — is the
                    # device's cache key, so a re-issued URL for unchanged content is never
                    # treated as a re-download.
                    url=media_service.view_url(media, ttl=settings.device_presign_ttl_seconds),
                    checksum=media.checksum,
                    bytes=media.size_bytes,
                    z_index=el.z_index,
                    x=el.x,
                    y=el.y,
                    width=el.width,
                    height=el.height,
                    fit=el.fit,
                    has_audio=el.has_audio,
                    rotation_degrees=el.rotation_degrees,
                )
                for el, media in elements
            ],
        )
        for item, elements in rows
    ]
    return Manifest(
        version=version,
        device_name=device.name,
        device_orientation=device.orientation.value,
        playlist=ManifestPlaylist(id=playlist.id, name=playlist.name, shuffle=playlist.shuffle)
        if playlist
        else None,
        slots=slots,
        schedule_name=resolution.schedule_name,
        valid_until=valid_until,
        settings=device_settings_dict,
    )


@dataclass
class AvailableUpdate:
    version: str
    url: str


def available_update(session: Session, device: Device) -> AvailableUpdate | None:
    """An APK this screen should install, or None.

    Offered whenever the device's reported version differs from the active rollout — **not
    only when it is older**. That makes a deliberate rollback possible by scheduling an
    earlier build as a new rollout, which matters more for signage than preventing
    downgrades: if a release breaks playback on a wall of screens, the fix has to be a CMS
    action, not a field visit to every one of them.

    Returns None when nothing has ever been rolled out, which is the default — an account
    with no `player_rollouts` row cannot accidentally push anything.
    """
    rollout = player_rollouts.active_rollout(session)
    if rollout is None:
        return None
    # A device that has never reported its version gets nothing: without knowing what it is
    # running we cannot tell whether an update is needed, and pushing blind risks an install
    # loop on every heartbeat.
    if not device.app_version:
        return None
    if device.app_version == rollout.version:
        return None

    settings = get_settings()
    return AvailableUpdate(
        version=rollout.version,
        # The same long TTL as media: an APK is a large file over the same bad venue wifi.
        url=storage.presign_get(rollout.apk_key, settings.device_presign_ttl_seconds),
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
    reported_settings: dict | None = None,
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

    if reported_settings:
        device_settings.record_reported(session, device=device, reported=reported_settings)

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
