import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import EventLevel


class StorageRead(BaseModel):
    used_bytes: int
    quota_bytes: int | None
    file_count: int


class LimitsRead(BaseModel):
    """What the account may use, and how much of it is used — for the customer's own eyes.
    The limits themselves are set by Marien staff in the monitoring app; None is unlimited."""

    screens_used: int
    max_screens: int | None
    storage_used_bytes: int
    storage_quota_bytes: int | None
    file_count: int


class DeviceHealthRead(BaseModel):
    device_id: uuid.UUID
    name: str
    last_seen_at: datetime | None
    minutes_since_seen: float | None
    is_online: bool
    error_count_24h: int
    plays_24h: int
    app_version: str | None


class DeviceEventRead(BaseModel):
    id: uuid.UUID
    level: EventLevel
    message: str
    created_at: datetime


class FleetEventRead(DeviceEventRead):
    """An event with the screen it came from — the Overview's Errors tab lists these across
    every screen."""

    device_id: uuid.UUID
    device_name: str


class PlayEventRead(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID | None
    filename: str
    started_at: datetime
    seconds: int
