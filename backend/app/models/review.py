"""Content reviews: a manager's change to what screens show, waiting for the owner.

A manager can build content freely, but the moment a save would change a screen — a playlist
that is on air, a campaign, a schedule — the change is parked here instead of applied, and
the owner approves or rejects it from the Reviews page. The full request is kept as sent, so
approving replays exactly what the manager asked for, as them, with their screen grants.

See docs/user-access-management.html for the rules and the knobs.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class ReviewKind(StrEnum):
    PLAYLIST_ITEMS = "playlist_items"
    PLAYLIST_SHUFFLE = "playlist_shuffle"
    CAMPAIGN_CREATE = "campaign_create"
    CAMPAIGN_UPDATE = "campaign_update"
    CAMPAIGN_DELETE = "campaign_delete"
    SCHEDULE_CREATE = "schedule_create"
    SCHEDULE_UPDATE = "schedule_update"
    SCHEDULE_DELETE = "schedule_delete"
    DEVICE_PLAYLIST = "device_playlist"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ContentReview(SQLModel, table=True):
    __tablename__ = "content_reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    # SET NULL: the review outlives the manager who sent it, and still reads sensibly thanks
    # to the name kept beside it.
    requested_by: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    requested_by_name: str
    kind: ReviewKind = Field(sa_column=enum_column(ReviewKind, nullable=False))
    # The playlist, campaign, schedule or screen the change is about — None for something
    # that does not exist yet (a new campaign). Not a foreign key: the target may be deleted
    # while the review waits, and approving then fails with a message rather than a cascade.
    target_id: uuid.UUID | None = Field(default=None)
    target_name: str
    # One line for the Reviews page: "6 scenes in Lobby Rotation".
    summary: str
    # Screen names the change would reach, as they were when it was sent.
    screens: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    # Playlist names the change touches — the one being edited, or the ones a campaign or
    # schedule puts on screens — as they were when it was sent. The list page shows both.
    playlists: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
    # The request body as sent, re-validated against the same schema when approved.
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: ReviewStatus = Field(
        default=ReviewStatus.PENDING, sa_column=enum_column(ReviewStatus, nullable=False, index=True)
    )
    # The owner's reason on a rejection, shown to the manager. Optional.
    note: str | None = Field(default=None)
    reviewed_by: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    reviewed_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False, index=True))
