"""Phase 8 checkpoint: the pairing handshake, device tokens, and screen management.

Run with:  .venv/bin/python -m scripts.check_devices
"""

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import (
    Account,
    Device,
    DeviceAccess,
    Playlist,
    User,
    UserRole,
)
from app.models.base import utcnow
from app.services import devices as device_service
from app.services.devices import CLAIM_ATTEMPT_LIMIT
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkdev"
settings = get_settings()
failures: list[str] = []


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
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Playlist).where(Playlist.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
        # Unclaimed rows have no account, so they need their own sweep.
        s.exec(delete(Device).where(Device.account_id.is_(None)))
        s.commit()
    device_service._claim_attempts.clear()


def client_for(uid: uuid.UUID) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(uid))
    return c


def main() -> None:
    cleanup()
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner", password_hash=hash_password("x"),
                     display_name="O", role=UserRole.OWNER)
        mgr = User(account_id=acct.id, username=f"{PREFIX}-mgr", password_hash=hash_password("x"),
                   display_name="M", role=UserRole.MANAGER)
        other = Account(name=f"{PREFIX} other"); s.add(other); s.flush()
        outsider = User(account_id=other.id, username=f"{PREFIX}-out", password_hash=hash_password("x"),
                        display_name="X", role=UserRole.OWNER)
        s.add(owner); s.add(mgr); s.add(outsider); s.commit()
        for u in (owner, mgr, outsider):
            s.refresh(u)
        owner_id, mgr_id, out_id = owner.id, mgr.id, outsider.id
        pl = Playlist(account_id=acct.id, name=f"{PREFIX} loop"); s.add(pl)
        foreign_pl = Playlist(account_id=other.id, name=f"{PREFIX} theirs"); s.add(foreign_pl)
        s.commit(); s.refresh(pl); s.refresh(foreign_pl)
        playlist_id, foreign_playlist_id = pl.id, foreign_pl.id

    o, m, x = client_for(owner_id), client_for(mgr_id), client_for(out_id)
    device = TestClient(app)   # no cookie: this stands in for the screen

    print("\nthe device asks for a code")
    r = device.post("/devices/pair")
    check("pair is unauthenticated and returns 201", r.status_code == 201, str(r.status_code))
    pair = r.json()
    code, poll_token = pair["pairing_code"], pair["poll_token"]
    check("the code is 6 characters", len(code) == 6, code)
    check(
        "the alphabet has no ambiguous glyphs",
        not set(code) & set("O0I1L"),
        f"code={code}",
    )
    check("a poll token is issued separately from the code", poll_token != code)

    print("\nnobody can see it yet")
    check("an unclaimed device is not in any account's list", o.get("/devices").json() == [])
    check("polling before a claim says not claimed",
          device.get(f"/devices/pair/{poll_token}").json()["claimed"] is False)
    check("no token is handed out before a claim",
          device.get(f"/devices/pair/{poll_token}").json()["device_token"] is None)

    print("\na human types the code")
    check("claiming with a wrong code is 404",
          o.post("/devices/claim", json={"pairing_code": "ZZZZZZ", "name": "n"}).status_code == 404)
    check("claiming is not anonymous",
          TestClient(app).post("/devices/claim",
                               json={"pairing_code": code, "name": "n"}).status_code == 401)
    r = o.post("/devices/claim", json={"pairing_code": code.lower(), "name": "Lobby", "location": "Front desk"})
    check("claiming with the code in lower case works", r.status_code == 201, str(r.status_code))
    claimed = r.json()
    device_id = claimed["id"]
    check("it takes the name it was given", claimed["name"] == "Lobby")
    check("it now appears in the account list", [d["id"] for d in o.get("/devices").json()] == [device_id])
    check("another account still cannot see it", x.get("/devices").json() == [])
    check("the same code cannot be claimed twice",
          o.post("/devices/claim", json={"pairing_code": code, "name": "again"}).status_code == 404)

    print("\nthe device collects its token, once")
    r = device.get(f"/devices/pair/{poll_token}")
    body = r.json()
    check("the poll now reports claimed", body["claimed"] is True)
    token = body["device_token"]
    check("a device token is returned", bool(token))
    check("the device learns its name", body["name"] == "Lobby")
    check("a second poll with the same token is 404",
          device.get(f"/devices/pair/{poll_token}").status_code == 404)
    with Session(engine) as s:
        row = s.get(Device, uuid.UUID(device_id))
        check("only a hash is stored, never the token",
              row.token_hash == device_service.hash_token(token) and token not in (row.token_hash or ""))
        check("the pairing code is cleared once claimed", row.pairing_code is None)

    print("\nthe device token authenticates")
    with Session(engine) as s:
        found = device_service.authenticate(s, bearer=token)
        check("a valid token resolves to the device", found.id == uuid.UUID(device_id))
        for label, bad in [("a wrong token is refused", "not-a-real-token"),
                           ("an empty token is refused", "")]:
            try:
                device_service.authenticate(s, bearer=bad)
                check(label, False, "no exception")
            except device_service.DeviceNotFound:
                check(label, True)

    print("\nmanaging the screen")
    r = o.patch(f"/devices/{device_id}", json={"playlist_id": str(playlist_id), "orientation": "portrait"})
    check("a playlist can be assigned", r.json()["playlist_id"] == str(playlist_id))
    check("orientation can be set", r.json()["orientation"] == "portrait")
    check("another account's playlist is refused with 404",
          o.patch(f"/devices/{device_id}", json={"playlist_id": str(foreign_playlist_id)}).status_code == 404)
    check("clear_playlist unassigns",
          o.patch(f"/devices/{device_id}", json={"clear_playlist": True}).json()["playlist_id"] is None)
    o.patch(f"/devices/{device_id}", json={"playlist_id": str(playlist_id)})

    print("\nscoping")
    check("a manager without a grant gets 404", m.get(f"/devices/{device_id}").status_code == 404)
    check("another account gets 404 by id", x.get(f"/devices/{device_id}").status_code == 404)
    with Session(engine) as s:
        s.add(DeviceAccess(user_id=mgr_id, device_id=uuid.UUID(device_id))); s.commit()
    check("a granted manager can read it", m.get(f"/devices/{device_id}").status_code == 200)
    check("a granted manager can assign a playlist",
          m.patch(f"/devices/{device_id}", json={"name": "Lobby screen"}).status_code == 200)

    print("\na manager who claims a screen keeps access to it")
    p2 = device.post("/devices/pair").json()
    m.post("/devices/claim", json={"pairing_code": p2["pairing_code"], "name": "Cafe"})
    check("the claiming manager sees their own new screen",
          any(d["name"] == "Cafe" for d in m.get("/devices").json()))

    print("\nunpair")
    r = o.post(f"/devices/{device_id}/unpair")
    check("unpair returns a fresh pairing code", r.status_code == 200 and len(r.json()["pairing_code"]) == 6)
    with Session(engine) as s:
        row = s.get(Device, uuid.UUID(device_id))
        check("the old token no longer works", row.token_hash != device_service.hash_token(token))
        check("the row and its playlist survive", row.playlist_id == playlist_id)
        check("the name survives", row.name == "Lobby screen")
    try:
        with Session(engine) as s:
            device_service.authenticate(s, bearer=token)
        check("the revoked token is rejected", False, "still authenticates")
    except device_service.DeviceNotFound:
        check("the revoked token is rejected", True)

    print("\nexpiry")
    p3 = device.post("/devices/pair").json()
    with Session(engine) as s:
        d3 = s.get(Device, uuid.UUID(p3["device_id"]))
        d3.pairing_expires_at = utcnow() - timedelta(minutes=1)
        s.add(d3); s.commit()
    check("an expired code cannot be claimed",
          o.post("/devices/claim", json={"pairing_code": p3["pairing_code"], "name": "late"}).status_code == 404)
    check("an expired pairing cannot be polled",
          device.get(f"/devices/pair/{p3['poll_token']}").status_code == 404)
    device.post("/devices/pair")   # triggers the sweep
    with Session(engine) as s:
        check("expired unclaimed rows are swept away",
              s.get(Device, uuid.UUID(p3["device_id"])) is None)

    print("\nrate limiting")
    device_service._claim_attempts.clear()
    codes = [device.post("/devices/pair").json()["pairing_code"] for _ in range(2)]
    statuses = [o.post("/devices/claim", json={"pairing_code": "AAAAAA", "name": "n"}).status_code
                for _ in range(12)]
    check("guessing is rate limited", 429 in statuses, f"{statuses.count(429)} of 12 refused")
    check(
        "the limit allows a reasonable number of typos first",
        statuses[:CLAIM_ATTEMPT_LIMIT].count(429) == 0,
        f"first {CLAIM_ATTEMPT_LIMIT} attempts all reached the lookup",
    )
    device_service._claim_attempts.clear()
    r = o.post("/devices/claim", json={"pairing_code": codes[0], "name": "After limit"})
    check("a genuine claim succeeds once the limit resets", r.status_code == 201, str(r.status_code))

    print("\ndelete")
    check("deleting a screen returns 204", o.delete(f"/devices/{device_id}").status_code == 204)
    check("...and it is gone", o.get(f"/devices/{device_id}").status_code == 404)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All device checks passed.")


if __name__ == "__main__":
    main()
