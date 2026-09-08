import uuid
from datetime import datetime, time

from sqlalchemy import Column, ForeignKey, Time
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow

# Bit 0 = Monday … bit 6 = Sunday, matching Python's `date.weekday()`. A bitmask rather than
# seven booleans or a join table: "weekdays" is one integer, it compares in one operation,
# and the set of days is fixed forever.
ALL_DAYS = 0b1111111
WEEKDAYS = 0b0011111
WEEKENDS = 0b1100000


class Schedule(SQLModel, table=True):
    """A window during which a device plays something other than its default playlist.

    Schedules are an **override layer, not a replacement**: `Device.playlist_id` remains what
    a screen plays normally, and a schedule only takes over while its window is open. A
    device with no matching schedule right now falls back to its default, which means adding
    a schedule can never leave a screen with nothing to show.
    """

    __tablename__ = "schedules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    device_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # CASCADE, with a friendly 409 enforced in services/playlists.py before it can fire —
    # a schedule pointing at a playlist that no longer exists would be worse than the
    # schedule disappearing with it.
    playlist_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    )

    name: str = Field(default="")
    days_of_week: int = Field(default=ALL_DAYS)

    # Local wall-clock time on the *device's* timezone, not the server's. TIME WITHOUT TIME
    # ZONE deliberately: "opens at 09:00" means 09:00 wherever the screen is, and storing an
    # offset here would freeze it against daylight saving.
    starts_at: time = Field(sa_column=Column(Time(timezone=False), nullable=False))
    ends_at: time = Field(sa_column=Column(Time(timezone=False), nullable=False))

    # Higher wins when windows overlap. Ties break toward the later `starts_at`, on the
    # reasoning that a window starting later is the more specific one.
    priority: int = Field(default=0)

    is_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
