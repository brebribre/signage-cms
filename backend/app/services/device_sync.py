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
from app.models import SceneBackground, Device, DevicePlatform, DeviceUpdateState, EventLevel, ItemFit, Media, MediaKind, Playlist, PlaylistItem, PlaylistItemElement
from app.models.base import utcnow
from app.infra import storage
from app.services import device_settings
from app.services import media as media_service
from app.services import player_releases
from app.services import player_rollouts
from app.services import scheduling
from app.schemas.device_sync import PlaybackReport

logger = logging.getLogger(__name__)


def web_checksum(url: str) -> str:
    """A website element's stand-in for a file checksum. The device keys everything on
    checksums, and the manifest version hashes them, so this must change exactly when the
    address does. Prefixed so it can never collide with a real file's sha256."""
    return "web-" + hashlib.sha256(url.encode()).hexdigest()


def text_checksum(text: str, style: dict | None) -> str:
    """The same for a text element: changes exactly when the words or their look do."""
    payload = json.dumps({"text": text, "style": style or {}}, sort_keys=True)
    return "text-" + hashlib.sha256(payload.encode()).hexdigest()


def element_checksum(el: PlaylistItemElement, media: Media | None) -> str:
    if media:
        return media_service.playback_checksum(media)
    if el.text is not None:
        return text_checksum(el.text, el.text_style)
    return web_checksum(el.web_url or "")


def _enabled_items(
    session: Session, playlist_id: uuid.UUID
) -> list[tuple[PlaylistItem, list[tuple[PlaylistItemElement, Media | None]]]]:
    """Playable slots only, in play order, each with its elements (media joined in — None for
    a website — paint order). A disabled item is not paused — it does not exist as far as a
    screen is concerned."""
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
        .outerjoin(Media, Media.id == PlaylistItemElement.media_id)
        .where(PlaylistItemElement.playlist_item_id.in_(item_ids))
        .order_by(PlaylistItemElement.z_index)
    ).all()
    by_item: dict[uuid.UUID, list[tuple[PlaylistItemElement, Media | None]]] = {i.id: [] for i in items}
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
                    item.background.value,
                    item.background_color,
                    [
                        (
                            str(el.id),
                            # The playable copy's identity once it exists (services/
                            # video_streams.py) — its arrival is what makes a screen fetch the
                            # smaller, normalised file in place of the original.
                            element_checksum(el, media),
                            # A video's streaming copy appearing (services/video_streams.py)
                            # changes what a web screen caches and plays.
                            media.stream_checksum if media else None,
                            el.z_index, el.x, el.y, el.width,
                            el.height, el.fit.value, el.crop_x, el.crop_y, el.crop_zoom,
                            el.has_audio, el.rotation_degrees,
                        )
                        for el, media in elements
                    ],
                )
                for item, elements in rows
            ],
        )
    # Live control: which scene the screen is being held on, if any. Deliberately read
    # through the same expiry every other reader uses, so a hold running out moves this hash
    # (and with it the screen, on its next check-in) exactly as ending it by hand would.
    from app.services.devices import effective_live_slot_id  # local: devices imports this module

    live_slot_id = effective_live_slot_id(device, now)
    canonical = json.dumps(
        (
            payload,
            str(live_slot_id) if live_slot_id else None,
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
    #: None for a website element.
    media_id: uuid.UUID | None
    #: A media kind ("image"/"video"), or "web" for a website shown live.
    kind: str
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
    crop_x: float | None = None
    crop_y: float | None = None
    crop_zoom: float | None = None
    #: The file's stored size — see schemas/device_sync.py. Not part of the version: it never
    #: changes for a given file, and a player falls back to the decoded size without it.
    media_width: int | None = None
    media_height: int | None = None
    stream_url: str | None = None
    stream_bytes: int | None = None
    stream_checksum: str | None = None
    stream_mime: str | None = None
    #: A video's thumbnail — what a blurred scene background shows for it (see
    #: models.playlist.SceneBackground). None for pictures, websites and videos without one.
    poster_url: str | None = None
    #: A text element's words and look (schemas/playlists.py TextStyle). None otherwise.
    text: str | None = None
    text_style: dict | None = None


@dataclass
class ManifestSlot:
    id: uuid.UUID
    duration_seconds: int
    elements: list[ManifestElement]
    background: str = "black"
    #: With background "color": the `#RRGGBB` to paint. None otherwise.
    background_color: str | None = None


@dataclass
class ManifestPlaylist:
    id: uuid.UUID
    name: str
    shuffle: bool


@dataclass
class Manifest:
    version: str
    device_name: str
    #: "portrait"/"landscape", for players that predate `device_rotation`.
    device_orientation: str
    device_rotation: int
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
    #: The screen's timezone — validated, so a bad name reaches the player as UTC, the same
    #: fallback scheduling.device_zone uses. The player evaluates its power schedule on it.
    device_timezone: str = "UTC"
    #: Live control (services/devices.py set_live): the one slot to show and hold, instead of
    #: looping. None — the usual case — means play the loop. Always one of `slots`' ids, or
    #: None: a hold on a scene that is no longer in the playlist is dropped here, not sent.
    live_slot_id: uuid.UUID | None = None


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
            device_orientation=device.orientation.legacy_name,
            device_rotation=device.orientation.degrees,
            device_timezone=scheduling.device_zone(device).key,
            playlist=None,
            slots=[],
            schedule_name=resolution.schedule_name,
            valid_until=valid_until,
            settings=device_settings_dict,
        )

    from app.services.devices import effective_live_slot_id  # local: devices imports this module

    playlist = session.get(Playlist, resolution.playlist_id)
    rows = _enabled_items(session, resolution.playlist_id)
    live_slot_id = effective_live_slot_id(device)
    if live_slot_id is not None and all(item.id != live_slot_id for item, _ in rows):
        live_slot_id = None
    slots = [
        ManifestSlot(
            id=item.id,
            duration_seconds=item.duration_seconds,
            elements=[
                ManifestElement(
                    id=el.id,
                    media_id=media.id if media else None,
                    kind=media.kind.value if media else ("text" if el.text is not None else "web"),
                    # 6 hours, not the CMS's shorter preview TTL: a screen may be pulling a
                    # large file over bad venue wifi. The checksum — not this URL — is the
                    # device's cache key, so a re-issued URL for unchanged content is never
                    # treated as a re-download. A website is its own address: nothing to
                    # download, loaded live.
                    # A web screen's video is its streaming copy both ways — stored, and as the
                    # network fallback — since that is the file made for what a TV browser
                    # decodes (see video_streams.STREAM_MAX_EDGE_PX); a fragmented MP4 plays
                    # fine as a plain file too. Android keeps the 4K playback copy.
                    url=(
                        storage.presign_get(
                            media.stream_key
                            if device.platform != DevicePlatform.ANDROID and media.kind == MediaKind.VIDEO and media.stream_key
                            else media_service.playback_key(media),
                            settings.device_presign_ttl_seconds,
                        )
                        if media
                        else (el.web_url or "")
                    ),
                    checksum=element_checksum(el, media),
                    text=el.text,
                    text_style=el.text_style,
                    bytes=media_service.playback_size_bytes(media) if media else 0,
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
                    media_width=media.width if media else None,
                    media_height=media.height if media else None,
                    stream_url=(
                        storage.presign_get(media.stream_key, settings.device_presign_ttl_seconds)
                        if media and media.stream_key
                        else None
                    ),
                    stream_bytes=media.stream_size_bytes if media and media.stream_key else None,
                    stream_checksum=media.stream_checksum if media and media.stream_key else None,
                    stream_mime=media.stream_mime if media and media.stream_key else None,
                    poster_url=(
                        storage.presign_get(media.thumbnail_key, settings.device_presign_ttl_seconds)
                        if media and media.kind == MediaKind.VIDEO and media.thumbnail_key
                        else None
                    ),
                )
                for el, media in elements
            ],
            background=item.background.value,
            background_color=item.background_color if item.background == SceneBackground.COLOR else None,
        )
        for item, elements in rows
    ]
    return Manifest(
        version=version,
        device_name=device.name,
        device_orientation=device.orientation.legacy_name,
        device_rotation=device.orientation.degrees,
        device_timezone=scheduling.device_zone(device).key,
        playlist=ManifestPlaylist(id=playlist.id, name=playlist.name, shuffle=playlist.shuffle)
        if playlist
        else None,
        slots=slots,
        schedule_name=resolution.schedule_name,
        valid_until=valid_until,
        settings=device_settings_dict,
        live_slot_id=live_slot_id,
    )


@dataclass
class AvailableUpdate:
    version: str
    url: str
    #: The APK's size — for a real download percentage on the screen, and for resuming.
    bytes: int | None = None
    #: When this offer was made; the player's failure backoff is keyed on it, so re-issuing an
    #: offer from the CMS is a fresh attempt. See `schemas.device_sync.UpdateInfo`.
    requested_at: datetime | None = None


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
    # A device that has never reported its version gets nothing either way: without knowing
    # what it is running we cannot tell whether an update is needed, and pushing blind risks
    # an install loop on every heartbeat.
    if not device.app_version:
        return None
    # A web screen runs whatever `web-player/` is deployed and reloads itself onto a new one;
    # there is no APK it could install.
    if device.platform != DevicePlatform.ANDROID:
        return None

    # A per-device forced update wins over the fleet rollout entirely, even onto a version the
    # fleet isn't (or is no longer) on — it exists specifically so one screen can be moved
    # independently of everyone else. Falls through to the fleet rollout below if the pinned
    # release has since vanished from R2, rather than leaving the screen stuck on nothing.
    # A pin scheduled for later waits — until then the screen follows the fleet like any other.
    if (
        device.forced_update_version
        and device.forced_update_version != device.app_version
        and (device.forced_update_at is None or device.forced_update_at <= utcnow())
    ):
        release = player_releases.find_release(device.forced_update_version)
        if release is not None:
            settings = get_settings()
            return AvailableUpdate(
                version=release.version,
                url=storage.presign_get(release.key, settings.device_presign_ttl_seconds),
                bytes=release.size_bytes,
                requested_at=device.forced_update_at,
            )

    rollout = player_rollouts.active_rollout(session)
    if rollout is None:
        return None
    if device.app_version == rollout.version:
        return None
    if _is_stale_rollout(rollout, running=device.app_version):
        return None

    settings = get_settings()
    # One HEAD per heartbeat that actually carries an offer — the common case (nothing to
    # install) returns above without touching R2. Worth it: the size is what turns "installing…"
    # into "43% of 18 MB" on both the screen and the CMS.
    release = player_releases.find_release(rollout.version)
    return AvailableUpdate(
        version=rollout.version,
        # The same long TTL as media: an APK is a large file over the same bad venue wifi.
        url=storage.presign_get(rollout.apk_key, settings.device_presign_ttl_seconds),
        bytes=release.size_bytes if release else None,
        requested_at=rollout.scheduled_at,
    )


def _is_stale_rollout(rollout, *, running: str) -> bool:
    """Whether the fleet rollout is simply older than what this screen already runs — as
    opposed to a deliberate rollback.

    The rule "offer whatever is live, even if older" exists so a rollback can be a rollout.
    But it also means a screen moved ahead of the fleet (a per-screen pin to a newer build,
    or a fresh install) is told to *downgrade* on every check-in for as long as nobody rolls
    the newer build out — Android refuses the downgrade, so the screen re-downloads and fails
    every ten minutes. The tell is time: a real rollback is scheduled *after* the newer build
    was published; a rollout that predates the newer build is just stale. Decided from the
    build's upload time in R2; a build R2 doesn't know (a dev install) can't be judged, and is
    offered the rollout as before."""
    release = player_releases.find_release(running)
    if release is None:
        return False
    uploaded_at = datetime.fromisoformat(release.uploaded_at)
    if rollout.scheduled_at >= uploaded_at:
        return False
    logger.info(
        "not offering rollout %s to a screen on %s: the rollout predates that build (a rollback "
        "would be scheduled after it)", rollout.version, running,
    )
    return True


# How long a "downloading"/"installing" report is trusted before the CMS treats it as stale.
# Longer than the player's own read timeout plus its in-attempt retries, so a screen that is
# genuinely still working is never called stuck; the player reports at least every few seconds
# while it is. Exposed for the frontend's own copy of this threshold to be checked against.
UPDATE_REPORT_STALE_SECONDS = 180


def record_update_status(
    session: Session,
    *,
    device: Device,
    version: str,
    state: DeviceUpdateState,
    progress_pct: int | None,
    detail: str | None,
) -> None:
    """The screen's own account of an install in progress — the whole reason the Screens page
    can now say "downloading, 43%" or "failed: not enough free space" instead of "pending".

    Counts as liveness too: the player's poll loop is blocked for the whole download, so
    without this the CMS would show a screen going amber precisely while it was doing what it
    was asked to. A failure is also written to the event log, so it survives being replaced by
    the next attempt's report and shows up under Errors & logs a week later.
    """
    now = utcnow()
    device.last_seen_at = now
    device.update_state = state
    device.update_version = version
    device.update_progress_pct = progress_pct
    device.update_detail = detail
    device.update_reported_at = now
    session.add(device)
    session.commit()

    if state == DeviceUpdateState.FAILED:
        from app.services import operations

        operations.record_event(
            session,
            device=device,
            level=EventLevel.ERROR,
            message=f"Update to {version} failed: {detail or 'no reason given'}",
        )
        logger.warning("device %s (%s) update to %s failed: %s", device.id, device.name, version, detail)


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
    playback: "PlaybackReport | None" = None,
    device_owner: bool | None = None,
) -> None:
    """Update liveness. Errors are logged, not stored — Phase 14 gives them a table if a
    device health page is ever built; until then they only need to be visible to whoever is
    watching the logs during setup."""
    now = utcnow()
    device.last_seen_at = now
    if app_version is not None:
        device.app_version = app_version
        # A one-shot pin, not a standing one — see Device.forced_update_version. Once the
        # screen confirms it's actually running the version that was pushed to it alone, it
        # goes back to following the fleet rollout like everything else, rather than silently
        # fighting every rollout after this one forever.
        if device.forced_update_version and device.forced_update_version == app_version:
            device.forced_update_version = None
            device.forced_update_at = None
        # Success is decided here, not reported: installing an update kills the process that
        # would report it. The first heartbeat from the new build is the proof — whether the
        # screen had got as far as reporting "installing", or the report never reached us.
        if device.update_version == app_version and device.update_state != DeviceUpdateState.INSTALLED:
            device.update_state = DeviceUpdateState.INSTALLED
            device.update_version = app_version
            device.update_progress_pct = 100
            device.update_detail = None
            device.update_reported_at = now
    if screen_width is not None:
        device.screen_width = screen_width
    if screen_height is not None:
        device.screen_height = screen_height
    if playback is not None:
        device.playback_dropped_frames = playback.dropped_frames
        device.playback_decoder = playback.decoder
        # Kept from the last measurable download rather than nulled on every quiet beat.
        if playback.download_bytes_per_second is not None:
            device.download_bytes_per_second = playback.download_bytes_per_second
        device.playback_reported_at = now
    if device_owner is not None:
        device.device_owner = device_owner
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
