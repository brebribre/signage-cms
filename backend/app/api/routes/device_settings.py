from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, DeviceForUser
from app.schemas.device_settings import (
    DeviceSettingRead,
    DeviceSettingWrite,
    PowerOverrideWrite,
    PowerStatusRead,
)
from app.services import device_settings as device_settings_service
from app.services import power as power_service
from app.services.device_settings import InvalidSetting, UnknownSetting

router = APIRouter(tags=["device-settings"])


def _read(row) -> DeviceSettingRead:
    return DeviceSettingRead.model_validate(row, from_attributes=True)


@router.get("/devices/{device_id}/settings", response_model=list[DeviceSettingRead])
def list_device_settings(device: DeviceForUser, session: DbSession) -> list[DeviceSettingRead]:
    return [_read(s) for s in device_settings_service.list_settings(session, device=device)]


@router.put("/devices/{device_id}/settings/{key}", response_model=DeviceSettingRead)
def set_device_setting(
    key: str, body: DeviceSettingWrite, device: DeviceForUser, session: DbSession
) -> DeviceSettingRead:
    """One route for every remotely-configurable setting — volume today, brightness, power
    on/off scheduling, the app lock password, and disabling the touchscreen later — because
    validation lives in the key registry (services/device_settings.py), not in the route.
    Adding a setting never means adding a route."""
    try:
        row = device_settings_service.set_setting(session, device=device, key=key, value=body.value)
    except UnknownSetting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown setting") from None
    except InvalidSetting as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return _read(row)


@router.get("/devices/{device_id}/power", response_model=PowerStatusRead)
def get_power(device: DeviceForUser, session: DbSession) -> PowerStatusRead:
    return PowerStatusRead(**power_service.status(session, device=device))


@router.put("/devices/{device_id}/power/override", response_model=PowerStatusRead)
def override_power(body: PowerOverrideWrite, device: DeviceForUser, session: DbSession) -> PowerStatusRead:
    """"Turn on/off now" — applied immediately, not staged with the rest of Settings. With a
    schedule on, it ends by itself at the schedule's next change."""
    power_service.set_override(session, device=device, state=body.state)
    return PowerStatusRead(**power_service.status(session, device=device))


@router.delete("/devices/{device_id}/power/override", response_model=PowerStatusRead)
def resume_power(device: DeviceForUser, session: DbSession) -> PowerStatusRead:
    """"Resume schedule" — drops any override so the schedule (or the default) decides again."""
    power_service.clear_override(session, device=device)
    return PowerStatusRead(**power_service.status(session, device=device))
