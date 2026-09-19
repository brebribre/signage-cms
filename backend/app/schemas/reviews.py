import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import ReviewKind, ReviewStatus


class ReviewRead(BaseModel):
    id: uuid.UUID
    kind: ReviewKind
    status: ReviewStatus
    requested_by: uuid.UUID | None
    requested_by_name: str
    target_id: uuid.UUID | None
    target_name: str
    summary: str
    screens: list[str]
    #: Playlist names the change touches, as they were when it was sent.
    playlists: list[str] = []
    # The change as sent — the Reviews page shows the parts worth reading (scene count,
    # rules) without a second request.
    payload: dict[str, Any]
    note: str | None
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class PendingReview(BaseModel):
    """What a write endpoint answers (202) instead of applying, when the caller's change has
    to be reviewed first — see services/reviews.py."""

    pending_review: ReviewRead


class ReviewDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class PendingCount(BaseModel):
    count: int
