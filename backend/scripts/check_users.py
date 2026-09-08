"""Phase 9b checkpoint: subusers, device grants, and the guardrails that prevent lockout.

The scoping checks call the endpoints directly with a manager's cookie — hiding a nav entry
in the UI is a courtesy, the server is the control, and only this proves it.

Run with:  .venv/bin/python -m scripts.check_users
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

PREFIX = "chkusers"
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
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner", password_hash=hash_password(PASSWORD),
                     display_name="Owner", role=UserRole.OWNER)
        owner2 = User(account_id=acct.id, username=f"{PREFIX}-owner2", password_hash=hash_password(PASSWORD),
                      display_name="Owner Two", role=UserRole.OWNER)
        s.add(owner); s.add(owner2)
        lobby = Device(account_id=acct.id, name="Lobby", paired_at=None)
        cafe = Device(account_id=acct.id, name="Cafe", paired_at=None)
        roof = Device(account_id=acct.id, name="Roof", paired_at=None)
        s.add(lobby); s.add(cafe); s.add(roof)

        other = Account(name=f"{PREFIX} other"); s.add(other); s.flush()
        outsider = User(account_id=other.id, username=f"{PREFIX}-out", password_hash=hash_password(PASSWORD),
                        display_name="Out", role=UserRole.OWNER)
        foreign = Device(account_id=other.id, name="Theirs")
        s.add(outsider); s.add(foreign)
        s.commit()
        for x in (owner, owner2, lobby, cafe, roof, outsider, foreign):
            s.refresh(x)
        owner_id, owner2_id, out_id = owner.id, owner2.id, outsider.id
        lobby_id, cafe_id, roof_id, foreign_id = lobby.id, cafe.id, roof.id, foreign.id

    o, o2, x = client_for(owner_id), client_for(owner2_id), client_for(out_id)

    print("\ncreate a subuser with grants")
    r = o.post("/users", json={
        "username": f"{PREFIX}-MGR", "password": PASSWORD, "display_name": "Manager",
        "device_ids": [str(lobby_id), str(cafe_id)],
    })
    check("create returns 201", r.status_code == 201, str(r.status_code))
    mgr = r.json()
    mgr_id = uuid.UUID(mgr["id"])
    check("username is lowercased", mgr["username"] == f"{PREFIX}-mgr", mgr["username"])
    check("the new user is a manager", mgr["role"] == "manager")
    check("no email is required", mgr["email"] is None)
    check("grants were applied", mgr["device_count"] == 2, str(mgr["device_count"]))
    check("duplicate username is 409", o.post("/users", json={
        "username": f"{PREFIX}-mgr", "password": PASSWORD, "display_name": "Dupe"}).status_code == 409)
    check("granting another account's device is 404", o.post("/users", json={
        "username": f"{PREFIX}-x", "password": PASSWORD, "display_name": "X",
        "device_ids": [str(foreign_id)]}).status_code == 404)

    m = client_for(mgr_id)

    print("\nowner-only routes")
    check("a manager cannot list users", m.get("/users").status_code == 403)
    check("a manager cannot create users", m.post("/users", json={
        "username": f"{PREFIX}-nope", "password": PASSWORD, "display_name": "N"}).status_code == 403)
    check("a manager cannot set grants", m.put(f"/users/{mgr_id}/devices",
        json={"device_ids": []}).status_code == 403)
    check("a manager cannot delete users", m.delete(f"/users/{mgr_id}").status_code == 403)
    outsider_users = [u["username"] for u in x.get("/users").json()]
    check("another account's owner sees only their own users",
          outsider_users == [f"{PREFIX}-out"], str(outsider_users))
    check("...and cannot touch them", x.delete(f"/users/{mgr_id}").status_code == 404)

    print("\ndevice scoping is enforced by the server")
    listed = [d["name"] for d in m.get("/devices").json()]
    check("a manager sees only granted devices", sorted(listed) == ["Cafe", "Lobby"], str(listed))
    check("an owner sees every device in the account",
          sorted(d["name"] for d in o.get("/devices").json()) == ["Cafe", "Lobby", "Roof"])
    check("another account sees none of them",
          [d["name"] for d in x.get("/devices").json()] == ["Theirs"])

    print("\n/me reports the manager's reach")
    me = m.get("/me").json()
    check("manager device_ids matches the grants",
          sorted(me["device_ids"]) == sorted([str(lobby_id), str(cafe_id)]), str(me["device_ids"]))
    check("owner device_ids is null (unrestricted)", o.get("/me").json()["device_ids"] is None)

    print("\ngrants are replaced, not appended")
    body = o.put(f"/users/{mgr_id}/devices", json={"device_ids": [str(roof_id)]}).json()
    check("replacing leaves exactly one grant", body["device_count"] == 1, str(body["device_count"]))
    check("the new device is reachable", [d["name"] for d in m.get("/devices").json()] == ["Roof"])
    check("the old ones are not", "Lobby" not in [d["name"] for d in m.get("/devices").json()])
    body = o.put(f"/users/{mgr_id}/devices", json={"device_ids": [str(roof_id), str(roof_id)]}).json()
    check("duplicate ids collapse to one", body["device_count"] == 1, str(body["device_count"]))
    check("granting an unknown device is 404", o.put(f"/users/{mgr_id}/devices",
        json={"device_ids": [str(uuid.uuid4())]}).status_code == 404)
    check("clearing grants is legal", o.put(f"/users/{mgr_id}/devices",
        json={"device_ids": []}).json()["device_count"] == 0)
    check("a manager with no grants sees no devices", m.get("/devices").json() == [])

    print("\npassword reset by the owner")
    check("owner sets a new password", o.post(f"/users/{mgr_id}/password",
        json={"password": "brand-new-password"}).status_code == 204)
    fresh = TestClient(app)
    check("the new password works", fresh.post("/auth/login", json={
        "identifier": f"{PREFIX}-mgr", "password": "brand-new-password"}).status_code == 200)
    check("the old one does not", TestClient(app).post("/auth/login", json={
        "identifier": f"{PREFIX}-mgr", "password": PASSWORD}).status_code == 401)
    check("a short password is refused", o.post(f"/users/{mgr_id}/password",
        json={"password": "short"}).status_code == 422)

    print("\ndeactivation")
    check("owner deactivates the manager",
          o.patch(f"/users/{mgr_id}", json={"is_active": False}).json()["is_active"] is False)
    check("their existing cookie stops working immediately", m.get("/devices").status_code == 401)
    check("and they cannot log in", TestClient(app).post("/auth/login", json={
        "identifier": f"{PREFIX}-mgr", "password": "brand-new-password"}).status_code == 401)
    check("reactivating restores access",
          o.patch(f"/users/{mgr_id}", json={"is_active": True}).json()["is_active"] is True)
    check("...and the cookie works again", client_for(mgr_id).get("/devices").status_code == 200)

    print("\nlockout guardrails")
    check("an owner cannot deactivate themselves",
          o.patch(f"/users/{owner_id}", json={"is_active": False}).status_code == 409)
    check("an owner cannot delete themselves", o.delete(f"/users/{owner_id}").status_code == 409)
    check("one owner may deactivate another while a second remains",
          o.patch(f"/users/{owner2_id}", json={"is_active": False}).status_code == 200)
    check("a deactivated owner's cookie stops working", o2.get("/users").status_code == 401)
    o.patch(f"/users/{owner2_id}", json={"is_active": True})

    # The LastOwner guard is defence-in-depth and is currently UNREACHABLE over HTTP: to act
    # you must be an active owner, and the self-guard blocks acting on yourself, so at least
    # one active owner always remains besides the target. Asserted at the service layer
    # instead of pretending an HTTP check exercises it.
    from app.infra.db import engine as _engine
    from app.services import users as _users
    with Session(_engine) as s:
        actor = s.get(User, owner_id)
        target = s.get(User, owner2_id)
        other_owner = s.get(User, owner_id)
        other_owner.is_active = False   # fabricate the state HTTP cannot reach
        s.add(other_owner); s.commit()
        try:
            _users.update_user(s, owner=actor, user_id=target.id, is_active=False)
            check("LastOwner guard refuses removing the final active owner", False, "no exception")
        except _users.LastOwner:
            check("LastOwner guard refuses removing the final active owner", True)
        finally:
            restored = s.get(User, owner_id)
            restored.is_active = True
            s.add(restored); s.commit()

    print("\ndeleting a subuser keeps their work")
    with Session(engine) as s:
        acct_id = s.get(User, mgr_id).account_id
        s.add(Device(account_id=acct_id, name="Made by manager", created_by=mgr_id))
        s.commit()
    check("delete returns 204", o.delete(f"/users/{mgr_id}").status_code == 204)
    with Session(engine) as s:
        survivor = s.exec(select(Device).where(Device.name == "Made by manager")).first()
        check("the device they created survives", survivor is not None)
        check("...with created_by nulled", survivor is not None and survivor.created_by is None)
        check("their grants are gone",
              s.exec(select(DeviceAccess).where(DeviceAccess.user_id == mgr_id)).all() == [])
    check("they are gone from the user list",
          all(u["id"] != str(mgr_id) for u in o.get("/users").json()))

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All user checks passed.")


if __name__ == "__main__":
    main()
