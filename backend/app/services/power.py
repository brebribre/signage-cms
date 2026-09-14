"""A screen's power state: its weekly on/off schedule plus a temporary manual override.

**The screen decides, not the CMS.** The player evaluates exactly these rules on its own clock
(`player/.../power/PowerPlan.kt`), because a screen has to go dark at 22:00 even with no network
at 22:00. This module is the CMS's copy of the same rules — to show what a screen *should* be
doing and why, and to work out when a manual override ends — and must be kept in step with it.

The rules, in order:

1. **An override that hasn't ended wins.** Overrides made while a schedule is on end at the
   schedule's next change, so nobody has to remember to undo one. An override with no end only
   counts while there is *no* schedule — switching a schedule on must never be silently blocked
   by an old manual setting.
2. **Otherwise an enabled schedule decides**: on inside the day's window, off outside it — and off
   all day on days that aren't selected. A window whose off time is earlier than its on time runs
   through midnight and belongs to the day it starts on, same as playlist schedules.
3. **Otherwise the screen is on.**
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.models import Device, DeviceSetting
from app.services import device_settings
from app.services.scheduling import device_zone

SCHEDULE_KEY = "power_schedule"
OVERRIDE_KEY = "power_override"
REPORTED_KEY = "power_state"

# Every weekly pattern repeats inside a week; one extra day covers a window crossing midnight.
LOOKAHEAD_DAYS = 8


def schedule_enabled(schedule: Any) -> bool:
    return isinstance(schedule, dict) and schedule.get("enabled") is True


def scheduled_on(schedule: dict, local: datetime) -> bool:
    """Whether the schedule wants the screen on at this device-local moment. Start inclusive,
    end exclusive."""
    on, off = time.fromisoformat(schedule["power_on"]), time.fromisoformat(schedule["power_off"])
    days = schedule["days_of_week"]
    t = local.time()
    weekday = local.weekday()  # Monday = 0, matching the bitmask

    if on < off:
        return bool(days & (1 << weekday)) and on <= t < off
    # Crosses midnight: late on a selected day, or early the morning after one.
    if t >= on:
        return bool(days & (1 << weekday))
    if t < off:
        return bool(days & (1 << ((weekday - 1) % 7)))
    return False


def next_schedule_change(schedule: dict, local: datetime) -> datetime | None:
    """The next moment the schedule's answer actually flips — skipping edges that change nothing,
    like an off time on a day the screen is already off. Device-local, like `local`."""
    zone = local.tzinfo
    current = scheduled_on(schedule, local)
    on, off = time.fromisoformat(schedule["power_on"]), time.fromisoformat(schedule["power_off"])
    edges = sorted(
        datetime.combine(local.date() + timedelta(days=offset), edge, tzinfo=zone)
        for offset in range(LOOKAHEAD_DAYS)
        for edge in (on, off)
    )
    for moment in edges:
        if moment > local and scheduled_on(schedule, moment) != current:
            return moment
    return None


def parse_instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


@dataclass
class Resolved:
    state: str  # "on" | "off"
    source: str  # "override" | "schedule" | "default"
    #: When `state` ends on its own — the override's end, or the schedule's next change. None
    #: means nothing will change it without someone acting.
    until: datetime | None


def resolve(schedule: Any, override: Any, now: datetime, zone: ZoneInfo) -> Resolved:
    local = now.astimezone(zone)
    has_schedule = schedule_enabled(schedule)

    if isinstance(override, dict) and override.get("state") in ("on", "off"):
        until = parse_instant(override.get("until"))
        if until is None and not has_schedule:
            return Resolved(override["state"], "override", None)
        if until is not None and now < until:
            return Resolved(override["state"], "override", until)

    if has_schedule:
        state = "on" if scheduled_on(schedule, local) else "off"
        return Resolved(state, "schedule", next_schedule_change(schedule, local))

    return Resolved("on", "default", None)


def status(session: Session, *, device: Device, now: datetime | None = None) -> dict[str, Any]:
    """What the CMS shows on the Power card: the state the screen should be in, why, until when,
    and what the screen itself last reported."""
    now = now or datetime.now(UTC)
    zone = device_zone(device)
    settings = device_settings.as_dict(session, device_id=device.id)
    resolved = resolve(settings.get(SCHEDULE_KEY), settings.get(OVERRIDE_KEY), now, zone)
    reported = session.get(DeviceSetting, (device.id, REPORTED_KEY))
    return {
        "state": resolved.state,
        "source": resolved.source,
        "until": resolved.until.astimezone(zone) if resolved.until else None,
        "schedule_enabled": schedule_enabled(settings.get(SCHEDULE_KEY)),
        "timezone": zone.key,
        "device_local_time": now.astimezone(zone),
        "reported_state": reported.reported_value if reported else None,
        "reported_at": reported.reported_at if reported else None,
    }


def set_override(session: Session, *, device: Device, state: str, now: datetime | None = None) -> None:
    """"Turn on/off now". With a schedule on, the override ends at the schedule's next change —
    always, no duration to pick; without one it simply stands until changed again."""
    now = now or datetime.now(UTC)
    zone = device_zone(device)
    schedule = device_settings.as_dict(session, device_id=device.id).get(SCHEDULE_KEY)
    until = next_schedule_change(schedule, now.astimezone(zone)) if schedule_enabled(schedule) else None
    device_settings.set_setting(
        session, device=device, key=OVERRIDE_KEY,
        value={"state": state, "until": until.astimezone(UTC).isoformat() if until else None},
    )


def clear_override(session: Session, *, device: Device) -> None:
    """"Resume schedule"."""
    device_settings.set_setting(session, device=device, key=OVERRIDE_KEY, value=None)
