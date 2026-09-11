from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeviceSettingWrite(BaseModel):
    """Generic on purpose — validation is per-key, in the registry in
    services/device_settings.py, not in this shape. A new setting never needs a new schema."""

    value: Any


class DeviceSettingRead(BaseModel):
    key: str
    #: What the CMS wants — null if this row exists only to carry a reported observation for
    #: a key nobody has configured yet.
    value: Any
    updated_at: datetime
    #: What the device's own heartbeat most recently said this actually is, and when. Both
    #: null until the first heartbeat that reports this key.
    reported_value: Any = None
    reported_at: datetime | None = None
