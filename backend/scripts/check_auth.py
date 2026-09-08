"""Phase 3 checkpoint: accounts, users, sessions and the authorization dependencies.

Run with:  .venv/bin/python -m scripts.check_auth
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, Device, DeviceAccess, User, UserRole
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkauth"
OWNER = f"{PREFIX}-owner"
MANAGER = f"{PREFIX}-manager"
PASSWORD = "correct-horse-battery"

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
        s.exec(delete(Device).where(Device.name.startswith(PREFIX)))
        s.commit()
        accounts = s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()
        if accounts:
            s.exec(delete(Account).where(Account.id.in_([a.id for a in accounts])))
            s.commit()


def client_for(user_id: uuid.UUID) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(user_id))
    return c


def main() -> None:
    cleanup()
    anon = TestClient(app)

    print("\nsignup")
    r = anon.post("/auth/signup", json={
        "username": OWNER.upper(),          # deliberately mixed case
        "password": PASSWORD,
        "display_name": "Owner",
        "email": f"{PREFIX}-Owner@Example.COM",
        "account_name": f"{PREFIX} account",
    })
    check("signup returns 201", r.status_code == 201, str(r.status_code))
    body = r.json()
    check("username is lowercased", body["user"]["username"] == OWNER, body["user"]["username"])
    check("email is lowercased", body["user"]["email"] == f"{PREFIX}-owner@example.com")
    check("first user is the owner", body["user"]["role"] == "owner")
    check("an account was created with them", body["account"]["name"] == f"{PREFIX} account")
    check("owner device_ids is null (means: all)", body["device_ids"] is None)
    check("signup sets a session cookie", settings.session_cookie_name in r.cookies)
    # TestClient keeps a cookie jar across requests, so the client that just signed up is
    # authenticated from here on. Anything asserting anonymous behaviour must clear it, or
    # it silently tests the logged-in path instead.
    anon.cookies.clear()
    owner_id = uuid.UUID(body["user"]["id"])
    account_id = uuid.UUID(body["account"]["id"])

    r = anon.post("/auth/signup", json={
        "username": OWNER, "password": PASSWORD, "display_name": "Dupe",
    })
    check("duplicate username is 409", r.status_code == 409, str(r.status_code))
    r = anon.post("/auth/signup", json={
        "username": f"{PREFIX}-other", "password": PASSWORD, "display_name": "Dupe",
        "email": f"{PREFIX}-owner@example.com",
    })
    check("duplicate email is 409", r.status_code == 409, str(r.status_code))
    r = anon.post("/auth/signup", json={
        "username": "ab", "password": PASSWORD, "display_name": "Short",
    })
    check("too-short username is 422", r.status_code == 422, str(r.status_code))
    r = anon.post("/auth/signup", json={
        "username": f"{PREFIX}-weak", "password": "short", "display_name": "Weak",
    })
    check("password under 8 chars is 422", r.status_code == 422, str(r.status_code))

    print("\npassword storage")
    with Session(engine) as s:
        stored = s.get(User, owner_id).password_hash
    check("hash is argon2id", stored.startswith("$argon2id$"), stored[:12])
    check("the password itself is nowhere in the hash", PASSWORD not in stored)

    print("\nlogin — one field, resolved two ways")
    c = TestClient(app)
    r = c.post("/auth/login", json={"identifier": OWNER, "password": PASSWORD})
    check("login by username", r.status_code == 200, str(r.status_code))
    r = c.post("/auth/login", json={
        "identifier": f"{PREFIX}-OWNER@example.com", "password": PASSWORD
    })
    check("login by email, case-insensitively", r.status_code == 200, str(r.status_code))

    print("\nlogin failures are indistinguishable")
    bad_pw = anon.post("/auth/login", json={"identifier": OWNER, "password": "wrong-password"})
    unknown = anon.post("/auth/login", json={"identifier": f"{PREFIX}-nobody", "password": PASSWORD})
    check("wrong password is 401", bad_pw.status_code == 401)
    check("unknown identifier is 401", unknown.status_code == 401)
    check(
        "both return a byte-identical body",
        bad_pw.content == unknown.content,
        bad_pw.text,
    )

    print("\n/me and the session cookie")
    r = anon.get("/me")
    check("anonymous /me is 401", r.status_code == 401, str(r.status_code))
    owner_client = client_for(owner_id)
    r = owner_client.get("/me")
    check("signed-in /me is 200", r.status_code == 200)
    tampered = TestClient(app)
    tampered.cookies.set(settings.session_cookie_name, create_session_token(owner_id)[:-4] + "AAAA")
    check("a tampered cookie is 401", tampered.get("/me").status_code == 401)
    ghost = client_for(uuid.uuid4())
    check("a valid cookie for a deleted user is 401", ghost.get("/me").status_code == 401)

    logged_in = TestClient(app)
    logged_in.post("/auth/login", json={"identifier": OWNER, "password": PASSWORD})
    check("logout returns 204", logged_in.post("/auth/logout").status_code == 204)
    check("after logout /me is 401", logged_in.get("/me").status_code == 401)

    print("\nmanager scoping")
    with Session(engine) as s:
        manager = User(
            account_id=account_id, username=MANAGER, password_hash=hash_password(PASSWORD),
            display_name="Manager", role=UserRole.MANAGER, created_by=owner_id,
        )
        s.add(manager)
        granted = Device(account_id=account_id, name=f"{PREFIX} lobby")
        ungranted = Device(account_id=account_id, name=f"{PREFIX} cafe")
        s.add(granted)
        s.add(ungranted)
        s.commit()
        s.refresh(manager); s.refresh(granted); s.refresh(ungranted)
        manager_id, granted_id, ungranted_id = manager.id, granted.id, ungranted.id
        s.add(DeviceAccess(user_id=manager_id, device_id=granted_id))
        s.commit()

        other_account = Account(name=f"{PREFIX} other account")
        s.add(other_account)
        s.flush()
        foreign = Device(account_id=other_account.id, name=f"{PREFIX} foreign")
        s.add(foreign)
        s.commit()
        s.refresh(foreign)
        foreign_id = foreign.id

    manager_client = client_for(manager_id)
    r = manager_client.get("/me")
    check("manager /me is 200", r.status_code == 200)
    check(
        "manager device_ids lists only the grant",
        r.json()["device_ids"] == [str(granted_id)],
        str(r.json()["device_ids"]),
    )

    print("\nthe three dependencies, called directly")
    from fastapi import HTTPException

    from app.api.deps import device_for_user, require_owner

    with Session(engine) as s:
        owner_obj = s.get(User, owner_id)
        manager_obj = s.get(User, manager_id)

        check("require_owner admits an owner", require_owner(owner_obj) is owner_obj)
        try:
            require_owner(manager_obj)
            check("require_owner rejects a manager with 403", False, "no exception")
        except HTTPException as e:
            check("require_owner rejects a manager with 403", e.status_code == 403, str(e.status_code))

        check(
            "owner reaches a device with no grant row",
            device_for_user(ungranted_id, owner_obj, s).id == ungranted_id,
        )
        check(
            "manager reaches a granted device",
            device_for_user(granted_id, manager_obj, s).id == granted_id,
        )
        for label, did, who in [
            ("manager gets 404 for an ungranted device in their own account", ungranted_id, manager_obj),
            ("manager gets 404 for another account's device", foreign_id, manager_obj),
            ("owner gets 404 for another account's device", foreign_id, owner_obj),
            ("404 for a device id that does not exist", uuid.uuid4(), owner_obj),
        ]:
            try:
                device_for_user(did, who, s)
                check(label, False, "no exception")
            except HTTPException as e:
                check(label, e.status_code == 404, f"got {e.status_code}")

    print("\ndeactivation takes effect immediately")
    with Session(engine) as s:
        m = s.get(User, manager_id)
        m.is_active = False
        s.add(m)
        s.commit()
    check("a deactivated user's existing cookie stops working", manager_client.get("/me").status_code == 401)
    r = anon.post("/auth/login", json={"identifier": MANAGER, "password": PASSWORD})
    check("a deactivated user cannot log in", r.status_code == 401)
    check(
        "and cannot tell they were deactivated (same body as a wrong password)",
        r.content == bad_pw.content,
    )

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All auth checks passed.")


if __name__ == "__main__":
    main()
