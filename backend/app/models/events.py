import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class EventLevel(StrEnum):
    INFO = "info"
    ERROR = "error"


class DeviceEvent(SQLModel, table=True):
    """Something a screen reported, or something that happened to it.

    Until now the errors devices send on every heartbeat were logged and dropped. That is
    fine while you are watching a terminal during setup and useless afterwards — the whole
    point of a health page is answering "what went wrong on that screen last Tuesday" without
    having had a terminal open at the time.
    """

    __tablename__ = "device_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    device_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # Denormalised so the health page can scope by account without joining through devices,
    # and so a query stays cheap as this table becomes the largest one in the schema.
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    level: EventLevel = Field(sa_column=enum_column(EventLevel, nullable=False, index=True))
    message: str
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=tz_column(nullable=False, index=True)
    )


class PlayEvent(SQLModel, table=True):
    """What actually played, when, on which screen.

    The one report a signage customer eventually asks for, and the only honest answer to
    "did our advert actually run". Cheap to collect because the device already knows; the
    cost is volume, which is why `scripts/prune_events.py` exists.
    """

    __tablename__ = "play_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    device_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # SET NULL, not CASCADE: a proof-of-play record must outlive the file it refers to.
    # Deleting a video cannot be allowed to erase the evidence that it ran.
    media_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("media.id", ondelete="SET NULL"), nullable=True),
    )
    # Denormalised for exactly the same reason. Once `media_id` is nulled, this is the only
    # thing that makes the row mean anything to a human.
    filename: str = Field(default="")
    started_at: datetime = Field(sa_column=tz_column(nullable=False, index=True))
    seconds: int = Field(default=0)
