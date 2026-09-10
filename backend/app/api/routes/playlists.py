import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models import Media, Playlist, PlaylistItem
from app.schemas.playlists import (
    ItemMedia,
    ItemRead,
    ItemsWrite,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistSummary,
    PlaylistUpdate,
)
from app.services import media as media_service
from app.services import playlists as playlist_service
from app.services.playlists import (
    InvalidItems,
    ItemSpec,
    NotYours,
    PlaylistInUse,
    PlaylistNotFound,
)

router = APIRouter(tags=["playlists"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Playlist not found")


def _item(item: PlaylistItem, media: Media) -> ItemRead:
    return ItemRead(
        id=item.id,
        position=item.position,
        duration_seconds=item.duration_seconds,
        fit=item.fit,
        is_enabled=item.is_enabled,
        crop_x=item.crop_x,
        crop_y=item.crop_y,
        crop_zoom=item.crop_zoom,
        trim_start_seconds=item.trim_start_seconds,
        trim_end_seconds=item.trim_end_seconds,
        has_audio=item.has_audio,
        media=ItemMedia(
            id=media.id,
            filename=media.filename,
            kind=media.kind,
            thumbnail_url=media_service.thumbnail_url(media),
            url=media_service.view_url(media),
            width=media.width,
            height=media.height,
            duration_seconds=media.duration_seconds,
        ),
    )


def _detail(session, playlist: Playlist, rows) -> PlaylistDetail:
    items = [_item(i, m) for i, m in rows]
    return PlaylistDetail(
        id=playlist.id,
        name=playlist.name,
        shuffle=playlist.shuffle,
        # Counted from enabled items only: the number people read as "how long is this loop"
        # must match what a screen actually plays.
        item_count=sum(1 for i in items if i.is_enabled),
        total_duration_seconds=sum(i.duration_seconds for i in items if i.is_enabled),
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        items=items,
        used_by=[n or "Unnamed screen" for n in playlist_service.devices_using(session, playlist.id)],
    )


@router.get("/playlists", response_model=list[PlaylistSummary])
def list_playlists(user: CurrentUser, session: DbSession) -> list[PlaylistSummary]:
    return [
        PlaylistSummary(
            id=p.id,
            name=p.name,
            shuffle=p.shuffle,
            item_count=count,
            total_duration_seconds=total,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p, count, total in playlist_service.list_playlists(session, user=user)
    ]


@router.post("/playlists", response_model=PlaylistDetail, status_code=status.HTTP_201_CREATED)
def create_playlist(body: PlaylistCreate, user: CurrentUser, session: DbSession) -> PlaylistDetail:
    playlist = playlist_service.create(session, user=user, name=body.name)
    return _detail(session, playlist, [])


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(playlist_id: uuid.UUID, user: CurrentUser, session: DbSession) -> PlaylistDetail:
    try:
        playlist, rows = playlist_service.get_with_items(
            session, user=user, playlist_id=playlist_id
        )
    except PlaylistNotFound:
        raise NOT_FOUND from None
    return _detail(session, playlist, rows)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistDetail)
def update_playlist(
    playlist_id: uuid.UUID, body: PlaylistUpdate, user: CurrentUser, session: DbSession
) -> PlaylistDetail:
    try:
        playlist_service.update(
            session, user=user, playlist_id=playlist_id, name=body.name, shuffle=body.shuffle
        )
        playlist, rows = playlist_service.get_with_items(
            session, user=user, playlist_id=playlist_id
        )
    except PlaylistNotFound:
        raise NOT_FOUND from None
    return _detail(session, playlist, rows)


@router.put("/playlists/{playlist_id}/items", response_model=PlaylistDetail)
def replace_items(
    playlist_id: uuid.UUID, body: ItemsWrite, user: CurrentUser, session: DbSession
) -> PlaylistDetail:
    """Replace the entire list, in order.

    One endpoint rather than insert/move/reorder verbs — drag-and-drop produces a complete
    new order anyway, and the array index *is* the position, so the two cannot disagree.
    """
    try:
        playlist, rows = playlist_service.replace_items(
            session,
            user=user,
            playlist_id=playlist_id,
            items=[
                ItemSpec(
                    media_id=i.media_id,
                    duration_seconds=i.duration_seconds,
                    fit=i.fit,
                    is_enabled=i.is_enabled,
                    crop_x=i.crop_x,
                    crop_y=i.crop_y,
                    crop_zoom=i.crop_zoom,
                    trim_start_seconds=i.trim_start_seconds,
                    trim_end_seconds=i.trim_end_seconds,
                    has_audio=i.has_audio,
                )
                for i in body.items
            ],
        )
    except PlaylistNotFound:
        raise NOT_FOUND from None
    except InvalidItems as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return _detail(session, playlist, rows)


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(playlist_id: uuid.UUID, user: CurrentUser, session: DbSession) -> None:
    try:
        playlist_service.remove(session, user=user, playlist_id=playlist_id)
    except PlaylistNotFound:
        raise NOT_FOUND from None
    except NotYours:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can only delete playlists you created"
        ) from None
    except PlaylistInUse as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Assigned to {', '.join(exc.device_names)} — point those screens elsewhere first",
        ) from None
