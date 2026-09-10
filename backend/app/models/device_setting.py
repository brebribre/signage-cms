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
    """

    __tablename__ = "device_settings"

    device_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    )
    key: str = Field(primary_key=True, max_length=64)
    value: Any = Field(sa_column=Column(JSON, nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
