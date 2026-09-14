"""Checkpoint: optional start/end *times* on a rule's date range.

The scheduler half tests `_covers` and `_boundaries` directly with unsaved `Schedule` rows —
a bound time must trim only the first and last day (including a window that crosses
midnight), leave a time-less range exactly as it was, and become the `valid_until` boundary.
The API half saves a campaign through the real route: times round-trip, reach the generated
schedule rows, and invalid combinations are refused.

Run with:  .venv/bin/python -m scripts.check_schedule_bounds
"""

import uuid
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, Campaign, Device, Playlist, Schedule, User, UserRole
from app.services import scheduling
from app.services.devices import hash_token
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkbounds"
settings = get_settings()
failures: list[str] = []

JAKARTA = ZoneInfo("Asia/Jakarta")


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  ✗ {label} FAILED {detail}")


def cleanup() -> None:
    with Session(engine) as s:
        ids = [a.id for a in s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()]
        if ids:
            s.exec(delete(Campaign).where(Campaign.account_id.in_(ids)))
            s.exec(delete(Schedule).where(Schedule.account_id.in_(ids)))
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def local(stamp: str) -> datetime:
    """A Jakarta wall-clock moment, the shape `_covers` receives."""
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=JAKARTA)


def rule(starts: str, ends: str, **bounds) -> Schedule:
    return Schedule(
        account_id=uuid.uuid4(), device_id=uuid.uuid4(), playlist_id=uuid.uuid4(),
        days_of_week=0b1111111,
        starts_at=time.fromisoformat(starts), ends_at=time.fromisoformat(ends),
        **bounds,
    )


def scheduler_checks() -> None:
    # 2026-09-07 is a Monday.
    print("\na start time trims the first day, an end time the last")
    day = rule(
        "09:00", "17:00",
        start_date=date(2026, 9, 7), start_time=time(14, 0),
        end_date=date(2026, 9, 9), end_time=time(12, 0),
    )
    check("first day, before the start time → closed", not scheduling._covers(day, local("2026-09-07 10:00")))
    check("first day, exactly at the start time → open", scheduling._covers(day, local("2026-09-07 14:00")))
    check("a middle day is untouched", scheduling._covers(day, local("2026-09-08 10:00")))
    check("last day, before the end time → open", scheduling._covers(day, local("2026-09-09 11:59")))
    check("last day, exactly at the end time → closed", not scheduling._covers(day, local("2026-09-09 12:00")))
    check("before the start date → closed", not scheduling._covers(day, local("2026-09-06 15:00")))

    print("\nan end time cuts a window that crosses midnight")
    night = rule("22:00", "02:00", end_date=date(2026, 9, 9), end_time=time(23, 0))
    check("end day, before the end time → open", scheduling._covers(night, local("2026-09-09 22:30")))
    check("end day, at the end time → closed", not scheduling._covers(night, local("2026-09-09 23:00")))
    check("the spill past midnight is cut too", not scheduling._covers(night, local("2026-09-10 01:00")))

    print("\na date range with no times behaves as it always did")
    plain = rule("22:00", "02:00", end_date=date(2026, 9, 9))
    check("the end date's window still spills past midnight", scheduling._covers(plain, local("2026-09-10 01:00")))
    plain_start = rule("09:00", "17:00", start_date=date(2026, 9, 7))
    check("the start date's window opens at its own start", scheduling._covers(plain_start, local("2026-09-07 09:00")))

    print("\nbound times are boundaries")
    first = scheduling._boundaries([day], JAKARTA, local("2026-09-07 10:00"))
    check("before the start time, the next boundary is the start time",
          bool(first) and first[0] == local("2026-09-07 14:00"), str(first[:1]))
    last = scheduling._boundaries([day], JAKARTA, local("2026-09-09 11:00"))
    check("on the last day, the next boundary is the end time",
          bool(last) and last[0] == local("2026-09-09 12:00"), str(last[:1]))


def api_checks() -> None:
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner",
                     password_hash=hash_password("x"), display_name="O", role=UserRole.OWNER)
        playlist = Playlist(account_id=acct.id, name="Promo")
        device = Device(account_id=acct.id, name="Lobby", timezone="Asia/Jakarta",
                        token_hash=hash_token("bounds-tok"))
        s.add_all([owner, playlist, device]); s.commit()
        owner_id, playlist_id, device_id = owner.id, playlist.id, device.id

    cms = TestClient(app)
    cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))

    def body(**bounds) -> dict:
        return {
            "name": "Bounded", "device_ids": [str(device_id)],
            "rules": [{"playlist_id": str(playlist_id), "starts_at": "09:00:00", "ends_at": "17:00:00", **bounds}],
        }

    print("\ntimes round-trip through the campaign API")
    r = cms.post("/campaigns", json=body(
        start_date="2026-09-07", start_time="14:00:00", end_date="2026-09-09", end_time="12:00:00",
    ))
    check("create returns 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    if r.status_code == 201:
        saved = r.json()["campaign"]
        check("the response carries both times",
              saved["rules"][0]["start_time"] == "14:00:00" and saved["rules"][0]["end_time"] == "12:00:00",
              str(saved["rules"][0]))
        again = cms.get(f"/campaigns/{saved['id']}").json()
        check("reading it back returns the same times", again["rules"][0]["start_time"] == "14:00:00")
        with Session(engine) as s:
            row = s.exec(select(Schedule).where(Schedule.campaign_id == uuid.UUID(saved["id"]))).first()
            check("the generated schedule row stores them",
                  row is not None and row.start_time == time(14, 0) and row.end_time == time(12, 0))
            dev = s.get(Device, device_id)
            check("resolves to the playlist after the start time",
                  scheduling.resolve(s, dev, datetime(2026, 9, 7, 8, 0, tzinfo=UTC)).playlist_id == playlist_id)
            check("resolves to nothing before it, on the same day",
                  scheduling.resolve(s, dev, datetime(2026, 9, 7, 3, 0, tzinfo=UTC)).playlist_id is None)

    print("\ninvalid combinations are refused")
    r = cms.post("/campaigns", json=body(start_time="14:00:00"))
    check("a start time without a start date → 422", r.status_code == 422, str(r.status_code))
    r = cms.post("/campaigns", json=body(end_time="14:00:00"))
    check("an end time without an end date → 422", r.status_code == 422, str(r.status_code))
    r = cms.post("/campaigns", json=body(
        start_date="2026-09-07", start_time="14:00:00", end_date="2026-09-07", end_time="13:00:00",
    ))
    check("same day, ending before it starts → 422", r.status_code == 422, str(r.status_code))
    r = cms.post("/campaigns", json=body(
        start_date="2026-09-07", start_time="14:00:00", end_date="2026-09-07", end_time="18:00:00",
    ))
    check("same day, ending after it starts → 201", r.status_code == 201, str(r.status_code))


def main() -> None:
    cleanup()
    try:
        scheduler_checks()
        api_checks()
    finally:
        cleanup()
    print()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed: {failures}")
    print("All schedule bound checks passed.")


if __name__ == "__main__":
    main()
