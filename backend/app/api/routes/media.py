import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models import Media, MediaKind
from app.schemas.media import (
    CompleteRequest,
    MediaDetail,
    MediaRead,
    UploadRequest,
    UploadResponse,
)
from app.services import media as media_service
from app.services.media import (
    ALLOWED_MIME,
    FileTooLarge,
    MediaInUse,
    NotYours,
    UnsupportedMediaType,
    UploadIncomplete,
    UploadNotFound,
)

router = APIRouter(tags=["media"])


def _read(media: Media, used_in: list[str] | None = None) -> MediaRead:
    return MediaRead(
        **media.model_dump(),
        thumbnail_url=media_service.thumbnail_url(media),
        url=media_service.view_url(media),
        used_in=used_in or [],
    )


@router.post("/media/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def start_upload(body: UploadRequest, user: CurrentUser, session: DbSession) -> UploadResponse:
    """Reserve a media row and return presigned URLs to PUT the file to."""
    try:
        media, upload_url, thumb_url = media_service.start_upload(
            session,
            user=user,
            filename=body.filename,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
        )
    except UnsupportedMediaType:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"{body.content_type} is not supported. Allowed: {', '.join(sorted(ALLOWED_MIME))}. "
            "Video must be h.264 in MP4 — it is the only codec every signage device decodes "
            "in hardware.",
        ) from None
    except FileTooLarge:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is too large"
        ) from None

    return UploadResponse(
        media_id=media.id, upload_url=upload_url, thumbnail_upload_url=thumb_url
    )


@router.post("/media/{media_id}/complete", response_model=MediaRead)
def complete_upload(
    media_id: uuid.UUID, body: CompleteRequest, user: CurrentUser, session: DbSession
) -> MediaRead:
    """Confirm the upload landed and make the media visible in the library."""
    try:
        media = media_service.complete_upload(
            session,
            user=user,
            media_id=media_id,
            checksum=body.checksum,
            width=body.width,
            height=body.height,
            duration_seconds=body.duration_seconds,
        )
    except UploadNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media not found") from None
    except UploadIncomplete as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Upload incomplete: {exc}") from None
    return _read(media)


@router.get("/media", response_model=list[MediaRead])
def list_media(
    user: CurrentUser, session: DbSession, kind: MediaKind | None = Query(default=None)
) -> list[MediaRead]:
    """The account's library. Shared: a manager sees what colleagues uploaded."""
    return [_read(m) for m in media_service.list_media(session, user=user, kind=kind)]


@router.get("/media/{media_id}", response_model=MediaDetail)
def get_media(media_id: uuid.UUID, user: CurrentUser, session: DbSession) -> MediaDetail:
    try:
        media = media_service.get_media(session, user=user, media_id=media_id)
    except UploadNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media not found") from None
    return MediaDetail(
        **media.model_dump(),
        thumbnail_url=media_service.thumbnail_url(media),
        url=media_service.view_url(media),
        used_in=media_service.playlists_using(session, media_id),
    )


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(media_id: uuid.UUID, user: CurrentUser, session: DbSession) -> None:
    try:
        media_service.delete_media(session, user=user, media_id=media_id)
    except UploadNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media not found") from None
    except NotYours:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can only delete media you uploaded"
        ) from None
    except MediaInUse as exc:
        # The 409 names the playlists, so the UI can say "remove it there first" rather than
        # showing a bare "Conflict".
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Used in {', '.join(exc.playlist_names)} — remove it there first",
        ) from None
