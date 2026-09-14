"""Checkpoint: a software update pinned to one screen, now or at a scheduled time.

R2 is stubbed — `player_releases.find_release` answers for any version — so this exercises the
decision (`device_sync.available_update`) and the API round trip, not storage.

Run with:  .venv/bin/python -m scripts.check_software_updates
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import storage
from app.infra.db import engine
from app.main import app
from app.models import Account, Device, User, UserRole
from app.models.base import utcnow
from app.services import device_sync, player_releases
from app.services.devices import hash_token
from app.services.passwords import hash_password
from app.services.player_releases import PlayerRelease
from app.services.session import create_session_token

PREFIX = "chkswupd"
settings = get_settings()
failures: list[str] = []

player_releases.find_release = lambda version, current_key=None: PlayerRelease(
    version=version, key=f"apks/fortu-player-{version}.apk", size_bytes=1, uploaded_at="2026-09-14T00:00:00+00:00",
)
storage.presign_get = lambda key, ttl=None: f"https://fake/{key}"


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
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def main() -> None:
    cleanup()
    try:
        with Session(engine) as s:
            acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
            owner = User(account_id=acct.id, username=f"{PREFIX}-owner",
                         password_hash=hash_password("x"), display_name="O", role=UserRole.OWNER)
            device = Device(account_id=acct.id, name="Lobby", token_hash=hash_token("swupd-tok"), app_version="1.0.9")
            s.add_all([owner, device]); s.commit()
            owner_id, device_id = owner.id, device.id

        cms = TestClient(app)
        cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))
        screen = TestClient(app)
        screen.headers.update({"Authorization": "Bearer swupd-tok"})

        def offered() -> str | None:
            with Session(engine) as s:
                u = device_sync.available_update(s, s.get(Device, device_id))
                return u.version if u else None

        print("\npinned for later")
        later = (utcnow() + timedelta(hours=2)).isoformat()
        r = cms.post(f"/devices/{device_id}/update", json={"version": "1.1.0", "scheduled_at": later})
        check("pinning with a time returns 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        body = r.json()
        check("the screen carries the pin and its time",
              body.get("forced_update_version") == "1.1.0" and body.get("forced_update_at") is not None, str(body))
        check("before its time, nothing is offered", offered() is None, str(offered()))

        print("\nonce its time has passed")
        with Session(engine) as s:
            d = s.get(Device, device_id); d.forced_update_at = utcnow() - timedelta(minutes=1); s.add(d); s.commit()
        check("the pinned version is offered", offered() == "1.1.0", str(offered()))

        print("\npinned for now")
        r = cms.post(f"/devices/{device_id}/update", json={"version": "1.1.0"})
        check("pinning without a time returns 200 with no time", r.status_code == 200 and r.json()["forced_update_at"] is None, r.text[:120])
        check("offered straight away", offered() == "1.1.0", str(offered()))

        print("\nclearing")
        cms.post(f"/devices/{device_id}/update", json={"version": "1.1.0", "scheduled_at": later})
        r = cms.delete(f"/devices/{device_id}/update")
        check("cancel clears both the pin and its time",
              r.json()["forced_update_version"] is None and r.json()["forced_update_at"] is None, str(r.json()))

        cms.post(f"/devices/{device_id}/update", json={"version": "1.1.0", "scheduled_at": later})
        screen.post("/device/heartbeat", json={"app_version": "1.1.0"})
        with Session(engine) as s:
            d = s.get(Device, device_id)
            check("a screen reporting the pinned version clears both",
                  d.forced_update_version is None and d.forced_update_at is None,
                  f"{d.forced_update_version} {d.forced_update_at}")
    finally:
        cleanup()

    print()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed: {failures}")
    print("All software update checks passed.")


if __name__ == "__main__":
    main()
