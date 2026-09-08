import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field

from app.services.schedules import MAX_PRIORITY


class ScheduleWrite(BaseModel):
    playlist_id: uuid.UUID
    name: str = Field(default="", max_length=80)
    # Bit 0 = Monday … bit 6 = Sunday. 127 = every day.
    days_of_week: int = Field(default=0b1111111, ge=1, le=0b1111111)
    starts_at: time
    ends_at: time
    priority: int = Field(default=0, ge=0, le=MAX_PRIORITY)


class ScheduleUpdate(BaseModel):
    playlist_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=80)
    days_of_week: int | None = Field(default=None, ge=1, le=0b1111111)
    starts_at: time | None = None
    ends_at: time | None = None
    priority: int | None = Field(default=None, ge=0, le=MAX_PRIORITY)
    is_enabled: bool | None = None


class ScheduleRead(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    playlist_id: uuid.UUID
    name: str
    days_of_week: int
    starts_at: time
    ends_at: time
    priority: int
    is_enabled: bool
    created_at: datetime


class ResolutionRead(BaseModel):
    """What a device is playing *right now* and why — so the CMS can show the effect of a
    schedule without waiting for the screen to report back."""

    playlist_id: uuid.UUID | None
    schedule_id: uuid.UUID | None
    schedule_name: str | None
    valid_until: datetime | None
    timezone: str
    device_local_time: datetime
