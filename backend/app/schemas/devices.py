import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import DeviceOrientation


class DeviceRead(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    orientation: DeviceOrientation
    playlist_id: uuid.UUID | None
    screen_width: int | None
    screen_height: int | None
    app_version: str | None
    last_seen_at: datetime | None
    paired_at: datetime | None
