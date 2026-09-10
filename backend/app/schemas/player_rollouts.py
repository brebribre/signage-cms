import uuid
from datetime import datetime

from pydantic import BaseModel


class PlayerReleaseRead(BaseModel):
    """One build sitting in R2 — everything `publish_player_apk.py` has ever uploaded."""

    version: str
    size_bytes: int
    uploaded_at: datetime
    is_current: bool


class PlayerRolloutWrite(BaseModel):
    version: str
    # None publishes immediately; a future instant schedules it.
    scheduled_at: datetime | None = None


class PlayerRolloutRead(BaseModel):
    id: uuid.UUID
    version: str
    scheduled_at: datetime
    created_at: datetime
    #: Whether this is the rollout currently in effect — the most recently *scheduled* one
    #: whose time has passed. At most one rollout in the list is ever active.
    is_active: bool
