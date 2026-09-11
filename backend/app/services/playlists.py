"""Playlists: an ordered list of scenes, each a set of one or more positioned media elements
shown simultaneously."""

import uuid
from dataclasses import dataclass, field

from sqlmodel import Session, delete, func, select

from app.infra import storage
from app.models import (
    Device,
    ItemFit,
    Media,
    MediaKind,
    MediaStatus,
    Playlist,
    PlaylistItem,
    PlaylistItemElement,
    User,
    UserRole,
)
from app.models.base import utcnow
from app.services import device_sync
from app.services.errors import DomainError

# What an image shows for when nothing says otherwise. A lone video element defaults to its
# own length instead.
IMAGE_DEFAULT_SECONDS = 10
MIN_ITEM_SECONDS = 1
MAX_ITEM_SECONDS = 3600
# How far a crop can zoom in past the tightest "cover" fit before signage media (rarely
# shot at high resolution) starts looking visibly soft.
MAX_CROP_ZOOM = 3.0


@dataclass(frozen=True)
class ElementSpec:
    """One media element within a scene, as the client describes it."""

    media_id: uuid.UUID
    z_index: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    fit: ItemFit = ItemFit.COVER
    crop_x: float | None = None
    crop_y: float | None = None
    crop_zoom: float | None = None
    has_audio: bool = False
    rotation_degrees: int = 0


@dataclass(frozen=True)
class ItemSpec:
    """One slot (scene) as the client describes it. Position is deliberately absent — it is
    the index in the list, so the two can never disagree."""

    elements: list[ElementSpec] = field(default_factory=list)
    duration_seconds: int | None = None
    is_enabled: bool = True


class PlaylistNotFound(DomainError):
    pass


class InvalidItems(DomainError):
    pass


class PlaylistInUse(DomainError):
    def __init__(self, device_names: list[str]):
        self.device_names = device_names
        super().__init__(", ".join(device_names))


class NotYours(DomainError):
    pass


def _owned(session: Session, user: User, playlist_id: uuid.UUID) -> Playlist:
    playlist = session.get(Playlist, playlist_id)
    # 404, not 403, for another account's playlist: do not confirm that it exists.
    if playlist is None or playlist.account_id != user.account_id:
        raise PlaylistNotFound(str(playlist_id))
    return playlist


def create(session: Session, *, user: User, name: str) -> Playlist:
    playlist = Playlist(account_id=user.account_id, created_by=user.id, name=name.strip())
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    return playlist


#: Thumbnails shown per playlist on the list page — a preview, not the whole loop. Capped so
#: a playlist with hundreds of items doesn't presign hundreds of URLs just to render a strip
#: that scrolls into view maybe six wide; the detail page (one playlist at a time) has no
#: such cap because there's no N-playlists-at-once cost to bound.
MAX_PREVIEW_THUMBNAILS = 6


def list_playlists(
    session: Session, *, user: User
) -> list[tuple[Playlist, int, int, list[str | None]]]:
    """Every playlist in the account, with its **enabled** item count, total duration, and a
    capped strip of preview thumbnails (one per scene, in play order; `None` where that
    scene's media has none — a blank tile, not a skipped one, same as the detail page).

    Both the counts and the thumbnails are each fetched in one query across every playlist
    in the account, not per playlist — N+1 queries for a number (or a thumbnail) is exactly
    the kind of thing that is invisible at three playlists and painful at three hundred.
    """
    rows = session.exec(
        select(
            Playlist,
            func.count(PlaylistItem.id),
            func.coalesce(func.sum(PlaylistItem.duration_seconds), 0),
        )
        # `is_enabled` is filtered in the JOIN condition, not in a WHERE: with an outer join
        # a WHERE would drop playlists whose every item is disabled, instead of showing them
        # with zero. It must also match what the detail endpoint reports — a list saying
        # "3 items · 0:45" beside a detail saying "2 items · 0:35" is worse than either.
        .outerjoin(
            PlaylistItem,
            (PlaylistItem.playlist_id == Playlist.id) & (PlaylistItem.is_enabled.is_(True)),
        )
        .where(Playlist.account_id == user.account_id)
        .group_by(Playlist.id)
        .order_by(Playlist.updated_at.desc())
    ).all()

    playlist_ids = [p.id for p, _, _ in rows]
    thumb_keys_by_playlist: dict[uuid.UUID, list[str | None]] = {}
    if playlist_ids:
        # Every element of every enabled item, ordered so that within one scene its lowest
        # z_index (first-painted) element comes first, and scenes themselves come in play
        # order. "First row per item" has no portable SQL expression, so — same reasoning as
        # `_with_elements` above — it's a dict keyed by item id built in Python from rows
        # already in the right order, taking each item's first occurrence only.
        thumb_rows = session.exec(
            select(PlaylistItem.playlist_id, PlaylistItem.id, Media.thumbnail_key)
            .join(PlaylistItemElement, PlaylistItemElement.playlist_item_id == PlaylistItem.id)
            .join(Media, Media.id == PlaylistItemElement.media_id)
            .where(
                PlaylistItem.playlist_id.in_(playlist_ids),
                PlaylistItem.is_enabled.is_(True),
            )
            .order_by(PlaylistItem.playlist_id, PlaylistItem.position, PlaylistItemElement.z_index)
        ).all()
        seen_items: set[uuid.UUID] = set()
        for playlist_id, item_id, thumbnail_key in thumb_rows:
            if item_id in seen_items:
                continue
            seen_items.add(item_id)
            bucket = thumb_keys_by_playlist.setdefault(playlist_id, [])
            if len(bucket) < MAX_PREVIEW_THUMBNAILS:
                bucket.append(thumbnail_key)

    def _urls(keys: list[str | None]) -> list[str | None]:
        return [storage.presign_get(k) if k else None for k in keys]

    return [
        (p, int(count), int(total), _urls(thumb_keys_by_playlist.get(p.id, [])))
        for p, count, total in rows
    ]


# A scene's elements, media joined in, ordered for paint (z_index ascending — later draws
# on top).
SceneRows = list[tuple[PlaylistItem, list[tuple[PlaylistItemElement, Media]]]]


def _with_elements(session: Session, items: list[PlaylistItem]) -> SceneRows:
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


def get_with_items(session: Session, *, user: User, playlist_id: uuid.UUID) -> tuple[Playlist, SceneRows]:
    playlist = _owned(session, user, playlist_id)
    items = session.exec(
        select(PlaylistItem)
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.position)
    ).all()
    return playlist, _with_elements(session, list(items))


def _affected_devices(session: Session, playlist_id: uuid.UUID) -> list[Device]:
    """Every screen this playlist could reach — by direct assignment or by a schedule.

    Same "both routes count" reasoning as remove()'s in-use check, applied to the push nudge
    instead of a delete guard: a schedule-only screen must hear about an edit exactly as
    readily as a directly-assigned one.
    """
    from app.services import schedules as schedule_service

    seen: dict[uuid.UUID, Device] = {
        d.id: d for d in session.exec(select(Device).where(Device.playlist_id == playlist_id)).all()
    }
    for device in schedule_service.devices_for_playlist(session, playlist_id):
        seen[device.id] = device
    return list(seen.values())


def _notify_devices(session: Session, playlist_id: uuid.UUID) -> None:
    """Best-effort push to every screen this playlist reaches — see devices.update() for the
    same pattern applied to a direct device change. Never the source of truth: a screen that
    misses this still catches up on its next poll."""
    from app.infra import mqtt
    from app.services import device_sync

    for device in _affected_devices(session, playlist_id):
        mqtt.notify_manifest_changed(
            device_id=device.id, version=device_sync.compute_version(session, device),
        )


def update(
    session: Session,
    *,
    user: User,
    playlist_id: uuid.UUID,
    name: str | None = None,
    shuffle: bool | None = None,
) -> Playlist:
    playlist = _owned(session, user, playlist_id)
    if name is not None:
        playlist.name = name.strip()
    if shuffle is not None:
        playlist.shuffle = shuffle
    playlist.updated_at = utcnow()
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    # Only shuffle changes what a screen shows — compute_version deliberately excludes the
    # playlist's name (cosmetic, see device_sync.py), and a rename must not wake up every
    # screen this playlist reaches for nothing.
    if shuffle is not None:
        _notify_devices(session, playlist_id)
    return playlist


def default_duration(elements_media: list[Media]) -> int:
    """A scene's default length: its one video element's own duration, or the fixed image
    default otherwise (an image-only scene, an empty scene, or one with no single canonical
    video to take a length from)."""
    videos = [m for m in elements_media if m.kind == MediaKind.VIDEO and m.duration_seconds]
    if len(videos) == 1:
        return max(MIN_ITEM_SECONDS, round(videos[0].duration_seconds))
    return IMAGE_DEFAULT_SECONDS


def replace_items(
    session: Session,
    *,
    user: User,
    playlist_id: uuid.UUID,
    items: list["ItemSpec"],
) -> tuple[Playlist, SceneRows]:
    """Replace the entire list of scenes in one transaction.

    Whole-array replace rather than insert/move/reorder verbs: drag-and-drop produces a
    complete new order anyway, so per-item mutation would only add conflict handling for a
    problem nobody has. Delete-then-insert also means the unique `(playlist_id, position)`
    constraint is never violated mid-transaction and needs no DEFERRABLE — elements cascade
    with their scene, so clearing `playlist_items` is enough.

    An empty list is legal — emptying a playlist is not an error. A scene with zero elements
    is also legal (a blank frame), for the same reason.
    """
    playlist = _owned(session, user, playlist_id)

    media_ids = {el.media_id for spec in items for el in spec.elements}
    found: dict[uuid.UUID, Media] = {}
    if media_ids:
        for media in session.exec(select(Media).where(Media.id.in_(media_ids))).all():
            found[media.id] = media

    for spec in items:
        video_count = 0
        for el in spec.elements:
            media = found.get(el.media_id)
            # Same message whether it is missing, another account's, or still uploading — a
            # playlist editor must not become a probe for what exists elsewhere.
            if media is None or media.account_id != user.account_id or media.status != MediaStatus.READY:
                raise InvalidItems(f"{el.media_id} is not available in this library")
            if media.kind != MediaKind.VIDEO and el.has_audio:
                raise InvalidItems(f"{el.media_id}: sound only applies to video")
            if media.kind != MediaKind.VIDEO and el.rotation_degrees:
                raise InvalidItems(f"{el.media_id}: rotation only applies to video")
            if media.kind == MediaKind.VIDEO:
                video_count += 1
        # Hardware, not taste: the player keeps exactly one long-lived video decoder/surface
        # alive per screen (see PlaybackSurface.kt), and low-end signage SoCs commonly expose
        # only 1-2 concurrent hardware decoders system-wide. Two videos in one scene risks the
        # "decodes fine, frame never paints, no error" failure this codebase has already been
        # burned by once — caught here, at save time, rather than discovered on a wall.
        if video_count > 1:
            raise InvalidItems("a scene can only have one video element at a time")
        if spec.duration_seconds is not None and not (
            MIN_ITEM_SECONDS <= spec.duration_seconds <= MAX_ITEM_SECONDS
        ):
            raise InvalidItems(
                f"duration must be between {MIN_ITEM_SECONDS} and {MAX_ITEM_SECONDS} seconds"
            )

    session.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id))
    for position, spec in enumerate(items):
        elements_media = [found[el.media_id] for el in spec.elements]
        # id is generated client-side (default_factory), so it's already real before add() —
        # no flush needed to reference it while building this scene's elements below.
        item = PlaylistItem(
            playlist_id=playlist_id,
            # Position comes from the array index; the client never sends one.
            position=position,
            duration_seconds=spec.duration_seconds or default_duration(elements_media),
            is_enabled=spec.is_enabled,
        )
        session.add(item)
        for el in spec.elements:
            session.add(
                PlaylistItemElement(
                    playlist_item_id=item.id,
                    media_id=el.media_id,
                    z_index=el.z_index,
                    x=el.x,
                    y=el.y,
                    width=el.width,
                    height=el.height,
                    fit=el.fit,
                    crop_x=el.crop_x,
                    crop_y=el.crop_y,
                    crop_zoom=el.crop_zoom,
                    has_audio=el.has_audio,
                    rotation_degrees=el.rotation_degrees,
                )
            )
    playlist.updated_at = utcnow()
    session.add(playlist)
    session.commit()
    _notify_devices(session, playlist_id)
    return get_with_items(session, user=user, playlist_id=playlist_id)


def devices_using(session: Session, playlist_id: uuid.UUID) -> list[str]:
    return list(
        session.exec(
            select(Device.name).where(Device.playlist_id == playlist_id)
        ).all()
    )


def remove(session: Session, *, user: User, playlist_id: uuid.UUID) -> None:
    """Refuse while a screen is pointed at it."""
    playlist = _owned(session, user, playlist_id)

    if user.role == UserRole.MANAGER and playlist.created_by != user.id:
        raise NotYours(str(playlist_id))

    # Both routes to a screen count. A playlist can reach a device by direct assignment *or*
    # by a schedule, and deleting one that is only scheduled would silently blank that screen
    # when the window next opens — a failure that surfaces days later, at 9am, on a wall.
    from app.services import schedules as schedule_service

    names = set(devices_using(session, playlist_id))
    names |= set(schedule_service.devices_scheduling(session, playlist_id))
    if names:
        raise PlaylistInUse(sorted(n or "Unnamed screen" for n in names))

    # Items (and their elements, via CASCADE) go with the playlist; the media they
    # referenced is untouched.
    session.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id))
    session.exec(delete(Playlist).where(Playlist.id == playlist_id))
    session.commit()
