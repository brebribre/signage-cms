from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, DeviceForUser
from app.models import Account, Media, MediaStatus
from app.schemas.operations import (
    DeviceEventRead,
    DeviceHealthRead,
    PlayEventRead,
    StorageRead,
)
from app.services import operations

router = APIRouter(tags=["operations"])


@router.get("/storage", response_model=StorageRead)
def storage(user: CurrentUser, session: DbSession) -> StorageRead:
    from sqlmodel import func, select

    account = session.get(Account, user.account_id)
    count = session.exec(
        select(func.count(Media.id)).where(
            Media.account_id == user.account_id, Media.status == MediaStatus.READY
        )
    ).one()
    return StorageRead(
        used_bytes=operations.storage_used(session, user.account_id),
        quota_bytes=account.storage_quota_bytes if account else None,
        file_count=int(count),
    )


@router.get("/health/devices", response_model=list[DeviceHealthRead])
def fleet_health(user: CurrentUser, session: DbSession) -> list[DeviceHealthRead]:
    """One row per screen this user may reach — the fleet at a glance.

    Scoped through the same rules as everything else: a manager sees exactly the screens they
    were granted, not the whole estate.
    """
    return [
        DeviceHealthRead(**h.__dict__)
        for h in operations.fleet_health(session, user=user)
    ]


@router.get("/devices/{device_id}/events", response_model=list[DeviceEventRead])
def device_events(device: DeviceForUser, session: DbSession) -> list[DeviceEventRead]:
    return [
        DeviceEventRead.model_validate(e, from_attributes=True)
        for e in operations.recent_events(session, device=device)
    ]


@router.get("/devices/{device_id}/plays", response_model=list[PlayEventRead])
def device_plays(device: DeviceForUser, session: DbSession) -> list[PlayEventRead]:
    """Proof of play: what this screen actually showed, newest first."""
    return [
        PlayEventRead.model_validate(p, from_attributes=True)
        for p in operations.recent_plays(session, device=device)
    ]
