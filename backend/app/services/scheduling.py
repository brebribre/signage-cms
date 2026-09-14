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
    #: Which Campaign produced the winning schedule, if any — null both when nothing is
    #: active and when the winning schedule was created directly (predates Campaigns, or was
    #: made via the standalone per-device Schedule API rather than a Campaign).
    campaign_id: uuid.UUID | None
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


def _in_date_range(schedule: Schedule, day: date) -> bool:
    """Whether `day` falls within the schedule's optional calendar-date bounds, both inclusive.
    A null bound is unbounded on that side — the common case, an ordinary recurring schedule
    with no date range at all, always passes."""
    if schedule.start_date is not None and day < schedule.start_date:
        return False
    if schedule.end_date is not None and day > schedule.end_date:
        return False
    return True


def _within_bound_times(schedule: Schedule, local: datetime) -> bool:
    """The optional time of day on the date bounds, checked against the actual moment rather
    than the window's "belongs to" day. `_in_date_range` still decides which days are in; this
    only trims the first and last of them — "from Sep 1 14:00" must not play Sep 1's 09:00
    window, and "until Oct 15 18:00" must cut a window still open at 18:00, including one that
    crossed midnight. A null time leaves its bound exactly as `_in_date_range` has it."""
    wall = local.replace(tzinfo=None)
    if schedule.start_date is not None and schedule.start_time is not None:
        if wall < datetime.combine(schedule.start_date, schedule.start_time):
            return False
    if schedule.end_date is not None and schedule.end_time is not None:
        if wall >= datetime.combine(schedule.end_date, schedule.end_time):
            return False
    return True


def _covers(schedule: Schedule, local: datetime) -> bool:
    """Whether a schedule's window is open at this local wall-clock moment.

    Handles windows that cross midnight (22:00–02:00), where `ends_at <= starts_at`. In that
    case the window belongs to the day it *starts* on, so 01:00 on Tuesday is inside Monday's
    22:00–02:00 window — which is what anyone writing "22:00 to 02:00 on Monday" means. The
    optional date range is checked against that same "belongs to" day, not `local.date()`
    directly — a range ending on Monday must still cover the 01:00 stretch that spilled into
    Tuesday, and one starting Tuesday must not claim Monday night's leftovers.
    """
    if not _within_bound_times(schedule, local):
        return False

    t = local.time()
    weekday = local.weekday()  # Monday = 0, matching the bitmask

    if schedule.starts_at < schedule.ends_at:
        # Ordinary same-day window.
        return (
            _in_date_range(schedule, local.date())
            and bool(schedule.days_of_week & (1 << weekday))
            and schedule.starts_at <= t < schedule.ends_at
        )

    # Crosses midnight: either late on the start day, or early on the following day.
    if t >= schedule.starts_at:
        return _in_date_range(schedule, local.date()) and bool(schedule.days_of_week & (1 << weekday))
    if t < schedule.ends_at:
        previous_day = local.date() - timedelta(days=1)
        previous_weekday = (weekday - 1) % 7
        return _in_date_range(schedule, previous_day) and bool(schedule.days_of_week & (1 << previous_weekday))
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

    A date range contributes two more kinds of boundary beyond its daily window: the date range
    is skipped for days it doesn't cover at all (a schedule that expired last week must not go
    on manufacturing phantom future edges), and the instant the range itself opens or closes —
    midnight of `start_date`, and midnight the day after `end_date` — is added directly, since
    neither is a `starts_at`/`ends_at` edge on any single day and would otherwise go unreported,
    leaving `valid_until` claiming an answer holds longer than a range boundary actually allows.
    """
    out: list[datetime] = []
    start_day = now_local.date()
    for offset in range(LOOKAHEAD_DAYS):
        day = start_day + timedelta(days=offset)
        for s in schedules:
            if not _in_date_range(s, day):
                continue
            for edge in (s.starts_at, s.ends_at):
                moment = datetime.combine(day, edge, tzinfo=zone)
                if moment > now_local:
                    out.append(moment)
    for s in schedules:
        # With a bound time, the range opens/closes at that moment instead of at midnight.
        if s.start_date is not None:
            moment = datetime.combine(s.start_date, s.start_time or time.min, tzinfo=zone)
            if moment > now_local:
                out.append(moment)
        if s.end_date is not None:
            moment = (
                datetime.combine(s.end_date, s.end_time, tzinfo=zone)
                if s.end_time is not None
                else datetime.combine(s.end_date + timedelta(days=1), time.min, tzinfo=zone)
            )
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
        campaign_id=winner.campaign_id if winner else None,
        valid_until=valid_until,
    )
