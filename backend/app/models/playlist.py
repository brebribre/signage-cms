import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, ForeignKey, UniqueConstraint
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
    """One slot in a playlist.

    `position` is assigned from the array index by the service — the client never sends it.
    `PUT /playlists/{id}/items` deletes every row and re-inserts, so the unique constraint
    below is never violated mid-transaction and needs no DEFERRABLE.
    """

    __tablename__ = "playlist_items"
    __table_args__ = (UniqueConstraint("playlist_id", "position", name="uq_playlist_position"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    playlist_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # RESTRICT, not CASCADE: deleting a file that is on air must be refused with a 409
    # naming the playlists, not silently punch a hole in a running screen.
    media_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("media.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    position: int
    # How long this slot shows. Defaults to the media's own duration for a video and to a
    # fixed number of seconds for an image, but is overridable — cutting a long video short
    # is a thing signage genuinely does.
    duration_seconds: int
    fit: ItemFit = Field(
        default=ItemFit.CONTAIN,
        sa_column=enum_column(ItemFit, nullable=False),
    )
    # Take a slot out of rotation without losing its position, duration and fit. Restoring
    # it is then one click rather than rebuilding the row from memory.
    is_enabled: bool = Field(default=True)
    # Normalized [0,1] center of the visible crop, and a >=1 zoom relative to whatever aspect
    # ratio this is rendered against (1.0 == today's plain centered `cover`). Stored regardless
    # of `fit` so toggling Fit to compare doesn't discard a careful crop — it just isn't
    # rendered unless fit == COVER. See frontend/src/utils/cropMath.ts for how these resolve
    # into an actual rectangle at render time.
    crop_x: float | None = Field(default=None)
    crop_y: float | None = Field(default=None)
    crop_zoom: float | None = Field(default=None)
    # Video only, ignored for images. trim_end None means "to the end".
    trim_start_seconds: float = Field(default=0.0)
    trim_end_seconds: float | None = Field(default=None)
