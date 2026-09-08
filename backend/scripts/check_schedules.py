"""Phase 13 checkpoint: dayparting resolution, boundaries, and manifest integration.

Most of this tests `services/scheduling.resolve()` directly with an injected `now`, because
the interesting cases — midnight crossing, a daylight-saving jump, a boundary five minutes
away — cannot be triggered by waiting for the clock.

Run with:  .venv/bin/python -m scripts.check_schedules
"""

import uuid
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import storage
from app.infra.db import engine
from app.main import app
from app.models import (
    Account,
    Device,
    Media,
    MediaKind,
    MediaStatus,
    Playlist,
    PlaylistItem,
    Schedule,
    User,
    UserRole,
)
from app.services import scheduling
from app.services.devices import hash_token
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chksched"
settings = get_settings()
failures: list[str] = []

storage.presign_get = lambda key, ttl=None: f"https://fake/{key}?ttl={ttl}"


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  ✗ {label} FAILED {detail}")


def cleanup() -> None:
    with Session(engine) as s:
        accounts = s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()
        ids = [a.id for a in accounts]
        if ids:
            devs = s.exec(select(Device).where(Device.account_id.in_(ids))).all()
            if devs:
                s.exec(delete(Schedule).where(Schedule.device_id.in_([d.id for d in devs])))
            pls = s.exec(select(Playlist).where(Playlist.account_id.in_(ids))).all()
            if pls:
                s.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id.in_([p.id for p in pls])))
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


# Jakarta: UTC+7 with no daylight saving — the deployment's actual timezone.
JAKARTA = ZoneInfo("Asia/Jakarta")


def at(local: str, zone=JAKARTA) -> datetime:
    """A UTC instant from a local wall-clock string, so tests read in the screen's time."""
    return datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=zone).astimezone(UTC)


def main() -> None:
    cleanup()
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner",
                     password_hash=hash_password("x"), display_name="O", role=UserRole.OWNER)
        s.add(owner); s.flush()

        def mk_playlist(name):
            p = Playlist(account_id=acct.id, name=name); s.add(p); s.flush(); return p.id

        default_pl = mk_playlist("Default loop")
        breakfast_pl = mk_playlist("Breakfast menu")
        night_pl = mk_playlist("Night loop")
        promo_pl = mk_playlist("Promo")

        device = Device(
            account_id=acct.id, name="Cafe screen", timezone="Asia/Jakarta",
            token_hash=hash_token("sched-tok"), playlist_id=default_pl,
        )
        s.add(device); s.commit()
        for o in (owner, device):
            s.refresh(o)
        owner_id, device_id, acct_id = owner.id, device.id, acct.id

    cms = TestClient(app)
    cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))
    screen = TestClient(app)
    screen.headers.update({"Authorization": "Bearer sched-tok"})

    print("\nno schedules — the default playlist plays")
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        r = scheduling.resolve(s, dev, at("2026-09-07 10:00"))
        check("falls back to the device's default", r.playlist_id == default_pl)
        check("no schedule named", r.schedule_name is None)
        check("valid_until is None when nothing is scheduled", r.valid_until is None)

    print("\na weekday breakfast window")
    r = cms.post(f"/devices/{device_id}/schedules", json={
        "playlist_id": str(breakfast_pl), "name": "Breakfast",
        "days_of_week": 0b0011111,  # Mon–Fri
        "starts_at": "07:00:00", "ends_at": "11:00:00", "priority": 10,
    })
    check("create returns 201", r.status_code == 201, str(r.status_code))
    breakfast_id = r.json()["id"]

    with Session(engine) as s:
        dev = s.get(Device, device_id)
        # 2026-09-07 is a Monday.
        check("inside the window → breakfast",
              scheduling.resolve(s, dev, at("2026-09-07 08:00")).playlist_id == breakfast_pl)
        check("before it opens → default",
              scheduling.resolve(s, dev, at("2026-09-07 06:59")).playlist_id == default_pl)
        check("exactly at the start → breakfast (inclusive)",
              scheduling.resolve(s, dev, at("2026-09-07 07:00")).playlist_id == breakfast_pl)
        check("exactly at the end → default (exclusive)",
              scheduling.resolve(s, dev, at("2026-09-07 11:00")).playlist_id == default_pl)
        # 2026-09-12 is a Saturday.
        check("Saturday is excluded by the day mask",
              scheduling.resolve(s, dev, at("2026-09-12 08:00")).playlist_id == default_pl)
        check("the winning schedule is named",
              scheduling.resolve(s, dev, at("2026-09-07 08:00")).schedule_name == "Breakfast")

    print("\ntimezone is the device's, not the server's")
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        # 01:00 UTC == 08:00 Jakarta → inside the window.
        utc_1am = datetime(2026, 9, 7, 1, 0, tzinfo=UTC)
        check("08:00 Jakarta resolves as inside, though it is 01:00 UTC",
              scheduling.resolve(s, dev, utc_1am).playlist_id == breakfast_pl)
        # Same instant for a screen in London is 02:00 — outside.
        dev.timezone = "Europe/London"; s.add(dev); s.commit(); s.refresh(dev)
        check("the same instant is outside the window for a London screen",
              scheduling.resolve(s, dev, utc_1am).playlist_id == default_pl)
        dev.timezone = "Asia/Jakarta"; s.add(dev); s.commit()

    print("\na window that crosses midnight")
    r = cms.post(f"/devices/{device_id}/schedules", json={
        "playlist_id": str(night_pl), "name": "Night",
        "days_of_week": 0b1111111,
        "starts_at": "22:00:00", "ends_at": "02:00:00", "priority": 5,
    })
    check("create returns 201", r.status_code == 201, str(r.status_code))
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        check("23:00 is inside", scheduling.resolve(s, dev, at("2026-09-07 23:00")).playlist_id == night_pl)
        check("01:00 next morning is still inside",
              scheduling.resolve(s, dev, at("2026-09-08 01:00")).playlist_id == night_pl)
        check("03:00 is outside", scheduling.resolve(s, dev, at("2026-09-08 03:00")).playlist_id == default_pl)
        check("21:59 is outside", scheduling.resolve(s, dev, at("2026-09-07 21:59")).playlist_id == default_pl)

    print("\noverlapping windows resolve by priority")
    r = cms.post(f"/devices/{device_id}/schedules", json={
        "playlist_id": str(promo_pl), "name": "Promo",
        "days_of_week": 0b1111111,
        "starts_at": "08:00:00", "ends_at": "09:00:00", "priority": 50,
    })
    check("create returns 201", r.status_code == 201, str(r.status_code))
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        check("higher priority wins inside the overlap",
              scheduling.resolve(s, dev, at("2026-09-07 08:30")).playlist_id == promo_pl)
        check("the lower-priority window resumes after it",
              scheduling.resolve(s, dev, at("2026-09-07 09:30")).playlist_id == breakfast_pl)

    print("\nvalid_until points at the next boundary")
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        res = scheduling.resolve(s, dev, at("2026-09-07 08:30"))
        expected = at("2026-09-07 09:00")
        check("during the promo, expires when the promo ends",
              res.valid_until == expected, f"{res.valid_until} vs {expected}")

        res2 = scheduling.resolve(s, dev, at("2026-09-07 12:00"))
        # Next boundary that day is the 22:00 night window opening.
        check("outside all windows, expires when the next one opens",
              res2.valid_until == at("2026-09-07 22:00"), str(res2.valid_until))

        res3 = scheduling.resolve(s, dev, at("2026-09-07 07:30"))
        check("a higher-priority window opening counts as a boundary",
              res3.valid_until == at("2026-09-07 08:00"), str(res3.valid_until))

    print("\nthe manifest reflects the schedule")
    with Session(engine) as s:
        # Give the scheduled playlist an item so the manifest is non-empty.
        m = Media(account_id=acct_id, filename="promo.png", kind=MediaKind.IMAGE,
                  mime_type="image/png", size_bytes=100, storage_key="k/p",
                  checksum="md5:promo", status=MediaStatus.READY)
        s.add(m); s.flush()
        s.add(PlaylistItem(playlist_id=promo_pl, media_id=m.id, position=0, duration_seconds=10))
        s.commit()

    body = screen.get("/device/manifest").json()
    check("manifest carries valid_until", body.get("valid_until") is not None, str(body.get("valid_until")))
    check("manifest names the active schedule when one is",
          "schedule_name" in body, str(body.get("schedule_name")))

    print("\nthe version hash tracks the schedule")
    # Pinned to a moment inside the promo window. Asserting this against the real clock would
    # pass or fail depending on the hour the suite happens to run — at 17:25 no window is near,
    # so every edit below would legitimately leave the hash untouched.
    inside_promo = at("2026-09-07 08:30")
    before_promo = at("2026-09-07 07:30")
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        from app.services import device_sync

        v_promo = device_sync.compute_version(s, dev, inside_promo)
        sched = s.exec(select(Schedule).where(Schedule.name == "Promo")).first()

        # Narrowing the window so 08:30 falls outside it changes what plays.
        sched.ends_at = time(8, 15)
        s.add(sched); s.commit(); s.refresh(dev)
        check("editing a schedule changes the version",
              device_sync.compute_version(s, dev, inside_promo) != v_promo)
        sched.ends_at = time(9, 0); s.add(sched); s.commit(); s.refresh(dev)

        # And moving a boundary changes it even from *outside* the window, because the
        # device's `valid_until` — when it should next wake — has moved.
        v_before = device_sync.compute_version(s, dev, before_promo)
        sched.starts_at = time(8, 30)
        s.add(sched); s.commit(); s.refresh(dev)
        check("moving a boundary changes the version even from outside the window",
              device_sync.compute_version(s, dev, before_promo) != v_before)
        sched.starts_at = time(8, 0); s.add(sched); s.commit(); s.refresh(dev)

        v_enabled = device_sync.compute_version(s, dev, inside_promo)
        sched.is_enabled = False
        s.add(sched); s.commit(); s.refresh(dev)
        check("disabling a schedule changes the version",
              device_sync.compute_version(s, dev, inside_promo) != v_enabled)
        sched.is_enabled = True; s.add(sched); s.commit()

        # And the converse: an unrelated edit at a moment it cannot affect must NOT churn the
        # hash, or every screen re-fetches for nothing.
        far_off = at("2026-09-07 15:00")
        v_far = device_sync.compute_version(s, dev, far_off)
        check("the same moment hashes identically when nothing changed",
              device_sync.compute_version(s, dev, far_off) == v_far)

    print("\nvalidation")
    for label, payload, code in [
        ("another account's playlist is refused",
         {"playlist_id": str(uuid.uuid4()), "starts_at": "09:00:00", "ends_at": "10:00:00"}, 422),
        ("identical start and end is refused",
         {"playlist_id": str(default_pl), "starts_at": "09:00:00", "ends_at": "09:00:00"}, 422),
        ("no days selected is refused",
         {"playlist_id": str(default_pl), "days_of_week": 0,
          "starts_at": "09:00:00", "ends_at": "10:00:00"}, 422),
    ]:
        check(label, cms.post(f"/devices/{device_id}/schedules", json=payload).status_code == code)

    print("\nplaylist deletion respects schedules")
    r = cms.delete(f"/playlists/{promo_pl}")
    check("deleting a scheduled playlist is 409", r.status_code == 409, str(r.status_code))
    check("...and names the screen", "Cafe screen" in r.json()["detail"], r.json()["detail"])

    print("\nthe /now endpoint explains the current state")
    now = cms.get(f"/devices/{device_id}/schedules/now").json()
    check("reports the device timezone", now["timezone"] == "Asia/Jakarta", str(now["timezone"]))
    check("reports a resolved playlist", now["playlist_id"] is not None)
    check("reports the device's local time", now["device_local_time"] is not None)

    print("\nscoping")
    anon = TestClient(app)
    check("anonymous cannot list schedules",
          anon.get(f"/devices/{device_id}/schedules").status_code == 401)
    check("a device token cannot manage schedules",
          screen.get(f"/devices/{device_id}/schedules").status_code == 401)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All schedule checks passed.")


if __name__ == "__main__":
    main()
