"""Remotely-configurable device settings: volume, brightness, power on/off scheduling, the app
lock password, and disabling the touchscreen — all through one generic mechanism, so the next
one is a registry entry, not a new subsystem.

Delivered to the screen through the exact same channel as a playlist or schedule change: a
`device_settings` row feeds `compute_version()` (services/device_sync.py), so a settings-only
edit bumps the manifest's ETag and the device picks it up on its next poll — nudged early by the
same MQTT "come poll" ping every other mutation in this app already sends. Nothing about the
manifest/version/MQTT path had to change to support this; only `compute_version` and
`build_manifest` had to start reading this table.
"""

import re
import uuid
from collections.abc import Callable
from typing import Any

from sqlmodel import Session, select

from app.models import Device, DeviceSetting
from app.models.base import utcnow
from app.models.schedule import ALL_DAYS
from app.services.errors import DomainError


class UnknownSetting(DomainError):
    pass


class InvalidSetting(DomainError):
    pass


def _percent_validator(label: str) -> Callable[[Any], int]:
    """Shared by every 0-100 setting (volume, brightness, …) — the shape is identical, only
    the name in the error message differs."""
    def _validate(value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not (0 <= value <= 100):
            raise InvalidSetting(f"{label} must be an integer between 0 and 100")
        return value
    return _validate


def _validate_touchscreen_disabled(value: Any) -> bool:
    if not isinstance(value, bool):
        raise InvalidSetting("touchscreen_disabled must be true or false")
    return value


def _validate_app_password(value: Any) -> str:
    # A PIN typed on the device's own screen to exit the player app, not an account
    # credential — no hashing here, the device needs the plaintext to compare against.
    if not isinstance(value, str) or not (4 <= len(value) <= 20):
        raise InvalidSetting("app password must be between 4 and 20 characters")
    return value


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_power_schedule(value: Any) -> dict:
    """Same day-bitmask + local time-of-day shape as a playlist `Schedule`, but for the
    device's power state rather than what it plays — kept a plain dict, not a new table, since
    (like every other setting) it only ever needs to round-trip through the manifest, never be
    queried on its own."""
    if not isinstance(value, dict):
        raise InvalidSetting("power schedule must be an object")
    enabled = value.get("enabled")
    days = value.get("days_of_week")
    power_on = value.get("power_on")
    power_off = value.get("power_off")

    if not isinstance(enabled, bool):
        raise InvalidSetting("power schedule: 'enabled' must be true or false")
    if not isinstance(days, int) or isinstance(days, bool) or not (0 < days <= ALL_DAYS):
        raise InvalidSetting("power schedule: select at least one day")
    if not isinstance(power_on, str) or not _TIME_RE.match(power_on):
        raise InvalidSetting("power schedule: 'power_on' must be HH:MM")
    if not isinstance(power_off, str) or not _TIME_RE.match(power_off):
        raise InvalidSetting("power schedule: 'power_off' must be HH:MM")
    if power_on == power_off:
        raise InvalidSetting("power schedule: on and off times must differ")

    return {"enabled": enabled, "days_of_week": days, "power_on": power_on, "power_off": power_off}


# One entry per remotely-configurable setting. Adding one is exactly this — a validator here, a
# row in the CMS form (DeviceSettingsContainer.vue's SETTINGS array) — no new route, no
# migration, no change to how the value reaches the device.
VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "volume": _percent_validator("volume"),
    "brightness": _percent_validator("brightness"),
    "touchscreen_disabled": _validate_touchscreen_disabled,
    "app_password": _validate_app_password,
    "power_schedule": _validate_power_schedule,
}


def list_settings(session: Session, *, device: Device) -> list[DeviceSetting]:
    return list(
        session.exec(
            select(DeviceSetting)
            .where(DeviceSetting.device_id == device.id)
            .order_by(DeviceSetting.key)
        ).all()
    )


def as_dict(session: Session, *, device_id: uuid.UUID) -> dict[str, Any]:
    """Keyed form for `compute_version`/`build_manifest` — every setting a device should
    apply, in one shape a player can iterate without knowing the individual keys in advance.
    Ordered by key so the hash `compute_version` folds this into is stable regardless of
    insertion order."""
    rows = session.exec(
        select(DeviceSetting)
        .where(DeviceSetting.device_id == device_id)
        .order_by(DeviceSetting.key)
    ).all()
    return {row.key: row.value for row in rows}


def set_setting(session: Session, *, device: Device, key: str, value: Any) -> DeviceSetting:
    validator = VALIDATORS.get(key)
    if validator is None:
        raise UnknownSetting(key)
    validated = validator(value)

    row = session.get(DeviceSetting, (device.id, key))
    if row is None:
        row = DeviceSetting(device_id=device.id, key=key, value=validated)
    else:
        row.value = validated
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)

    _notify(session, device)
    return row


def _notify(session: Session, device: Device) -> None:
    # Lazy import, same reasoning as schedules.py's `_notify`: device_sync now imports this
    # module at top level (to feed compute_version), so importing it back at module scope here
    # would be circular.
    from app.infra import mqtt
    from app.services import device_sync

    mqtt.notify_manifest_changed(
        device_id=device.id, version=device_sync.compute_version(session, device),
    )
