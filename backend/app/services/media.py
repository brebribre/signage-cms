"""The media library.

Uploads never pass through this API. The browser PUTs straight to R2 with a presigned URL,
so a 500 MB video never touches the service, and proxy body limits stop being a concern.
That makes the flow three calls, and makes `status` load-bearing.
"""

import uuid
from datetime import datetime

from sqlmodel import Session, delete, select

from app.infra import storage
from app.config import get_settings
from app.models import Media, MediaKind, MediaStatus, Playlist, PlaylistItem, User, UserRole
from app.services.errors import DomainError

# Deliberately narrow. h.264/AAC in MP4 is the only combination a cheap Android stick is
# certain to decode in hardware; h.265 and VP9 are a coin flip, and software decoding a 4K
# file means dropped frames rather than a clean failure. Refusing at upload is far kinder
# than a screen that stutters in a lobby.
ALLOWED_MIME: dict[str, MediaKind] = {
    "image/jpeg": MediaKind.IMAGE,
    "image/png": MediaKind.IMAGE,
    "image/webp": MediaKind.IMAGE,
    "image/gif": MediaKind.IMAGE,
    "video/mp4": MediaKind.VIDEO,
}


class UnsupportedMediaType(DomainError):
    pass


class FileTooLarge(DomainError):
    pass


class UploadNotFound(DomainError):
    pass


class UploadIncomplete(DomainError):
    """The presigned PUT never landed, or landed at a different size than declared."""


class MediaInUse(DomainError):
    def __init__(self, playlist_names: list[str]):
        self.playlist_names = playlist_names
        super().__init__(", ".join(playlist_names))


class NotYours(DomainError):
    """A manager may delete only what they uploaded."""


def _object_key(account_id: uuid.UUID, media_id: uuid.UUID, filename: str) -> str:
    # Account-prefixed so a bucket listing is comprehensible, id-scoped so two files with the
    # same name never collide.
    safe = filename.replace("/", "_").strip() or "file"
    return f"media/{account_id}/{media_id}/{safe}"


def _thumbnail_key(account_id: uuid.UUID, media_id: uuid.UUID) -> str:
    return f"media/{account_id}/{media_id}/thumb.jpg"


def start_upload(
    session: Session, *, user: User, filename: str, content_type: str, size_bytes: int
) -> tuple[Media, str, str]:
    """Reserve a row and hand back the URLs to PUT to.

    The row is created `pending` and is invisible to every listing until `complete_upload`
    confirms the object exists. That is what makes an abandoned upload harmless rather than a
    broken tile in the library.
    """
    settings = get_settings()

    kind = ALLOWED_MIME.get(content_type)
    if kind is None:
        raise UnsupportedMediaType(content_type)
    if size_bytes <= 0 or size_bytes > settings.media_max_bytes:
        raise FileTooLarge(str(size_bytes))

    media_id = uuid.uuid4()
    key = _object_key(user.account_id, media_id, filename)
    thumb_key = _thumbnail_key(user.account_id, media_id)

    media = Media(
        id=media_id,
        account_id=user.account_id,
        created_by=user.id,
        filename=filename,
        kind=kind,
        mime_type=content_type,
        size_bytes=size_bytes,
        storage_key=key,
        thumbnail_key=thumb_key,
        checksum="",
        status=MediaStatus.PENDING,
    )
    session.add(media)
    session.commit()
    session.refresh(media)

    return media, storage.presign_put(key, content_type), storage.presign_put(thumb_key, "image/jpeg")


def complete_upload(
    session: Session,
    *,
    user: User,
    media_id: uuid.UUID,
    checksum: str,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: float | None = None,
) -> Media:
    """Confirm the object landed, then make the row visible.

    Verified against R2 rather than trusted: a client that says "done" without having
    uploaded anything would otherwise put a permanently broken row in the library.
    """
    media = session.get(Media, media_id)
    if media is None or media.account_id != user.account_id:
        raise UploadNotFound(str(media_id))

    head = storage.head_object(media.storage_key)
    if head is None:
        raise UploadIncomplete("object not found in storage")
    actual = head.get("ContentLength")
    if actual is not None and int(actual) != media.size_bytes:
        raise UploadIncomplete(f"declared {media.size_bytes} bytes, stored {actual}")

    media.checksum = checksum
    media.width = width
    media.height = height
    media.duration_seconds = duration_seconds
    media.status = MediaStatus.READY
    # A thumbnail is optional: if the browser could not make one, the tile falls back to a
    # placeholder rather than the upload failing.
    if storage.head_object(media.thumbnail_key) is None:
        media.thumbnail_key = None

    session.add(media)
    session.commit()
    session.refresh(media)
    return media


def list_media(session: Session, *, user: User, kind: MediaKind | None = None) -> list[Media]:
    """Ready media in the caller's account, newest first.

    Account-scoped, not user-scoped: the library is shared, which is the whole point of the
    accounts table. A manager sees what their colleagues uploaded.
    """
    statement = (
        select(Media)
        .where(Media.account_id == user.account_id, Media.status == MediaStatus.READY)
        .order_by(Media.created_at.desc())
    )
    if kind is not None:
        statement = statement.where(Media.kind == kind)
    return list(session.exec(statement).all())


def get_media(session: Session, *, user: User, media_id: uuid.UUID) -> Media:
    media = session.get(Media, media_id)
    # 404 rather than 403 for another account's media: do not confirm that it exists.
    if media is None or media.account_id != user.account_id or media.status != MediaStatus.READY:
        raise UploadNotFound(str(media_id))
    return media


def playlists_using(session: Session, media_id: uuid.UUID) -> list[str]:
    return list(
        session.exec(
            select(Playlist.name)
            .join(PlaylistItem, PlaylistItem.playlist_id == Playlist.id)
            .where(PlaylistItem.media_id == media_id)
            .distinct()
        ).all()
    )


def delete_media(session: Session, *, user: User, media_id: uuid.UUID) -> None:
    """Refuse if the file is on air; otherwise remove the row, then the objects."""
    media = get_media(session, user=user, media_id=media_id)

    # The guardrail from Phase 3: a manager may delete only what they created, so one person
    # cannot quietly remove a colleague's library. Owners may delete anything.
    if user.role == UserRole.MANAGER and media.created_by != user.id:
        raise NotYours(str(media_id))

    names = playlists_using(session, media_id)
    if names:
        # Surfacing the RESTRICT from the schema as a usable error rather than a 500.
        raise MediaInUse(names)

    keys = [media.storage_key] + ([media.thumbnail_key] if media.thumbnail_key else [])
    session.exec(delete(Media).where(Media.id == media_id))
    session.commit()

    # After the commit, deliberately. See storage.delete_object.
    for key in keys:
        storage.delete_object(key)


def view_url(media: Media, ttl: int | None = None) -> str:
    return storage.presign_get(media.storage_key, ttl)


def thumbnail_url(media: Media) -> str | None:
    return storage.presign_get(media.thumbnail_key) if media.thumbnail_key else None
