from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.devices import DeviceRead
from app.services import devices as device_service

router = APIRouter(tags=["devices"])


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(user: CurrentUser, session: DbSession) -> list[DeviceRead]:
    """Screens this user may reach.

    Landed with Phase 9b rather than Phase 9, because assigning device grants needs something
    to assign them against. Pairing, claiming and unpairing arrive in Phase 8.
    """
    return [
        DeviceRead.model_validate(d, from_attributes=True)
        for d in device_service.list_devices(session, user=user)
    ]
