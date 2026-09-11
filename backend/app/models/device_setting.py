import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class DeviceSetting(SQLModel, table=True):
    """One remotely-configurable value on a device — volume today, and by the same mechanism,
    brightness, power on/off scheduling, the app lock password, and disabling the touchscreen
    later.

    A key-value row per setting, not a typed column per setting or one JSON blob on `Device`:
    adding a setting is a new `key` handled by the validator registry in
    `services/device_settings.py`, never a migration. `value` is JSON because different keys
    need different shapes (an int for volume, a nested schedule for power on/off) — the
    registry is what keeps each key's shape honest, not the column type.

    `value` and `reported_value` are two different things that happen to share a row:
    `value` is what the CMS *wants* (delivered to the device via the manifest — see
    `as_dict`), `reported_value` is what the device's own heartbeat most recently said it
    *actually is* right now (see `record_reported`). They can disagree — a change in flight,
    a device that ignored an unsupported value, someone adjusting volume by hand at the
    screen — and showing both rather than collapsing them into one is the point. `value` is
    nullable so a row can exist purely to carry a reported observation for a key the CMS has
    never configured.
    """

    __tablename__ = "device_settings"

    device_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    )
    key: str = Field(primary_key=True, max_length=64)
    value: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    #: What the device last said this setting actually is, and when. Both null until the
    #: first heartbeat that reports this key.
    reported_value: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
    reported_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))
