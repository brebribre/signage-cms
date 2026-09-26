"""Passwords someone else chose are temporary: the person replaces them before anything else
works, and changing a password ends every other session.

Run with:  .venv/bin/python -m scripts.check_passwords
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, AccountKind, AdminAction, User, UserRole
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkpw"
PASSWORD = "a-good-enough-password"
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
        s.exec(delete(AdminAction).where(AdminAction.account_name.startswith(PREFIX)))
        ids = [a.id for a in s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()]
        if ids:
            s.exec(delete(Account).where(Account.id.in_(ids)))
        s.commit()


def client_for(uid: uuid.UUID, version: int = 1) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(uid, version))
    return c


def login(identifier: str, password: str) -> TestClient:
    c = TestClient(app)
    r = c.post("/auth/login", json={"identifier": identifier, "password": password})
    c.status = r.status_code  # type: ignore[attr-defined]
    return c


def main() -> None:
    cleanup()
    with Session(engine) as s:
        owner_acc = s.exec(select(Account).where(Account.kind == AccountKind.OWNER)).first()
        if owner_acc is None:
            owner_acc = Account(name=f"{PREFIX} marien", kind=AccountKind.OWNER); s.add(owner_acc); s.flush()
            boss = User(account_id=owner_acc.id, username=f"{PREFIX}-boss", password_hash=hash_password(PASSWORD),
                        display_name="Boss", role=UserRole.OWNER); s.add(boss)
        else:
            boss = s.exec(select(User).where(User.account_id == owner_acc.id, User.role == UserRole.OWNER)).first()
        techs = Account(name=f"{PREFIX} techs", kind=AccountKind.ADMIN); s.add(techs); s.flush()
        tech = User(account_id=techs.id, username=f"{PREFIX}-tech", password_hash=hash_password(PASSWORD),
                    display_name="Tech", role=UserRole.OWNER); s.add(tech)
        s.commit()
        for x in (boss, tech, techs): s.refresh(x)
        boss_id, boss_version, tech_id, techs_id = boss.id, boss.session_version, tech.id, techs.id
        owner_acc_id = owner_acc.id
    b, t = client_for(boss_id, boss_version), client_for(tech_id)

    print("\nan issued account starts on a temporary password")
    r = t.post("/admin/accounts", json={"name": f"{PREFIX} shop", "username": f"{PREFIX}-shop",
                                        "password": PASSWORD, "display_name": "Shop"})
    check("issued", r.status_code == 201, r.text[:100])
    shop_id = r.json()["id"]
    check("the monitoring list says it's still temporary", r.json()["users"][0]["must_change_password"] is True)
    c = login(f"{PREFIX}-shop", PASSWORD)
    check("the customer can sign in with it", c.status == 200)
    me = c.get("/me")
    check("/me says a new password is needed", me.status_code == 200 and me.json()["user"]["must_change_password"] is True)
    r = c.get("/devices")
    check("everything else is refused until then (403)", r.status_code == 403 and "own password" in r.json()["detail"], r.text[:100])
    check("…writes too", c.patch("/account", json={"default_timezone": "UTC"}).status_code == 403)
    r = c.post("/auth/password", json={"current_password": "wrong-one-entirely", "new_password": "my-own-secret-pw"})
    check("a wrong current password is 400, not a sign-out", r.status_code == 400, r.text[:100])
    r = c.post("/auth/password", json={"current_password": PASSWORD, "new_password": PASSWORD})
    check("keeping the temporary one is refused", r.status_code == 400, r.text[:100])
    check("too short is refused", c.post("/auth/password", json={"current_password": PASSWORD, "new_password": "short"}).status_code == 422)
    stale = TestClient(app); stale.cookies.set(settings.session_cookie_name, c.cookies.get(settings.session_cookie_name))
    r = c.post("/auth/password", json={"current_password": PASSWORD, "new_password": "my-own-secret-pw"})
    check("choosing their own works", r.status_code == 200 and r.json()["user"]["must_change_password"] is False, r.text[:100])
    check("…and this session carries on with its new cookie", c.get("/devices").status_code == 200)
    check("the session from before the change is ended (401)", stale.get("/me").status_code == 401)
    check("the temporary password no longer signs in", login(f"{PREFIX}-shop", PASSWORD).status == 401)
    check("the new one does", login(f"{PREFIX}-shop", "my-own-secret-pw").status == 200)
    check("the monitoring list says it's theirs now",
          b.get(f"/admin/accounts/{shop_id}").json()["users"][0]["must_change_password"] is False)

    print("\nstaff reset a forgotten password")
    signed_in = login(f"{PREFIX}-shop", "my-own-secret-pw")
    r = t.post(f"/admin/accounts/{shop_id}/password", json={"password": "temporary-again-1"})
    check("a technician resets a client's password", r.status_code == 200, r.text[:100])
    check("the customer's open session is ended", signed_in.get("/me").status_code == 401)
    check("their own password no longer works", login(f"{PREFIX}-shop", "my-own-secret-pw").status == 401)
    c = login(f"{PREFIX}-shop", "temporary-again-1")
    check("the temporary one signs in, and must be replaced", c.status == 200 and c.get("/devices").status_code == 403)
    with Session(engine) as s:
        log = s.exec(select(AdminAction).where(AdminAction.action == "reset_password",
                                               AdminAction.account_name == f"{PREFIX} shop")).all()
        check("the reset is logged", len(log) == 1, str([x.detail for x in log]))
        check("…without the password", log and "temporary-again-1" not in log[0].detail)
    check("a technician can't reset another admin account (403)",
          t.post(f"/admin/accounts/{techs_id}/password", json={"password": "whatever-123"}).status_code == 403)
    check("nobody resets the owner account (403)",
          b.post(f"/admin/accounts/{owner_acc_id}/password", json={"password": "whatever-123"}).status_code == 403)
    check("a customer can't reset anyone",
          c.post(f"/admin/accounts/{shop_id}/password", json={"password": "whatever-123"}).status_code in (401, 403))

    print("\nsub accounts")
    c.post("/auth/password", json={"current_password": "temporary-again-1", "new_password": "my-own-secret-pw"})
    r = c.post("/users", json={"username": f"{PREFIX}-sub", "password": PASSWORD, "display_name": "Sub"})
    check("the owner makes a sub account", r.status_code == 201, r.text[:100])
    sub_id = r.json()["id"]
    sub = login(f"{PREFIX}-sub", PASSWORD)
    check("…whose first password is temporary too", sub.status == 200 and sub.get("/devices").status_code == 403)
    sub.post("/auth/password", json={"current_password": PASSWORD, "new_password": "sub-own-password"})
    check("…until they choose their own", sub.get("/devices").status_code == 200)
    check("the owner resets it", c.post(f"/users/{sub_id}/password", json={"password": "sub-temporary-9"}).status_code == 204)
    check("…which ends the sub account's session", sub.get("/me").status_code == 401)
    check("…and makes them choose again", login(f"{PREFIX}-sub", "sub-temporary-9").get("/devices").status_code == 403)

    print("\nthe monitoring app")
    r = b.post("/admin/accounts", json={"name": f"{PREFIX} newtech", "kind": "admin", "username": f"{PREFIX}-newtech",
                                        "password": PASSWORD, "display_name": "New tech"})
    r = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-newtech", "password": PASSWORD})
    check("a technician on a temporary password is sent to the CMS first (403)",
          r.status_code == 403 and "CMS" in r.json()["detail"], r.text[:120])
    fresh = login(f"{PREFIX}-newtech", PASSWORD)
    fresh.post("/auth/password", json={"current_password": PASSWORD, "new_password": "tech-own-password"})
    r = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-newtech", "password": "tech-own-password"})
    check("…and gets in once they have their own", r.status_code == 200, r.text[:80])
    check("a cookie from before versions existed still works for someone who never changed",
          client_for(boss_id, 1).get("/me").status_code == (200 if boss_version == 1 else 401))

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All password checks passed.")


if __name__ == "__main__":
    main()
