"""Monitoring-app checkpoint: /admin/* is reachable by staff only — the main user of an owner
or admin account — and each kind of staff can issue and limit exactly the kinds of account the
rules allow; nothing a customer can call changes an account's kind; and an account past its end
date is read-only, while its screens carry on.

Run with:  .venv/bin/python -m scripts.check_admin
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Account, AccountKind, AdminAction, Device, User, UserRole
from app.models.base import utcnow
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkadmin"
PASSWORD = "a-good-enough-password"
GB = 1024**3
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


def user(account: Account, name: str, role: UserRole) -> User:
    return User(account_id=account.id, username=f"{PREFIX}-{name}", password_hash=hash_password(PASSWORD),
                display_name=name.title(), role=role)


def issue(client: TestClient, name: str, **extra):
    body = {"name": f"{PREFIX} {name}", "username": f"{PREFIX}-{name}", "password": PASSWORD, "display_name": name}
    return client.post("/admin/accounts", json={**body, **extra})


def main() -> None:
    cleanup()
    # There may already be a real owner account in this database; the checks below never make
    # one through the API (that is refused by design), so a seeded owner is only used when the
    # database has none. Otherwise its main user stands in — same kind, same rights.
    with Session(engine) as s:
        existing_owner = s.exec(select(Account).where(Account.kind == AccountKind.OWNER)).first()
        if existing_owner is None:
            paskall = Account(name=f"{PREFIX} paskall", kind=AccountKind.OWNER); s.add(paskall); s.flush()
            boss = user(paskall, "boss", UserRole.OWNER); s.add(boss)
        else:
            paskall = existing_owner
            boss = s.exec(select(User).where(User.account_id == paskall.id, User.role == UserRole.OWNER)).first()

        techs = Account(name=f"{PREFIX} techs", kind=AccountKind.ADMIN, max_screens=15); s.add(techs); s.flush()
        tech = user(techs, "tech", UserRole.OWNER); s.add(tech)
        tech_sub = user(techs, "techsub", UserRole.MANAGER); s.add(tech_sub)

        cust = Account(name=f"{PREFIX} customer", max_screens=3); s.add(cust); s.flush()
        owner = user(cust, "owner", UserRole.OWNER); s.add(owner)
        manager = user(cust, "mgr", UserRole.MANAGER); s.add(manager)
        s.add(Device(account_id=cust.id, name="Lobby"))
        s.add(Device(account_id=cust.id, name="Cafe"))
        # Told to disconnect but not yet gone — must not take up a seat.
        s.add(Device(account_id=cust.id, name="Dead", disconnect_requested_at=utcnow()))
        s.commit()
        for x in (boss, tech, tech_sub, owner, manager, paskall, techs, cust):
            s.refresh(x)
        boss_id, tech_id, tech_sub_id, owner_id, manager_id = boss.id, tech.id, tech_sub.id, owner.id, manager.id
        paskall_id, techs_id, cust_id = paskall.id, techs.id, cust.id

    b, t, ts, o, m = client_for(boss_id), client_for(tech_id), client_for(tech_sub_id), client_for(owner_id), client_for(manager_id)

    print("\nonly staff get in: the main user of an owner or admin account")
    check("no cookie is 401", TestClient(app).get("/admin/accounts").status_code == 401)
    check("a client's owner is 403", o.get("/admin/accounts").status_code == 403)
    check("a client's sub account is 403", m.get("/admin/accounts").status_code == 403)
    check("a sub account inside an admin account is 403 too", ts.get("/admin/accounts").status_code == 403)
    check("the owner account's main user is in", b.get("/admin/accounts").status_code == 200)
    r = t.get("/admin/accounts")
    check("an admin account's main user is in", r.status_code == 200, str(r.status_code))
    check("a client cannot issue accounts", issue(o, "x").status_code == 403)
    check("a client cannot set limits", o.patch(f"/admin/accounts/{cust_id}", json={"max_screens": 99}).status_code == 403)

    print("\nwho you are, and your kind")
    check("/admin/me says owner for the owner account", b.get("/admin/me").json().get("kind") == "owner")
    check("/admin/me says admin for an admin account", t.get("/admin/me").json().get("kind") == "admin")
    check("the CMS's /me carries the account kind", o.get("/me").json()["account"]["kind"] == "client")
    check("...and no per-user admin flag any more", "is_platform_admin" not in o.get("/me").json()["user"])

    print("\nthe list shows every account, its kind, and usage against limits")
    rows = {x["id"]: x for x in r.json()}
    check("an admin sees the owner account too", str(paskall_id) in rows)
    check("kinds come through", rows[str(paskall_id)]["kind"] == "owner" and rows[str(techs_id)]["kind"] == "admin"
          and rows[str(cust_id)]["kind"] == "client")
    row = rows[str(cust_id)]
    check("owner_username is the first owner", row["owner_username"] == f"{PREFIX}-owner", str(row["owner_username"]))
    listed = [(u["username"], u["role"]) for u in row["users"]]
    check("everyone in the account is listed, owner first, sub account under them",
          listed == [(f"{PREFIX}-owner", "owner"), (f"{PREFIX}-mgr", "manager")], str(listed))
    check("max_screens comes through", row["max_screens"] == 3, str(row["max_screens"]))
    check("a disconnecting screen does not take a seat", row["screens_used"] == 2, str(row["screens_used"]))
    check("storage quota is unlimited (null)", row["storage_quota_bytes"] is None)

    print("\nthe owner issues client accounts")
    r = issue(b, "shop", max_screens=5, storage_quota_bytes=GB)
    check("create returns 201", r.status_code == 201, str(r.status_code) + " " + r.text[:120])
    shop = r.json()
    shop_id = uuid.UUID(shop["id"])
    check("kind defaults to client", shop["kind"] == "client", shop["kind"])
    check("limits were set as sent", shop["max_screens"] == 5 and shop["storage_quota_bytes"] == GB)
    check("a client with no limits sent is unlimited, as before",
          issue(b, "shop2").json()["max_screens"] is None)
    check("the new owner can log in to the CMS", TestClient(app).post("/auth/login", json={
        "identifier": f"{PREFIX}-shop", "password": PASSWORD}).status_code == 200)
    with Session(engine) as s:
        log = s.exec(select(AdminAction).where(AdminAction.account_id == shop_id)).all()
        check("creation was logged once, naming the kind", len(log) == 1 and log[0].action == "create_account"
              and log[0].detail.startswith("client account"), str([x.detail for x in log]))
        check("the log names who did it", log and log[0].admin_user_id == boss_id)

    print("\nthe owner issues admin accounts")
    r = issue(b, "newtech", kind="admin")
    check("create returns 201", r.status_code == 201, str(r.status_code) + " " + r.text[:120])
    newtech = r.json()
    check("kind is admin", newtech["kind"] == "admin")
    check("limits left out → 15 screens and 5 GB", newtech["max_screens"] == 15 and newtech["storage_quota_bytes"] == 5 * GB,
          f'{newtech["max_screens"]} / {newtech["storage_quota_bytes"]}')
    r = issue(b, "newtech2", kind="admin", max_screens=None, storage_quota_bytes=None)
    check("limits sent as null → unlimited", r.json()["max_screens"] is None and r.json()["storage_quota_bytes"] is None)
    r = issue(b, "newtech3", kind="admin", max_screens=2)
    check("one limit sent, the other defaulted", r.json()["max_screens"] == 2 and r.json()["storage_quota_bytes"] == 5 * GB)
    nt = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-newtech", "password": PASSWORD})
    check("the new technician's issued password is temporary: the CMS first (403)",
          nt.status_code == 403 and "CMS" in nt.json().get("detail", ""), f"{nt.status_code} {nt.text[:80]}")
    cms = TestClient(app)
    cms.post("/auth/login", json={"identifier": f"{PREFIX}-newtech", "password": PASSWORD})
    cms.post("/auth/password", json={"current_password": PASSWORD, "new_password": PASSWORD + "-own"})
    nt = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-newtech", "password": PASSWORD + "-own"})
    check("the new technician can sign in to the monitoring app as admin",
          nt.status_code == 200 and nt.json().get("kind") == "admin", f"{nt.status_code} {nt.text[:80]}")
    r = issue(b, "second-owner", kind="owner")
    check("nobody issues a second owner account (403)", r.status_code == 403, str(r.status_code))
    check("...and it says so", "only one owner" in r.json().get("detail", ""), r.json().get("detail"))

    print("\nan admin issues client accounts only")
    r = issue(t, "shop3")
    check("an admin creates a client", r.status_code == 201 and r.json()["kind"] == "client", str(r.status_code))
    r = issue(t, "sneaky-admin", kind="admin")
    check("an admin cannot create an admin (403)", r.status_code == 403, str(r.status_code))
    check("...in plain words", "only issue client accounts" in r.json().get("detail", ""), r.json().get("detail"))
    check("an admin cannot create an owner (403)", issue(t, "sneaky-owner", kind="owner").status_code == 403)

    print("\nchanging limits: whose you may change")
    body = b.patch(f"/admin/accounts/{shop_id}", json={"max_screens": 10}).json()
    check("the owner changes a client's limits", body["max_screens"] == 10, str(body.get("max_screens")))
    check("storage is left alone when not sent", body["storage_quota_bytes"] == GB)
    body = b.patch(f"/admin/accounts/{shop_id}", json={"storage_quota_bytes": None}).json()
    check("sending null makes storage unlimited", body["storage_quota_bytes"] is None)
    body = b.patch(f"/admin/accounts/{techs_id}", json={"max_screens": 20}).json()
    check("the owner changes an admin account's limits", body.get("max_screens") == 20, str(body))
    r = b.patch(f"/admin/accounts/{paskall_id}", json={"max_screens": 1})
    check("nobody puts limits on the owner account (403)", r.status_code == 403, str(r.status_code))
    check("...and it says why", "owner account has no limits" in r.json().get("detail", ""), r.json().get("detail"))
    r = t.patch(f"/admin/accounts/{shop_id}", json={"max_screens": 12})
    check("an admin changes a client's limits", r.status_code == 200 and r.json()["max_screens"] == 12, str(r.status_code))
    r = t.patch(f"/admin/accounts/{techs_id}", json={"max_screens": 99})
    check("an admin cannot change an admin account's limits, even their own (403)", r.status_code == 403, str(r.status_code))
    check("an admin cannot change the owner account's limits (403)",
          t.patch(f"/admin/accounts/{paskall_id}", json={"max_screens": 99}).status_code == 403)
    b.patch(f"/admin/accounts/{shop_id}", json={"max_screens": 12})  # a no-op: must not be logged
    with Session(engine) as s:
        log = s.exec(select(AdminAction).where(AdminAction.account_id == shop_id,
                                               AdminAction.action == "set_limits")).all()
        check("each real change was logged, a no-op and a refusal were not", len(log) == 3, str(len(log)))
        check("the log says what changed in plain words",
              any("max_screens 5 → 10" in x.detail for x in log), str([x.detail for x in log]))
    check("zero screens is legal", b.patch(f"/admin/accounts/{shop_id}", json={"max_screens": 0}).json()["max_screens"] == 0)
    check("an unknown account is 404", b.patch(f"/admin/accounts/{uuid.uuid4()}", json={"max_screens": 1}).status_code == 404)
    check("GET one account works", b.get(f"/admin/accounts/{shop_id}").json()["name"] == f"{PREFIX} shop")
    check("a bad username is 422", issue(b, "bad", username="x").status_code == 422)
    check("a negative limit is 422", issue(b, "neg", max_screens=-1).status_code == 422)
    check("duplicate username is 409", issue(b, "shop").status_code == 409)

    print("\nno customer route changes an account's kind")
    r = o.patch("/account", json={"kind": "owner", "default_timezone": "Asia/Jakarta"})
    check("the owner's settings save still works", r.status_code == 200, str(r.status_code))
    with Session(engine) as s:
        check("...but kind was ignored", s.get(Account, cust_id).kind == AccountKind.CLIENT)
    r = o.post("/users", json={"username": f"{PREFIX}-sneak", "password": PASSWORD, "display_name": "Sneak", "kind": "admin"})
    check("a sub account is still created", r.status_code == 201, str(r.status_code))
    check("...as a manager, who cannot get in", client_for(uuid.UUID(r.json()["id"])).get("/admin/me").status_code == 403)

    print("\nthe screen limit is enforced when pairing")
    from app.services import devices as device_service

    screen = TestClient(app)  # no cookie: stands in for a screen asking for a code

    def claim(client: TestClient, label: str):
        # A fresh code each time, and the rate limit cleared so it can't be what refuses us.
        device_service._claim_attempts.clear()
        code = screen.post("/devices/pair").json()["pairing_code"]
        return client.post("/devices/claim", json={"pairing_code": code, "name": label})

    # The customer account counts 2 screens (Dead is disconnecting) against a limit of 3.
    r = claim(o, "Third")
    check("one under the limit still pairs", r.status_code == 201, f"{r.status_code} {r.text[:100]}")
    third_id = r.json()["id"]
    with Session(engine) as s:
        row = s.get(Device, uuid.UUID(third_id))
        row.disconnect_requested_at = utcnow()
        s.add(row)
        s.commit()
    check("a disconnecting screen frees its seat", claim(o, "Replacement").status_code == 201)
    r = claim(o, "Fourth")
    check("at the limit, a claim is 409", r.status_code == 409, str(r.status_code))
    check("...and says so in plain words, with the number",
          "3 screens" in r.json().get("detail", ""), r.json().get("detail"))
    b.patch(f"/admin/accounts/{cust_id}", json={"max_screens": 4})
    check("raising the limit lets the next one in", claim(o, "Fourth, now").status_code == 201)
    b.patch(f"/admin/accounts/{cust_id}", json={"max_screens": 0})
    r = claim(o, "None allowed")
    check("a limit of zero refuses every claim", r.status_code == 409, str(r.status_code))
    b.patch(f"/admin/accounts/{cust_id}", json={"max_screens": None})
    check("no limit means claims work again", claim(o, "Unlimited").status_code == 201)
    # Only against our own seeded owner account — never pair a throwaway screen onto the real one.
    if existing_owner is None:
        check("the owner account, with no limit, claims freely", claim(b, "Staff screen").status_code == 201)

    print("\naccounts that expire")
    from datetime import timedelta

    past = (utcnow() - timedelta(minutes=1)).isoformat()
    future = (utcnow() + timedelta(days=30)).isoformat()
    lobby_id = None
    with Session(engine) as s:
        lobby_id = s.exec(select(Device).where(Device.account_id == cust_id, Device.name == "Lobby")).one().id

    r = b.patch(f"/admin/accounts/{cust_id}", json={"expires_at": future})
    check("the owner sets a client's end date", r.status_code == 200 and r.json()["expires_at"] is not None, r.text[:120])
    check("...a future one is not expired", r.json()["is_expired"] is False)
    check("...and the limits are left alone", r.json()["max_screens"] is None)
    check("before the date, changes still work", o.patch("/account", json={"default_timezone": "UTC"}).status_code == 200)
    check("the CMS's /me carries the date", o.get("/me").json()["account"]["expires_at"] is not None)

    r = b.patch(f"/admin/accounts/{cust_id}", json={"expires_at": past})
    check("a date already past is allowed, and expires it now", r.status_code == 200 and r.json()["is_expired"] is True,
          r.text[:120])
    me = o.get("/me")
    check("an expired account still signs in to the CMS", TestClient(app).post("/auth/login", json={
        "identifier": f"{PREFIX}-owner", "password": PASSWORD}).status_code == 200)
    check("/me says it has expired", me.status_code == 200 and me.json()["account"]["is_expired"] is True)
    check("it can still read: screens", o.get("/devices").status_code == 200)
    check("it can still read: media and playlists",
          o.get("/media").status_code == 200 and o.get("/playlists").status_code == 200)
    check("a sub account can still read", m.get("/devices").status_code == 200)
    r = claim(o, "After the end")
    check("pairing a screen is refused (403)", r.status_code == 403, str(r.status_code))
    check("...in plain words", "expired" in r.json().get("detail", ""), r.json().get("detail"))
    check("settings are refused", o.patch("/account", json={"default_timezone": "UTC"}).status_code == 403)
    check("a new playlist is refused", o.post("/playlists", json={"name": "Nope"}).status_code == 403)
    check("renaming a screen is refused", o.patch(f"/devices/{lobby_id}", json={"name": "Nope"}).status_code == 403)
    check("adding a sub account is refused", o.post("/users", json={
        "username": f"{PREFIX}-late", "password": PASSWORD, "display_name": "Late"}).status_code == 403)
    check("a sub account's change is refused too, not sent for review",
          m.post("/playlists", json={"name": "Nope"}).status_code == 403)
    probe = o.post(f"/devices/{lobby_id}/probe")
    check("asking a screen to check in still works", probe.status_code == 200, f"{probe.status_code} {probe.text[:80]}")
    check("signing out still works", client_for(owner_id).post("/auth/logout").status_code == 204)
    with Session(engine) as s:
        check("its screens are untouched", s.get(Device, lobby_id).disconnect_requested_at is None)

    r = t.patch(f"/admin/accounts/{cust_id}", json={"expires_at": future})
    check("a technician renews a client", r.status_code == 200 and r.json()["is_expired"] is False, r.text[:120])
    check("...and changes work again at once", o.patch("/account", json={"default_timezone": "UTC"}).status_code == 200)
    r = b.patch(f"/admin/accounts/{cust_id}", json={"expires_at": None})
    check("null removes the end date", r.status_code == 200 and r.json()["expires_at"] is None)
    naive = (utcnow() + timedelta(days=1)).replace(tzinfo=None).isoformat()
    r = b.patch(f"/admin/accounts/{cust_id}", json={"expires_at": naive})
    check("a time with no offset is read as UTC", r.status_code == 200 and r.json()["expires_at"].endswith(("Z", "+00:00")),
          r.json().get("expires_at"))
    b.patch(f"/admin/accounts/{cust_id}", json={"expires_at": None})

    check("nobody gives the owner account an end date (403)",
          b.patch(f"/admin/accounts/{paskall_id}", json={"expires_at": future}).status_code == 403)
    check("a technician cannot change their own end date (403)",
          t.patch(f"/admin/accounts/{techs_id}", json={"expires_at": None}).status_code == 403)
    r = issue(b, "ending", expires_at=future)
    check("an account can be issued with an end date", r.status_code == 201 and r.json()["expires_at"] is not None,
          r.text[:120])
    check("...and without one it has none", issue(b, "endless").json()["expires_at"] is None)
    with Session(engine) as s:
        log = s.exec(select(AdminAction).where(AdminAction.account_id == cust_id,
                                               AdminAction.action == "set_limits")).all()
        check("end date changes are logged", any("expires_at" in x.detail for x in log), str([x.detail for x in log]))

    r = b.patch(f"/admin/accounts/{techs_id}", json={"expires_at": past})
    check("the owner expires a technician", r.status_code == 200 and r.json()["is_expired"] is True)
    check("...who loses the monitoring app (403)", t.get("/admin/accounts").status_code == 403)
    r = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-tech", "password": PASSWORD})
    check("...and is told why at sign-in, not 'wrong password'", r.status_code == 403 and "expired" in r.json()["detail"],
          f"{r.status_code} {r.text[:100]}")
    wrong_tech = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-tech", "password": "not-it"})
    check("...but a wrong password is still a plain 401", wrong_tech.status_code == 401)
    check("...and cannot issue accounts", issue(t, "after-hours").status_code == 403)
    check("...but can still read their own CMS", t.get("/me").json()["account"]["is_expired"] is True)
    b.patch(f"/admin/accounts/{techs_id}", json={"expires_at": None})
    check("renewed, the technician is back in", t.get("/admin/accounts").status_code == 200)

    print("\nthe monitoring app's own sign-in: staff only")
    wrong = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-tech", "password": "not-it"})
    check("a wrong password is 401", wrong.status_code == 401, str(wrong.status_code))
    denied = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-owner", "password": PASSWORD})
    check("a client with the right password is also 401", denied.status_code == 401, str(denied.status_code))
    check("...with a byte-identical body, so trying teaches nothing", denied.content == wrong.content, denied.text)
    check("...and no cookie", settings.session_cookie_name not in denied.cookies)
    sub = TestClient(app).post("/admin/auth/login", json={"identifier": f"{PREFIX}-techsub", "password": PASSWORD})
    check("a technician's sub account is 401 too", sub.status_code == 401 and sub.content == wrong.content)
    signed_in = TestClient(app)
    ok = signed_in.post("/admin/auth/login", json={"identifier": f"{PREFIX}-tech", "password": PASSWORD})
    check("a technician signs in, and learns their kind", ok.status_code == 200 and ok.json().get("kind") == "admin",
          f"{ok.status_code} {ok.text[:80]}")
    check("...and gets a session cookie", settings.session_cookie_name in ok.cookies)
    check("/admin/me answers with them", signed_in.get("/admin/me").json().get("username") == f"{PREFIX}-tech")
    check("/admin/me is 403 for a client's session", o.get("/admin/me").status_code == 403)
    check("/admin/me is 401 with no session", TestClient(app).get("/admin/me").status_code == 401)
    check("sign-out is 204", signed_in.post("/admin/auth/logout").status_code == 204)
    check("...and /admin/me is 401 after it", signed_in.get("/admin/me").status_code == 401)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All admin checks passed.")


if __name__ == "__main__":
    main()
