"""Checkpoint: device power — the weekly schedule, a temporary manual override, and what the
screen reports.

The rules half mirrors `player/app/src/test/java/com/fortu/player/PowerPlanTest.kt` case for
case: the player is what actually switches power, and the CMS shows what these decide, so the two
must agree. The API half drives the real routes — status, override, resume — plus the manifest a
screen receives and the heartbeat it reports back on.

Run with:  .venv/bin/python -m scripts.check_power
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, Device, DeviceSetting, User, UserRole
from app.services import power
from app.services.devices import hash_token
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkpower"
settings = get_settings()
failures: list[str] = []

JAKARTA = ZoneInfo("Asia/Jakarta")
WEEKDAYS = {"enabled": True, "days_of_week": 0b0011111, "power_on": "08:00", "power_off": "22:00"}
NIGHTLY = {"enabled": True, "days_of_week": 0b1111111, "power_on": "20:00", "power_off": "02:00"}


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
            devices = [d.id for d in s.exec(select(Device).where(Device.account_id.in_(ids))).all()]
            if devices:
                s.exec(delete(DeviceSetting).where(DeviceSetting.device_id.in_(devices)))
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def at(day: int, hour: int, minute: int = 0) -> datetime:
    """A Jakarta moment in September 2026, as UTC. 2026-09-07 is a Monday."""
    return datetime(2026, 9, day, hour, minute, tzinfo=JAKARTA).astimezone(UTC)


def rule_checks() -> None:
    print("\nthe schedule")
    r = power.resolve(WEEKDAYS, None, at(7, 10), JAKARTA)
    check("inside the window is on, by schedule", r.state == "on" and r.source == "schedule")
    check("…and the next change is the off time", r.until == at(7, 22), str(r.until))
    r = power.resolve(WEEKDAYS, None, at(7, 23), JAKARTA)
    check("after the off time is off until the next morning", r.state == "off" and r.until == at(8, 8), str(r.until))
    check("the start is inclusive", power.resolve(WEEKDAYS, None, at(7, 8), JAKARTA).state == "on")
    check("the end is exclusive", power.resolve(WEEKDAYS, None, at(7, 22), JAKARTA).state == "off")
    r = power.resolve(WEEKDAYS, None, at(12, 10), JAKARTA)
    check("an unselected day is off until the next selected morning",
          r.state == "off" and r.until == at(14, 8), str(r.until))
    r = power.resolve(NIGHTLY, None, at(8, 1), JAKARTA)
    check("a window crossing midnight stays on into the morning",
          r.state == "on" and r.until == at(8, 2), str(r.until))

    print("\nthe override")
    until = at(7, 22).isoformat()
    r = power.resolve(WEEKDAYS, {"state": "off", "until": until}, at(7, 15), JAKARTA)
    check("an unexpired override wins, and ends at its own end",
          r.state == "off" and r.source == "override" and r.until == at(7, 22))
    r = power.resolve(WEEKDAYS, {"state": "on", "until": at(7, 8).isoformat()}, at(7, 23), JAKARTA)
    check("an expired override hands back to the schedule", r.state == "off" and r.source == "schedule")
    r = power.resolve(WEEKDAYS, {"state": "off", "until": None}, at(7, 10), JAKARTA)
    check("an override with no end is ignored while a schedule is on", r.state == "on" and r.source == "schedule")
    r = power.resolve(None, {"state": "off", "until": None}, at(7, 10), JAKARTA)
    check("an override with no end stands when there is no schedule",
          r.state == "off" and r.source == "override" and r.until is None)
    r = power.resolve(None, None, at(7, 10), JAKARTA)
    check("nothing configured is on, by default", r.state == "on" and r.source == "default")


def api_checks() -> None:
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner",
                     password_hash=hash_password("x"), display_name="O", role=UserRole.OWNER)
        device = Device(account_id=acct.id, name="Lobby", timezone="Asia/Jakarta",
                        token_hash=hash_token("power-tok"))
        s.add_all([owner, device]); s.commit()
        owner_id, device_id = owner.id, device.id

    cms = TestClient(app)
    cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))
    screen = TestClient(app)
    screen.headers.update({"Authorization": "Bearer power-tok"})
    base = f"/devices/{device_id}"

    def manifest_settings() -> dict:
        return screen.get("/device/manifest").json()["settings"]

    print("\nstatus with nothing configured")
    r = cms.get(f"{base}/power")
    check("GET power returns 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("on, by default, no schedule", body["state"] == "on" and body["source"] == "default"
          and body["schedule_enabled"] is False and body["timezone"] == "Asia/Jakarta", str(body))

    print("\nthe retired manual switch")
    r = cms.put(f"{base}/settings/power_on", json={"value": False})
    check("power_on can no longer be set → 404", r.status_code == 404, str(r.status_code))
    with Session(engine) as s:
        s.add(DeviceSetting(device_id=device_id, key="power_on", value=False)); s.commit()
    check("a leftover power_on row never reaches the screen", "power_on" not in manifest_settings())

    print("\nthe manifest carries the timezone")
    check("device.timezone is the screen's", screen.get("/device/manifest").json()["device"]["timezone"] == "Asia/Jakarta")

    print("\nwith a schedule on")
    r = cms.put(f"{base}/settings/power_schedule", json={"value": WEEKDAYS})
    check("saving the schedule returns 200", r.status_code == 200, str(r.status_code))
    body = cms.get(f"{base}/power").json()
    check("status comes from the schedule", body["source"] == "schedule" and body["schedule_enabled"] is True, str(body))

    print("\nturning it off now")
    before = datetime.now(UTC)
    expected_state = "off" if body["state"] == "on" else "on"
    r = cms.put(f"{base}/power/override", json={"state": expected_state})
    check("override returns 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    expected_until = power.next_schedule_change(WEEKDAYS, before.astimezone(JAKARTA))
    got_until = datetime.fromisoformat(body["until"]) if body["until"] else None
    check("state flips, marked as an override", body["state"] == expected_state and body["source"] == "override", str(body))
    check("…and ends at the schedule's next change, in the screen's timezone",
          got_until is not None and abs(got_until - expected_until) < timedelta(minutes=1)
          and body["until"].endswith("+07:00"), f"{body['until']} vs {expected_until}")
    sent = manifest_settings().get("power_override")
    check("the screen receives the override with a UTC end",
          sent is not None and sent["state"] == expected_state and sent["until"].endswith("Z"), str(sent))

    print("\nwhat the screen reports")
    r = screen.post("/device/heartbeat", json={"reported_settings": {"power_state": "off"}})
    check("heartbeat returns 200", r.status_code == 200, str(r.status_code))
    body = cms.get(f"{base}/power").json()
    check("reported_state is recorded", body["reported_state"] == "off" and body["reported_at"] is not None, str(body))
    screen.post("/device/heartbeat", json={"reported_settings": {"power_state": "sideways"}})
    check("a nonsense report is dropped, not recorded", cms.get(f"{base}/power").json()["reported_state"] == "off")
    r = cms.put(f"{base}/settings/power_state", json={"value": "on"})
    check("power_state can't be set from the CMS → 404", r.status_code == 404, str(r.status_code))

    print("\nresuming the schedule")
    r = cms.delete(f"{base}/power/override")
    check("resume returns 200", r.status_code == 200, str(r.status_code))
    check("status is back to the schedule", r.json()["source"] == "schedule", str(r.json()))
    check("the screen stops receiving the override", "power_override" not in manifest_settings())

    print("\nwith no schedule, the switch simply stands")
    cms.put(f"{base}/settings/power_schedule", json={"value": {**WEEKDAYS, "enabled": False}})
    body = cms.put(f"{base}/power/override", json={"state": "off"}).json()
    check("off, as an override with no end", body["state"] == "off" and body["source"] == "override"
          and body["until"] is None and body["schedule_enabled"] is False, str(body))

    print("\nvalidation")
    r = cms.put(f"{base}/power/override", json={"state": "sideways"})
    check("an unknown state → 422", r.status_code == 422, str(r.status_code))
    r = cms.put(f"{base}/settings/power_override", json={"value": {"state": "off", "until": "tomorrow"}})
    check("an unparseable end → 422", r.status_code == 422, str(r.status_code))


def main() -> None:
    cleanup()
    try:
        rule_checks()
        api_checks()
    finally:
        cleanup()
    print()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed: {failures}")
    print("All power checks passed.")


if __name__ == "__main__":
    main()
