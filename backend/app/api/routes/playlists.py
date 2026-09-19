import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.api.review_gate import needs_review, park
from app.models import Media, Playlist, PlaylistItem, PlaylistItemElement, ReviewKind
from app.schemas.playlists import (
    PlaylistTile,
    TextStyle,
    ElementRead,
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
    ElementSpec,
    InvalidItems,
    ItemSpec,
    NotYours,
    PlaylistInUse,
    PlaylistNotFound,
)

router = APIRouter(tags=["playlists"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Playlist not found")


def _element(element: PlaylistItemElement, media: Media | None) -> ElementRead:
    return ElementRead(
        id=element.id,
        z_index=element.z_index,
        x=element.x,
        y=element.y,
        width=element.width,
        height=element.height,
        fit=element.fit,
        crop_x=element.crop_x,
        crop_y=element.crop_y,
        crop_zoom=element.crop_zoom,
        has_audio=element.has_audio,
        rotation_degrees=element.rotation_degrees,
        media=ItemMedia(
            id=media.id,
            filename=media.filename,
            kind=media.kind,
            thumbnail_url=media_service.thumbnail_url(media),
            url=media_service.view_url(media),
            width=media.width,
            height=media.height,
            duration_seconds=media.duration_seconds,
        )
        if media
        else None,
        web_url=element.web_url,
        text=element.text,
        text_style=element.text_style,
    )


def _item(item: PlaylistItem, elements: list[tuple[PlaylistItemElement, Media | None]]) -> ItemRead:
    return ItemRead(
        id=item.id,
        position=item.position,
        duration_seconds=item.duration_seconds,
        is_enabled=item.is_enabled,
        background=item.background,
        background_color=item.background_color,
        elements=[_element(el, media) for el, media in elements],
    )


def _detail(session, playlist: Playlist, rows) -> PlaylistDetail:
    items = [_item(i, elements) for i, elements in rows]
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
        used_by=[n or "Unnamed screen" for n in playlist_service.screens_reached(session, playlist.id)],
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
            thumbnails=[PlaylistTile(**t) for t in thumbnails],
        )
        for p, count, total, thumbnails in playlist_service.list_playlists(session, user=user)
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


@router.patch("/playlists/{playlist_id}", response_model=PlaylistDetail, responses={202: {"description": "Sent for review"}})
def update_playlist(
    playlist_id: uuid.UUID, body: PlaylistUpdate, user: CurrentUser, session: DbSession
):
    # Only shuffle changes what a screen shows; a rename never needs a review.
    if body.shuffle is not None and needs_review(user):
        try:
            playlist, _ = playlist_service.get_with_items(session, user=user, playlist_id=playlist_id)
        except PlaylistNotFound:
            raise NOT_FOUND from None
        screens = playlist_service.screens_reached(session, playlist_id)
        if screens and body.shuffle != playlist.shuffle:
            if body.name is not None:
                # The rename part applies now; only the shuffle waits.
                playlist_service.update(session, user=user, playlist_id=playlist_id, name=body.name)
            return park(
                session, user=user, kind=ReviewKind.PLAYLIST_SHUFFLE, target_id=playlist_id,
                target_name=playlist.name,
                summary=f"Shuffle {'on' if body.shuffle else 'off'} for playlist “{playlist.name}”",
                screens=screens, playlists=[playlist.name], payload={"shuffle": body.shuffle},
            )
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


def item_specs(body: ItemsWrite) -> list[ItemSpec]:
    """The request body as the service takes it. Shared with the review replay
    (routes/reviews.py), so an approved change is built exactly as a direct save is."""
    return [
        ItemSpec(
            duration_seconds=i.duration_seconds,
            is_enabled=i.is_enabled,
            background=i.background,
            background_color=i.background_color,
            elements=[
                ElementSpec(
                    media_id=el.media_id,
                    web_url=el.web_url.strip() if el.web_url else None,
                    text=el.text,
                    text_style=el.text_style.model_dump() if el.text_style else (TextStyle().model_dump() if el.text is not None else None),
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
                for el in i.elements
            ],
        )
        for i in body.items
    ]


@router.put("/playlists/{playlist_id}/items", response_model=PlaylistDetail, responses={202: {"description": "Sent for review"}})
def replace_items(
    playlist_id: uuid.UUID, body: ItemsWrite, user: CurrentUser, session: DbSession
):
    """Replace the entire list of scenes, in order.

    One endpoint rather than insert/move/reorder verbs — drag-and-drop produces a complete
    new order anyway, and the array index *is* the position, so the two cannot disagree.

    A manager's save of a playlist that is on screens is parked for the owner (202) instead
    of applied — see api/review_gate.py. A playlist nobody plays saves at once.
    """
    if needs_review(user):
        try:
            playlist, _ = playlist_service.get_with_items(session, user=user, playlist_id=playlist_id)
        except PlaylistNotFound:
            raise NOT_FOUND from None
        screens = playlist_service.screens_reached(session, playlist_id)
        if screens:
            n = sum(1 for i in body.items if i.is_enabled)
            return park(
                session, user=user, kind=ReviewKind.PLAYLIST_ITEMS, target_id=playlist_id,
                target_name=playlist.name,
                summary=f"{n} scene{'' if n == 1 else 's'} in playlist “{playlist.name}”",
                screens=screens, playlists=[playlist.name], payload=body.model_dump(mode="json"),
            )
    try:
        playlist, rows = playlist_service.replace_items(
            session, user=user, playlist_id=playlist_id, items=item_specs(body),
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
