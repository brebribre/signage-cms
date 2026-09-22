from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, DeviceForUser
from app.models import Account, Media, MediaStatus
from app.schemas.operations import (
    FleetEventRead,
    DeviceEventRead,
    DeviceHealthRead,
    PlayEventRead,
    StorageRead,
    LimitsRead,
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


@router.get("/limits", response_model=LimitsRead)
def limits(user: CurrentUser, session: DbSession) -> LimitsRead:
    """The account's plan as figures: screens used against the limit, storage used against the
    quota. Read-only here; the limits are set from the monitoring app."""
    from sqlmodel import func, select

    from app.services import devices as device_service

    account = session.get(Account, user.account_id)
    count = session.exec(
        select(func.count(Media.id)).where(
            Media.account_id == user.account_id, Media.status == MediaStatus.READY
        )
    ).one()
    return LimitsRead(
        screens_used=device_service.count_claimed(session, account_id=user.account_id),
        max_screens=account.max_screens if account else None,
        storage_used_bytes=operations.storage_used(session, user.account_id),
        storage_quota_bytes=account.storage_quota_bytes if account else None,
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


@router.get("/events/errors", response_model=list[FleetEventRead])
def fleet_errors(user: CurrentUser, session: DbSession) -> list[FleetEventRead]:
    """The newest errors across every screen the caller can reach, newest first."""
    return [
        FleetEventRead(
            id=e.id, level=e.level, message=e.message, created_at=e.created_at,
            device_id=e.device_id, device_name=name or "Unnamed screen",
        )
        for e, name in operations.recent_errors(session, user=user)
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
