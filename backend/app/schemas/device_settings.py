from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeviceSettingWrite(BaseModel):
    """Generic on purpose — validation is per-key, in the registry in
    services/device_settings.py, not in this shape. A new setting never needs a new schema."""

    value: Any


class DeviceSettingRead(BaseModel):
    key: str
    value: Any
    updated_at: datetime
