"""Resolving *what a screen should be playing right now*.

**All of this happens server-side, deliberately.** The device asks "what do I play?" and is
told a playlist id — it never evaluates a calendar. Putting the rules on the device would mean
every screen needing the right clock, the right timezone and the same version of the rules:
three independent ways for a wall of screens to disagree with the CMS, all of them invisible
until someone notices the wrong thing on a wall.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, select

from app.models import Device, Schedule

# How far ahead to look for the next boundary. A week covers every weekly pattern, so if
# nothing is found inside it, nothing will change on its own.
LOOKAHEAD_DAYS = 8


@dataclass
class Resolution:
    """What to play, and until when."""

    playlist_id: uuid.UUID | None
    schedule_id: uuid.UUID | None
    schedule_name: str | None
    #: When this answer stops being true — the next boundary of any schedule on this
    #: device. None means nothing is scheduled and the answer never expires on its own.
    valid_until: datetime | None


def device_zone(device: Device) -> ZoneInfo:
    """The screen's timezone, falling back to UTC rather than raising.

    A device row with a typo'd or since-removed IANA name must not take a screen off the air —
    it should keep playing on a defensible clock while somebody fixes the setting.
    """
    try:
        return ZoneInfo(device.timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _covers(schedule: Schedule, local: datetime) -> bool:
    """Whether a schedule's window is open at this local wall-clock moment.

    Handles windows that cross midnight (22:00–02:00), where `ends_at <= starts_at`. In that
    case the window belongs to the day it *starts* on, so 01:00 on Tuesday is inside Monday's
    22:00–02:00 window — which is what anyone writing "22:00 to 02:00 on Monday" means.
    """
    t = local.time()
    weekday = local.weekday()  # Monday = 0, matching the bitmask

    if schedule.starts_at < schedule.ends_at:
        # Ordinary same-day window.
        return bool(schedule.days_of_week & (1 << weekday)) and schedule.starts_at <= t < schedule.ends_at

    # Crosses midnight: either late on the start day, or early on the following day.
    if t >= schedule.starts_at:
        return bool(schedule.days_of_week & (1 << weekday))
    if t < schedule.ends_at:
        previous = (weekday - 1) % 7
        return bool(schedule.days_of_week & (1 << previous))
    return False


def _rank(schedule: Schedule) -> tuple[int, time]:
    """Higher priority wins; ties go to the window that starts later.

    A later start is the more specific instruction — "everything from 09:00, but this from
    12:00" reads as the 12:00 rule taking over, and that is what people expect without having
    to think about priorities at all.
    """
    return (schedule.priority, schedule.starts_at)


def _boundaries(schedules: list[Schedule], zone: ZoneInfo, now_local: datetime) -> list[datetime]:
    """Every moment in the near future at which the answer could change.

    Both edges of every window on every upcoming day. Cheap — a handful of schedules over
    eight days — and far more robust than trying to reason about which edge matters next.
    """
    out: list[datetime] = []
    start_day = now_local.date()
    for offset in range(LOOKAHEAD_DAYS):
        day = start_day + timedelta(days=offset)
        for s in schedules:
            for edge in (s.starts_at, s.ends_at):
                moment = datetime.combine(day, edge, tzinfo=zone)
                if moment > now_local:
                    out.append(moment)
    return sorted(out)


def resolve(session: Session, device: Device, now: datetime | None = None) -> Resolution:
    """What this screen plays right now, and when that answer expires."""
    now_utc = now or datetime.now(UTC)
    zone = device_zone(device)
    now_local = now_utc.astimezone(zone)

    schedules = list(
        session.exec(
            select(Schedule).where(
                Schedule.device_id == device.id, Schedule.is_enabled.is_(True)
            )
        ).all()
    )

    active = [s for s in schedules if _covers(s, now_local)]
    winner = max(active, key=_rank) if active else None

    # No window open → the device's default playlist. Schedules are an override layer, so a
    # screen is never left blank just because nothing is scheduled at 3am.
    playlist_id = winner.playlist_id if winner else device.playlist_id

    # The next boundary of *any* schedule, not just the winning one: a higher-priority window
    # opening is just as much a change as the current one closing.
    upcoming = _boundaries(schedules, zone, now_local)
    valid_until = upcoming[0].astimezone(UTC) if upcoming else None

    return Resolution(
        playlist_id=playlist_id,
        schedule_id=winner.id if winner else None,
        schedule_name=winner.name if winner else None,
        valid_until=valid_until,
    )
