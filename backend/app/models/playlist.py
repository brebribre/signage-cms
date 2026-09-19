import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class ItemFit(StrEnum):
    """How a slot's media fills the screen when their aspect ratios differ.

    Every established signage CMS exposes this per item, because mismatched aspect ratios
    are the normal case rather than the exception — portrait screens, square photos, mixed
    libraries. Without it the player has to guess, and it guesses wrong half the time.
    """

    # Whole image visible, letterboxed. The safe default: nothing is cropped or distorted.
    CONTAIN = "contain"
    # Fills the screen, cropping the overflow. Best-looking when the content can spare edges.
    COVER = "cover"
    # Fills by distorting. Rarely right, but occasionally the only way to place a fixed asset.
    STRETCH = "stretch"


class SceneBackground(StrEnum):
    """What shows wherever a scene's elements don't cover the screen — a portrait video placed
    on a landscape screen, say."""

    BLACK = "black"
    # A blurred, zoomed-in copy of the scene's largest picture or video, filling the screen
    # behind it. For a video that is its thumbnail, not the video itself: a second copy of a
    # playing video would need a second hardware decoder, which most TVs and signage boxes
    # don't have. Which element counts as "largest" is decided the same way everywhere (CMS
    # preview, web player, Android player): biggest box by area, bottom-most on a tie.
    BLUR = "blur"


class Playlist(SQLModel, table=True):
    """An ordered list of media with a duration per slot."""

    __tablename__ = "playlists"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    name: str
    # Randomise the play order. Order still matters when it is off, so this is a flag rather
    # than a different kind of playlist.
    shuffle: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class PlaylistItem(SQLModel, table=True):
    """One slot in a playlist — a scene that can hold one or more `PlaylistItemElement`s shown
    simultaneously (a video in one corner, a logo elsewhere), not a single media file itself.
    The common case (one full-bleed element) is just a scene with exactly one element sized to
    the whole frame — there is no separate "simple" representation.

    `position` is assigned from the array index by the service — the client never sends it.
    `PUT /playlists/{id}/items` deletes every row (elements cascade with it) and re-inserts, so
    the unique constraint below is never violated mid-transaction and needs no DEFERRABLE.
    """

    __tablename__ = "playlist_items"
    __table_args__ = (UniqueConstraint("playlist_id", "position", name="uq_playlist_position"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    playlist_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    position: int
    # How long this slot shows. Defaults to its one video element's own duration, or a fixed
    # default for an image-only scene, but is overridable — cutting a long video short is a
    # thing signage genuinely does. See services/playlists.py's default_duration().
    duration_seconds: int
    # Take a slot out of rotation without losing its elements. Restoring it is then one click
    # rather than rebuilding the scene from memory.
    is_enabled: bool = Field(default=True)
    background: SceneBackground = Field(
        default=SceneBackground.BLACK,
        sa_column=enum_column(SceneBackground, nullable=False, server_default=SceneBackground.BLACK.value),
    )


class PlaylistItemElement(SQLModel, table=True):
    """One media element within a scene (`PlaylistItem`), positioned/sized/rotated on its own.

    At most one element per scene may reference a video — enforced in
    services/playlists.py's replace_items(), not here, because it needs the media's `kind`
    (a join) rather than anything this row alone can check. The reason is hardware, not taste:
    the Android player keeps exactly one long-lived video decoder/surface alive for the whole
    screen (see PlaybackSurface.kt's own comment on why), and low-end signage SoCs commonly
    expose only 1-2 concurrent hardware decoders system-wide — two videos in one scene risks
    the exact "decodes fine, frame never paints, no error" failure this codebase has already
    been burned by once, just relocated. Images have no decoder to contend for, so they're
    unlimited.

    An element shows a library file (`media_id`), a live website (`web_url`), or a piece of
    text (`text`) — exactly one, enforced by the check constraint below.
    """

    __tablename__ = "playlist_item_elements"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN media_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN web_url IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN text IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_element_one_source",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    playlist_item_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("playlist_items.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # RESTRICT, not CASCADE: deleting a file that is on air must be refused with a 409
    # naming the playlists, not silently punch a hole in a running screen. Null for a website.
    media_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("media.id", ondelete="RESTRICT"), nullable=True, index=True
        ),
    )
    # A website shown live in this element's box — an iframe in the CMS, a WebView on the
    # screen. https only (see services/playlists.py). Set instead of `media_id`, never with it.
    web_url: str | None = Field(default=None)
    # Text typed in the scene editor, shown by the players themselves — no file, nothing to
    # download. Set instead of `media_id` and `web_url`. Its look is `text_style` (see
    # schemas/playlists.py TextStyle): a size as a fraction of the screen's height so the same
    # scene reads the same on a 1080p wall and a 4K one, a colour, a weight, an alignment and an
    # optional background — the handful of controls Canva's text box has, no more.
    text: str | None = Field(default=None)
    text_style: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    # Paint order within the scene — higher draws on top. Not a unique/sequential constraint:
    # the editor just needs *a* stable order, and re-saving the whole list (same pattern as
    # position above) never has to renumber gaps.
    z_index: int = Field(default=0)
    # Normalized [0,1] against the scene's own frame, deliberately NOT clamped to stay fully
    # inside it — a design surface that refuses a partially-off-canvas element is not Canva,
    # it's a crop tool. Validated only as finite/positive in replace_items(), not bounded here.
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    width: float = Field(default=1.0)
    height: float = Field(default=1.0)
    fit: ItemFit = Field(
        default=ItemFit.COVER,
        sa_column=enum_column(ItemFit, nullable=False),
    )
    # Normalized [0,1] center of the visible crop, and a >=1 zoom relative to this element's
    # own box aspect ratio (1.0 == plain centered `cover`, today's default). Stored regardless
    # of `fit` so toggling Fit to compare doesn't discard a careful crop — it just isn't
    # rendered unless fit == COVER. See frontend/src/utils/cropMath.ts for how these resolve
    # into an actual rectangle at render time.
    crop_x: float | None = Field(default=None)
    crop_y: float | None = Field(default=None)
    crop_zoom: float | None = Field(default=None)
    # Video only. Every video is muted by default — see PlaybackSurface.kt's `volume = 0f` —
    # so this is opt-in per element, not a mute toggle on an otherwise-audible default.
    has_audio: bool = Field(default=False)
    # Video only. Degrees clockwise (0/90/180/270) to correct a file shot sideways — applied
    # before fit/crop, so "rotate" always means "make it upright first, then place it."
    rotation_degrees: int = Field(default=0)
