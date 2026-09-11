import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ItemFit, MediaKind
from app.services.playlists import MAX_CROP_ZOOM, MAX_ITEM_SECONDS, MIN_ITEM_SECONDS


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PlaylistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    shuffle: bool | None = None


class ElementWrite(BaseModel):
    media_id: uuid.UUID
    z_index: int = 0
    # Normalized against the scene's own frame, deliberately unbounded — see
    # PlaylistItemElement for why a design surface must allow partially-off-canvas elements.
    x: float = 0.0
    y: float = 0.0
    width: float = Field(default=1.0, gt=0.0)
    height: float = Field(default=1.0, gt=0.0)
    fit: ItemFit = ItemFit.COVER
    # Normalized crop center + zoom — see PlaylistItemElement for the full explanation. Stored
    # regardless of `fit`; only rendered when fit == cover.
    crop_x: float | None = Field(default=None, ge=0.0, le=1.0)
    crop_y: float | None = Field(default=None, ge=0.0, le=1.0)
    crop_zoom: float | None = Field(default=None, ge=1.0, le=MAX_CROP_ZOOM)
    # Video only. Every video is muted unless this is set — see PlaylistItemElement.has_audio.
    has_audio: bool = False
    # Video only. See PlaylistItemElement.rotation_degrees.
    rotation_degrees: Literal[0, 90, 180, 270] = 0


class ItemWrite(BaseModel):
    # Null means "use the one video element's own length, or a fixed default for an
    # image-only scene" — the server decides, so the client need not know the rule.
    duration_seconds: int | None = Field(
        default=None, ge=MIN_ITEM_SECONDS, le=MAX_ITEM_SECONDS
    )
    is_enabled: bool = True
    elements: list[ElementWrite] = Field(default_factory=list, max_length=20)


class ItemsWrite(BaseModel):
    """The whole list, in order. An empty list is legal."""

    items: list[ItemWrite] = Field(default_factory=list, max_length=500)


class ItemMedia(BaseModel):
    """Enough of the media to render a row *and* preview it at full size.

    `url` is a presigned GET, included per element so the editor's device preview can show the
    real file rather than the 480px thumbnail — the whole point of the preview is judging
    sharpness and cropping, which a thumbnail cannot answer. Presigning is a local HMAC, so
    N elements cost N cheap computations and no network calls.
    """

    id: uuid.UUID
    filename: str
    kind: MediaKind
    thumbnail_url: str | None
    url: str
    width: int | None
    height: int | None
    duration_seconds: float | None


class ElementRead(BaseModel):
    id: uuid.UUID
    z_index: int
    x: float
    y: float
    width: float
    height: float
    fit: ItemFit
    crop_x: float | None
    crop_y: float | None
    crop_zoom: float | None
    has_audio: bool
    rotation_degrees: int
    media: ItemMedia


class ItemRead(BaseModel):
    id: uuid.UUID
    position: int
    duration_seconds: int
    is_enabled: bool
    elements: list[ElementRead]


class PlaylistSummary(BaseModel):
    id: uuid.UUID
    name: str
    shuffle: bool
    item_count: int
    total_duration_seconds: int
    created_at: datetime
    updated_at: datetime
    # A preview strip, not the whole loop — capped, see services/playlists.py::list_playlists.
    # `None` for a scene whose media has no thumbnail: a blank tile, not a skipped one.
    thumbnails: list[str | None] = []


class PlaylistDetail(PlaylistSummary):
    items: list[ItemRead]
    used_by: list[str] = []
