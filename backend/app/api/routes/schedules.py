import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, DeviceForUser
from app.schemas.schedules import (
    ResolutionRead,
    ScheduleRead,
    ScheduleUpdate,
    ScheduleWrite,
)
from app.services import scheduling
from app.services import schedules as schedule_service
from app.services.schedules import InvalidSchedule, ScheduleNotFound

router = APIRouter(tags=["schedules"])


def _read(s) -> ScheduleRead:
    return ScheduleRead.model_validate(s, from_attributes=True)


@router.get("/devices/{device_id}/schedules", response_model=list[ScheduleRead])
def list_schedules(device: DeviceForUser, session: DbSession) -> list[ScheduleRead]:
    return [_read(s) for s in schedule_service.list_for_device(session, device=device)]


@router.post(
    "/devices/{device_id}/schedules",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    body: ScheduleWrite, device: DeviceForUser, user: CurrentUser, session: DbSession
) -> ScheduleRead:
    try:
        schedule = schedule_service.create(
            session, user=user, device=device, playlist_id=body.playlist_id,
            name=body.name, days_of_week=body.days_of_week,
            starts_at=body.starts_at, ends_at=body.ends_at, priority=body.priority,
        )
    except InvalidSchedule as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return _read(schedule)


@router.get("/devices/{device_id}/schedules/now", response_model=ResolutionRead)
def resolve_now(device: DeviceForUser, session: DbSession) -> ResolutionRead:
    """What this screen is playing at this moment, resolved the same way the manifest does it.

    Exists so the CMS can show the *effect* of a schedule immediately — otherwise the only
    way to check a daypart rule is to wait for the window and look at the wall.
    """
    from datetime import UTC, datetime

    resolution = scheduling.resolve(session, device)
    zone = scheduling.device_zone(device)
    return ResolutionRead(
        playlist_id=resolution.playlist_id,
        schedule_id=resolution.schedule_id,
        schedule_name=resolution.schedule_name,
        valid_until=resolution.valid_until,
        timezone=str(zone),
        device_local_time=datetime.now(UTC).astimezone(zone),
    )


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: uuid.UUID, body: ScheduleUpdate, user: CurrentUser, session: DbSession
) -> ScheduleRead:
    try:
        schedule = schedule_service.get(session, user=user, schedule_id=schedule_id)
        updated = schedule_service.update(
            session, user=user, schedule=schedule,
            playlist_id=body.playlist_id, name=body.name,
            days_of_week=body.days_of_week, starts_at=body.starts_at,
            ends_at=body.ends_at, priority=body.priority, is_enabled=body.is_enabled,
        )
    except ScheduleNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found") from None
    except InvalidSchedule as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return _read(updated)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: uuid.UUID, user: CurrentUser, session: DbSession) -> None:
    try:
        schedule = schedule_service.get(session, user=user, schedule_id=schedule_id)
    except ScheduleNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found") from None
    schedule_service.remove(session, schedule=schedule)
