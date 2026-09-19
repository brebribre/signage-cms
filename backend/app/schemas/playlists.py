import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ItemFit, MediaKind, SceneBackground
from app.services.playlists import MAX_CROP_ZOOM, MAX_ITEM_SECONDS, MIN_ITEM_SECONDS


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PlaylistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    shuffle: bool | None = None


HEX_COLOUR = r"^#[0-9a-fA-F]{6}$"


class TextStyle(BaseModel):
    """How a text element looks. Every player draws it from these same few numbers, and the CMS
    preview does too, so a scene reads the same everywhere. Unset fields take these defaults."""

    # Font size as a fraction of the screen's height — 0.06 is a comfortable headline on any
    # panel, whatever its resolution.
    size: float = Field(default=0.06, ge=0.01, le=0.5)
    color: str = Field(default="#FFFFFF", pattern=HEX_COLOUR)
    weight: Literal["regular", "bold"] = "bold"
    align: Literal["left", "center", "right"] = "center"
    # A solid box behind the text, or none. Text on a busy photo needs one.
    background: str | None = Field(default=None, pattern=HEX_COLOUR)


class ElementWrite(BaseModel):
    # Exactly one of these three: a library file, a website shown live (https only), or a piece
    # of text drawn by the player. Checked in services/playlists.py::replace_items, alongside
    # the rest of a scene's rules.
    media_id: uuid.UUID | None = None
    web_url: str | None = Field(default=None, max_length=2048)
    text: str | None = Field(default=None, max_length=2000)
    text_style: TextStyle | None = None
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
    # Behind anything the elements don't cover. See models.playlist.SceneBackground. Blur by
    # default: a picture on a screen of another shape looks placed rather than letterboxed.
    background: SceneBackground = SceneBackground.BLUR
    # Required when `background` is "color"; kept otherwise.
    background_color: str | None = Field(default=None, pattern=HEX_COLOUR)
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
    # A file element carries `media`; a website element carries `web_url`; a text element
    # carries `text` and `text_style`.
    media: ItemMedia | None
    web_url: str | None = None
    text: str | None = None
    text_style: TextStyle | None = None


class ItemRead(BaseModel):
    id: uuid.UUID
    position: int
    duration_seconds: int
    is_enabled: bool
    background: SceneBackground
    background_color: str | None = None
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
    # One tile per enabled scene, in play order, up to MAX_PREVIEW_THUMBNAILS: the first-painted
    # element's thumbnail, or none with a kind that says what the tile is (a website, text, or
    # a file without a picture) so the list can show an icon instead of a blank.
    thumbnails: list["PlaylistTile"] = []


class PlaylistTile(BaseModel):
    url: str | None
    #: "image", "video", "web" or "text".
    kind: str


class PlaylistDetail(PlaylistSummary):
    items: list[ItemRead]
    used_by: list[str] = []


PlaylistSummary.model_rebuild()
