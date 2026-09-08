import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import ItemFit, MediaKind
from app.services.playlists import MAX_ITEM_SECONDS, MIN_ITEM_SECONDS


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PlaylistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    shuffle: bool | None = None


class ItemWrite(BaseModel):
    media_id: uuid.UUID
    # Null means "use the media's own length for a video, the image default otherwise" —
    # the server decides, so the client need not know the rule.
    duration_seconds: int | None = Field(
        default=None, ge=MIN_ITEM_SECONDS, le=MAX_ITEM_SECONDS
    )
    fit: ItemFit = ItemFit.CONTAIN
    is_enabled: bool = True


class ItemsWrite(BaseModel):
    """The whole list, in order. An empty list is legal."""

    items: list[ItemWrite] = Field(default_factory=list, max_length=500)


class ItemMedia(BaseModel):
    """Enough of the media to render a row *and* preview it at full size.

    `url` is a presigned GET, included per item so the editor's device preview can show the
    real file rather than the 480px thumbnail — the whole point of the preview is judging
    sharpness and cropping, which a thumbnail cannot answer. Presigning is a local HMAC, so
    N items cost N cheap computations and no network calls.
    """

    id: uuid.UUID
    filename: str
    kind: MediaKind
    thumbnail_url: str | None
    url: str
    width: int | None
    height: int | None
    duration_seconds: float | None


class ItemRead(BaseModel):
    id: uuid.UUID
    position: int
    duration_seconds: int
    fit: ItemFit
    is_enabled: bool
    media: ItemMedia


class PlaylistSummary(BaseModel):
    id: uuid.UUID
    name: str
    shuffle: bool
    item_count: int
    total_duration_seconds: int
    created_at: datetime
    updated_at: datetime


class PlaylistDetail(PlaylistSummary):
    items: list[ItemRead]
    used_by: list[str] = []
