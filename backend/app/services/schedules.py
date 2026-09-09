"""Managing schedules from the CMS. Resolution itself lives in services/scheduling.py."""

import uuid
from datetime import time

from sqlmodel import Session, delete, select

from app.models import Device, Playlist, Schedule, User
from app.services.errors import DomainError

MAX_PRIORITY = 100


class ScheduleNotFound(DomainError):
    pass


class InvalidSchedule(DomainError):
    pass


def _validate(session: Session, user: User, playlist_id: uuid.UUID, days: int,
              starts_at: time, ends_at: time, priority: int) -> None:
    playlist = session.get(Playlist, playlist_id)
    # 404-shaped rather than 403: never confirm another account's playlist exists.
    if playlist is None or playlist.account_id != user.account_id:
        raise InvalidSchedule("that playlist is not available in this account")
    if not 0 < days <= 0b1111111:
        raise InvalidSchedule("select at least one day")
    if starts_at == ends_at:
        # Ambiguous rather than wrong: it could mean "zero length" or "all day", and guessing
        # either way would surprise half of the people who typed it.
        raise InvalidSchedule("start and end must differ — use 00:00–23:59 for a whole day")
    if not 0 <= priority <= MAX_PRIORITY:
        raise InvalidSchedule(f"priority must be between 0 and {MAX_PRIORITY}")


def list_for_device(session: Session, *, device: Device) -> list[Schedule]:
    return list(
        session.exec(
            select(Schedule)
            .where(Schedule.device_id == device.id)
            .order_by(Schedule.priority.desc(), Schedule.starts_at)
        ).all()
    )


def create(
    session: Session, *, user: User, device: Device, playlist_id: uuid.UUID,
    name: str, days_of_week: int, starts_at: time, ends_at: time, priority: int = 0,
) -> Schedule:
    _validate(session, user, playlist_id, days_of_week, starts_at, ends_at, priority)
    schedule = Schedule(
        account_id=user.account_id,
        device_id=device.id,
        playlist_id=playlist_id,
        name=name.strip(),
        days_of_week=days_of_week,
        starts_at=starts_at,
        ends_at=ends_at,
        priority=priority,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    _notify(session, device)
    return schedule


def get(session: Session, *, user: User, schedule_id: uuid.UUID) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None or schedule.account_id != user.account_id:
        raise ScheduleNotFound(str(schedule_id))
    return schedule


def update(
    session: Session, *, user: User, schedule: Schedule, playlist_id: uuid.UUID | None = None,
    name: str | None = None, days_of_week: int | None = None, starts_at: time | None = None,
    ends_at: time | None = None, priority: int | None = None, is_enabled: bool | None = None,
) -> Schedule:
    _validate(
        session, user,
        playlist_id or schedule.playlist_id,
        days_of_week if days_of_week is not None else schedule.days_of_week,
        starts_at or schedule.starts_at,
        ends_at or schedule.ends_at,
        priority if priority is not None else schedule.priority,
    )
    if playlist_id is not None:
        schedule.playlist_id = playlist_id
    if name is not None:
        schedule.name = name.strip()
    if days_of_week is not None:
        schedule.days_of_week = days_of_week
    if starts_at is not None:
        schedule.starts_at = starts_at
    if ends_at is not None:
        schedule.ends_at = ends_at
    if priority is not None:
        schedule.priority = priority
    if is_enabled is not None:
        schedule.is_enabled = is_enabled
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    device = session.get(Device, schedule.device_id)
    if device:
        _notify(session, device)
    return schedule


def remove(session: Session, *, schedule: Schedule) -> None:
    device_id = schedule.device_id
    session.exec(delete(Schedule).where(Schedule.id == schedule.id))
    session.commit()
    device = session.get(Device, device_id)
    if device:
        _notify(session, device)


def devices_scheduling(session: Session, playlist_id: uuid.UUID) -> list[str]:
    """Names of devices with a schedule pointing at this playlist.

    Used by playlist deletion, which must refuse for a scheduled playlist exactly as it does
    for a directly-assigned one — otherwise a delete would silently blank a screen at 9am
    next Monday, which is the worst possible time to discover it.
    """
    return list(
        session.exec(
            select(Device.name)
            .join(Schedule, Schedule.device_id == Device.id)
            .where(Schedule.playlist_id == playlist_id)
            .distinct()
        ).all()
    )


def devices_for_playlist(session: Session, playlist_id: uuid.UUID) -> list[Device]:
    """Same query as devices_scheduling, full rows instead of names — for
    playlists.py's MQTT fanout rather than a UI warning."""
    return list(
        session.exec(
            select(Device)
            .join(Schedule, Schedule.device_id == Device.id)
            .where(Schedule.playlist_id == playlist_id)
            .distinct()
        ).all()
    )


def _notify(session: Session, device: Device) -> None:
    """Best-effort push — see devices.update() for the same pattern applied to a direct
    device change. Never the source of truth: a screen that misses this still catches up on
    its next poll."""
    from app.infra import mqtt
    from app.services import device_sync

    mqtt.notify_manifest_changed(
        device_id=device.id, version=device_sync.compute_version(session, device),
    )
