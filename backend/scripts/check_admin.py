"""Platform admin checkpoint: /admin/* is reachable by admins only, issues accounts, sets
limits, and logs what it did — and nothing a customer can call ever grants the flag.

Run with:  .venv/bin/python -m scripts.check_admin
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, AdminAction, Device, User, UserRole
from app.models.base import utcnow
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkadmin"
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
        accounts = s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()
        ids = [a.id for a in accounts]
        if ids:
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
        s.commit()


def client_for(uid: uuid.UUID) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(uid))
    return c


def main() -> None:
    cleanup()
    with Session(engine) as s:
        staff = Account(name=f"{PREFIX} fortu"); s.add(staff); s.flush()
        admin = User(account_id=staff.id, username=f"{PREFIX}-admin", password_hash=hash_password(PASSWORD),
                     display_name="Admin", role=UserRole.OWNER, is_platform_admin=True)
        s.add(admin)

        cust = Account(name=f"{PREFIX} customer", max_screens=3); s.add(cust); s.flush()
        owner = User(account_id=cust.id, username=f"{PREFIX}-owner", password_hash=hash_password(PASSWORD),
                     display_name="Owner", role=UserRole.OWNER)
        manager = User(account_id=cust.id, username=f"{PREFIX}-mgr", password_hash=hash_password(PASSWORD),
                       display_name="Manager", role=UserRole.MANAGER)
        s.add(owner); s.add(manager)
        s.add(Device(account_id=cust.id, name="Lobby"))
        s.add(Device(account_id=cust.id, name="Cafe"))
        # Told to disconnect but not yet gone — must not take up a seat.
        s.add(Device(account_id=cust.id, name="Dead", disconnect_requested_at=utcnow()))
        s.commit()
        for x in (admin, owner, manager, cust):
            s.refresh(x)
        admin_id, owner_id, manager_id, cust_id = admin.id, owner.id, manager.id, cust.id

    a, o, m = client_for(admin_id), client_for(owner_id), client_for(manager_id)

    print("\nonly a platform admin gets in")
    check("no cookie is 401", TestClient(app).get("/admin/accounts").status_code == 401)
    check("an ordinary owner is 403", o.get("/admin/accounts").status_code == 403)
    check("a manager is 403", m.get("/admin/accounts").status_code == 403)
    check("an owner cannot create accounts", o.post("/admin/accounts", json={
        "name": "x", "username": f"{PREFIX}-x", "password": PASSWORD, "display_name": "X"}).status_code == 403)
    check("an owner cannot set limits", o.patch(f"/admin/accounts/{cust_id}", json={"max_screens": 99}).status_code == 403)
    r = a.get("/admin/accounts")
    check("the admin lists accounts", r.status_code == 200, str(r.status_code))

    print("\n/me says who is an admin")
    check("admin's /me has the flag", a.get("/me").json()["user"]["is_platform_admin"] is True)
    check("owner's /me does not", o.get("/me").json()["user"]["is_platform_admin"] is False)

    print("\nthe list shows usage against limits")
    row = next(x for x in r.json() if x["id"] == str(cust_id))
    check("owner_username is the first owner", row["owner_username"] == f"{PREFIX}-owner", str(row["owner_username"]))
    check("max_screens comes through", row["max_screens"] == 3, str(row["max_screens"]))
    check("a disconnecting screen does not take a seat", row["screens_used"] == 2, str(row["screens_used"]))
    check("storage quota is unlimited (null)", row["storage_quota_bytes"] is None)
    check("storage used is a number", isinstance(row["storage_used_bytes"], int))

    print("\nissuing an account")
    r = a.post("/admin/accounts", json={
        "name": f"{PREFIX} issued", "username": f"{PREFIX}-NEW", "password": PASSWORD,
        "display_name": "New Owner", "max_screens": 5, "storage_quota_bytes": 1_073_741_824,
    })
    check("create returns 201", r.status_code == 201, str(r.status_code) + " " + r.text[:120])
    issued = r.json()
    issued_id = uuid.UUID(issued["id"])
    check("username is lowercased", issued["owner_username"] == f"{PREFIX}-new", str(issued["owner_username"]))
    check("limits were set", issued["max_screens"] == 5 and issued["storage_quota_bytes"] == 1_073_741_824)
    check("starts with no screens", issued["screens_used"] == 0)
    check("the new owner can log in", TestClient(app).post("/auth/login", json={
        "identifier": f"{PREFIX}-new", "password": PASSWORD}).status_code == 200)
    with Session(engine) as s:
        new_owner = s.exec(select(User).where(User.username == f"{PREFIX}-new")).first()
        check("the new owner is an owner", new_owner is not None and new_owner.role == UserRole.OWNER)
        check("...and not a platform admin", new_owner is not None and new_owner.is_platform_admin is False)
        log = s.exec(select(AdminAction).where(AdminAction.account_id == issued_id)).all()
        check("creation was logged once", len(log) == 1 and log[0].action == "create_account", str([x.action for x in log]))
        check("the log names the admin", log and log[0].admin_user_id == admin_id)
    check("duplicate username is 409", a.post("/admin/accounts", json={
        "name": f"{PREFIX} dupe", "username": f"{PREFIX}-new", "password": PASSWORD, "display_name": "D"}).status_code == 409)
    check("a bad username is 422", a.post("/admin/accounts", json={
        "name": f"{PREFIX} bad", "username": "x", "password": PASSWORD, "display_name": "B"}).status_code == 422)
    check("a negative limit is 422", a.post("/admin/accounts", json={
        "name": f"{PREFIX} neg", "username": f"{PREFIX}-neg", "password": PASSWORD, "display_name": "N",
        "max_screens": -1}).status_code == 422)

    print("\nchanging limits")
    body = a.patch(f"/admin/accounts/{issued_id}", json={"max_screens": 10}).json()
    check("max_screens changes", body["max_screens"] == 10, str(body["max_screens"]))
    check("storage is left alone when not sent", body["storage_quota_bytes"] == 1_073_741_824)
    body = a.patch(f"/admin/accounts/{issued_id}", json={"storage_quota_bytes": None}).json()
    check("sending null makes storage unlimited", body["storage_quota_bytes"] is None)
    check("...and max_screens is still 10", body["max_screens"] == 10)
    body = a.patch(f"/admin/accounts/{issued_id}", json={"max_screens": 10}).json()
    with Session(engine) as s:
        log = s.exec(select(AdminAction).where(AdminAction.account_id == issued_id,
                                               AdminAction.action == "set_limits")).all()
        check("each real change was logged, a no-op was not", len(log) == 2, str(len(log)))
        check("the log says what changed in plain words",
              any("max_screens 5 → 10" in x.detail for x in log), str([x.detail for x in log]))
    check("zero screens is legal", a.patch(f"/admin/accounts/{issued_id}", json={"max_screens": 0}).json()["max_screens"] == 0)
    check("an unknown account is 404", a.patch(f"/admin/accounts/{uuid.uuid4()}", json={"max_screens": 1}).status_code == 404)
    check("GET one account works", a.get(f"/admin/accounts/{issued_id}").json()["name"] == f"{PREFIX} issued")

    print("\nthe flag cannot be granted through a customer route")
    r = o.post("/users", json={
        "username": f"{PREFIX}-sneak", "password": PASSWORD, "display_name": "Sneak",
        "is_platform_admin": True,
    })
    check("owner still creates a manager", r.status_code == 201, str(r.status_code))
    with Session(engine) as s:
        sneak = s.exec(select(User).where(User.username == f"{PREFIX}-sneak")).first()
        check("...but is_platform_admin was ignored", sneak is not None and sneak.is_platform_admin is False)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All admin checks passed.")


if __name__ == "__main__":
    main()
