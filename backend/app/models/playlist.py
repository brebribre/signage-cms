import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


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
