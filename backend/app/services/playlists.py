"""Playlists: an ordered list of media with a duration per slot."""

import uuid
from dataclasses import dataclass

from sqlmodel import Session, delete, func, select

from app.infra import mqtt
from app.models import (
    Device,
    ItemFit,
    Media,
    MediaKind,
    MediaStatus,
    Playlist,
    PlaylistItem,
    User,
    UserRole,
)
from app.models.base import utcnow
from app.services import device_sync
from app.services.errors import DomainError

# What an image shows for when nothing says otherwise. A video defaults to its own length.
IMAGE_DEFAULT_SECONDS = 10
MIN_ITEM_SECONDS = 1
MAX_ITEM_SECONDS = 3600


@dataclass(frozen=True)
class ItemSpec:
    """One slot as the client describes it. Position is deliberately absent — it is the
    index in the list, so the two can never disagree."""

    media_id: uuid.UUID
    duration_seconds: int | None = None
    fit: ItemFit = ItemFit.CONTAIN
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


def list_playlists(session: Session, *, user: User) -> list[tuple[Playlist, int, int]]:
    """Every playlist in the account, with its **enabled** item count and total duration.

    Aggregated in one query rather than by loading items per playlist — the list page shows
    both numbers for every row, and N+1 queries for a number is exactly the kind of thing
    that is invisible at three playlists and painful at three hundred.
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
    return [(p, int(count), int(total)) for p, count, total in rows]


def get_with_items(
    session: Session, *, user: User, playlist_id: uuid.UUID
) -> tuple[Playlist, list[tuple[PlaylistItem, Media]]]:
    playlist = _owned(session, user, playlist_id)
    rows = session.exec(
        select(PlaylistItem, Media)
        .join(Media, Media.id == PlaylistItem.media_id)
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.position)
    ).all()
    return playlist, [(item, media) for item, media in rows]


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


def default_duration(media: Media) -> int:
    if media.kind == MediaKind.VIDEO and media.duration_seconds:
        return max(MIN_ITEM_SECONDS, round(media.duration_seconds))
    return IMAGE_DEFAULT_SECONDS


def replace_items(
    session: Session,
    *,
    user: User,
    playlist_id: uuid.UUID,
    items: list["ItemSpec"],
) -> tuple[Playlist, list[tuple[PlaylistItem, Media]]]:
    """Replace the entire list in one transaction.

    Whole-array replace rather than insert/move/reorder verbs: drag-and-drop produces a
    complete new order anyway, so per-item mutation would only add conflict handling for a
    problem nobody has. Delete-then-insert also means the unique `(playlist_id, position)`
    constraint is never violated mid-transaction and needs no DEFERRABLE.

    An empty list is legal — emptying a playlist is not an error.
    """
    playlist = _owned(session, user, playlist_id)

    media_ids = [spec.media_id for spec in items]
    found: dict[uuid.UUID, Media] = {}
    if media_ids:
        for media in session.exec(select(Media).where(Media.id.in_(media_ids))).all():
            found[media.id] = media

    for spec in items:
        media_id, seconds = spec.media_id, spec.duration_seconds
        media = found.get(media_id)
        # Same message whether it is missing, another account's, or still uploading — a
        # playlist editor must not become a probe for what exists elsewhere.
        if media is None or media.account_id != user.account_id or media.status != MediaStatus.READY:
            raise InvalidItems(f"{media_id} is not available in this library")
        if seconds is not None and not (MIN_ITEM_SECONDS <= seconds <= MAX_ITEM_SECONDS):
            raise InvalidItems(
                f"duration must be between {MIN_ITEM_SECONDS} and {MAX_ITEM_SECONDS} seconds"
            )

    session.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id))
    for position, spec in enumerate(items):
        session.add(
            PlaylistItem(
                playlist_id=playlist_id,
                media_id=spec.media_id,
                # Position comes from the array index; the client never sends one.
                position=position,
                duration_seconds=spec.duration_seconds
                or default_duration(found[spec.media_id]),
                fit=spec.fit,
                is_enabled=spec.is_enabled,
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

    # Items cascade with the playlist; the media they referenced is untouched.
    session.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id))
    session.exec(delete(Playlist).where(Playlist.id == playlist_id))
    session.commit()
