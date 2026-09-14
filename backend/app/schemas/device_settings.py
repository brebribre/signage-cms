from datetime import datetime
from typing import Any, Literal

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


class PowerOverrideWrite(BaseModel):
    state: Literal["on", "off"]


class PowerStatusRead(BaseModel):
    """What the Power card shows — see services/power.py for the rules behind `state`/`source`."""

    state: Literal["on", "off"]
    source: Literal["override", "schedule", "default"]
    #: When `state` ends on its own (the override's end, or the schedule's next change), in the
    #: device's own timezone. Null when nothing will change it without someone acting.
    until: datetime | None
    schedule_enabled: bool
    timezone: str
    device_local_time: datetime
    #: What the screen itself last said it is, and when — null until a player new enough to
    #: report power has heartbeated.
    reported_state: Literal["on", "off"] | None
    reported_at: datetime | None
