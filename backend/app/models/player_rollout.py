import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class PlayerRollout(SQLModel, table=True):
    """One "publish this build" event — scheduled now or in the future.

    `scheduled_at` is never null: an immediate rollout stores its own `created_at` as its
    `scheduled_at`, so "what's live right now" is always the same query — the row with the
    latest `scheduled_at` that has already passed. That makes both "publish now" and
    "publish at 2am Tuesday" the same kind of row, and a future rollout can be superseded or
    rolled back just by creating (or deleting) another one; nothing has to wake up and flip a
    flag when the clock hits it. See `services/player_rollouts.py::active_rollout`.

    Replaces the old `PLAYER_LATEST_VERSION`/`PLAYER_APK_KEY` env vars, which could only be
    changed by redeploying and had no notion of "later" at all.
    """

    __tablename__ = "player_rollouts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    version: str = Field(max_length=32)
    # R2 key, e.g. "apks/fortu-player-1.2.0.apk" — same naming convention
    # scripts/publish_player_apk.py already uploads under.
    apk_key: str
    scheduled_at: datetime = Field(sa_column=tz_column(nullable=False, index=True))
    created_by: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
