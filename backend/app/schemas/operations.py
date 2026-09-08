import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import EventLevel


class StorageRead(BaseModel):
    used_bytes: int
    quota_bytes: int | None
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


class PlayEventRead(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID | None
    filename: str
    started_at: datetime
    seconds: int
