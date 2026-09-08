"""Phase 7 checkpoint: whole-list replace, ordering, validation and delete refusals.

Run with:  .venv/bin/python -m scripts.check_playlists
"""

import uuid

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
    User,
    UserRole,
)
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkpl"
settings = get_settings()
failures: list[str] = []

storage.presign_get = lambda key, ttl=None: f"https://fake/{key}"


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
            pls = s.exec(select(Playlist).where(Playlist.account_id.in_(ids))).all()
            if pls:
                s.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id.in_([p.id for p in pls])))
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

        def mk(name, kind, dur=None, status=MediaStatus.READY, account=None):
            m = Media(account_id=account or acct.id, created_by=owner.id, filename=name, kind=kind,
                      mime_type="video/mp4" if kind == MediaKind.VIDEO else "image/png",
                      size_bytes=1000, storage_key=f"k/{name}", thumbnail_key=f"t/{name}",
                      checksum=f"md5:{name}", status=status, duration_seconds=dur)
            s.add(m); s.flush(); return m.id

        vid = mk("clip.mp4", MediaKind.VIDEO, dur=42.4)
        img_a = mk("a.png", MediaKind.IMAGE)
        img_b = mk("b.png", MediaKind.IMAGE)
        pending = mk("half.png", MediaKind.IMAGE, status=MediaStatus.PENDING)
        foreign = mk("theirs.png", MediaKind.IMAGE, account=other.id)
        s.commit()

    o, m, x = client_for(owner_id), client_for(mgr_id), client_for(out_id)

    print("\ncreate and list")
    pl = o.post("/playlists", json={"name": "Lobby Loop"}).json()
    pid = pl["id"]
    check("create returns an empty playlist", pl["item_count"] == 0 and pl["items"] == [])
    check("shuffle defaults to false", pl["shuffle"] is False)
    check("it appears in the list", any(p["id"] == pid for p in o.get("/playlists").json()))
    check("another account cannot see it", x.get(f"/playlists/{pid}").status_code == 404)

    print("\nreplace items — the whole list, in order")
    r = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(img_a)}, {"media_id": str(vid)}, {"media_id": str(img_b)}]})
    body = r.json()
    check("replace returns 200", r.status_code == 200, str(r.status_code))
    check("positions come from the array index", [i["position"] for i in body["items"]] == [0, 1, 2])
    check("order is preserved", [i["media"]["filename"] for i in body["items"]] == ["a.png", "clip.mp4", "b.png"])
    check("an image gets the default duration", body["items"][0]["duration_seconds"] == 10)
    check("a video defaults to its own length (rounded)", body["items"][1]["duration_seconds"] == 42,
          str(body["items"][1]["duration_seconds"]))
    check("fit defaults to contain", all(i["fit"] == "contain" for i in body["items"]))
    check("items are enabled by default", all(i["is_enabled"] for i in body["items"]))
    check("total duration is summed", body["total_duration_seconds"] == 10 + 42 + 10,
          str(body["total_duration_seconds"]))

    print("\nreplace is a replace, not an append")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(img_b)}, {"media_id": str(img_a)}]}).json()
    check("the list is exactly what was sent", [i["media"]["filename"] for i in body["items"]] == ["b.png", "a.png"])
    check("no duplicate rows survive", body["item_count"] == 2, str(body["item_count"]))
    with Session(engine) as s:
        rows = s.exec(select(PlaylistItem).where(PlaylistItem.playlist_id == uuid.UUID(pid))).all()
    check("...verified in the database too", len(rows) == 2, f"{len(rows)} rows")

    print("\nper-item fit, duration and enable")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(img_a), "duration_seconds": 25, "fit": "cover"},
        {"media_id": str(vid), "duration_seconds": 15, "fit": "stretch", "is_enabled": False}]}).json()
    check("explicit duration overrides the default", body["items"][0]["duration_seconds"] == 25)
    check("a video can be cut short", body["items"][1]["duration_seconds"] == 15)
    check("fit round-trips", [i["fit"] for i in body["items"]] == ["cover", "stretch"])
    check("a disabled item keeps its position", body["items"][1]["is_enabled"] is False)
    check("disabled items are excluded from the count", body["item_count"] == 1, str(body["item_count"]))
    check("...and from the total duration", body["total_duration_seconds"] == 25,
          str(body["total_duration_seconds"]))

    print("\nthe list and the detail agree")
    summary = next(p for p in o.get("/playlists").json() if p["id"] == pid)
    detail = o.get(f"/playlists/{pid}").json()
    check("list item_count matches detail", summary["item_count"] == detail["item_count"],
          f"list {summary['item_count']} vs detail {detail['item_count']}")
    check("list total duration matches detail",
          summary["total_duration_seconds"] == detail["total_duration_seconds"],
          f"list {summary['total_duration_seconds']} vs detail {detail['total_duration_seconds']}")
    check("both exclude the disabled item", summary["item_count"] == 1, str(summary["item_count"]))

    print("\nvalidation")
    for label, payload, code in [
        ("media from another account is refused", {"items": [{"media_id": str(foreign)}]}, 422),
        ("media still uploading is refused", {"items": [{"media_id": str(pending)}]}, 422),
        ("a media id that does not exist is refused", {"items": [{"media_id": str(uuid.uuid4())}]}, 422),
        ("duration below the minimum is refused", {"items": [{"media_id": str(img_a), "duration_seconds": 0}]}, 422),
        ("duration above the maximum is refused", {"items": [{"media_id": str(img_a), "duration_seconds": 99999}]}, 422),
        ("an unknown fit value is refused", {"items": [{"media_id": str(img_a), "fit": "warp"}]}, 422),
    ]:
        check(label, o.put(f"/playlists/{pid}/items", json=payload).status_code == code)
    check("the failed writes left the list untouched",
          len(o.get(f"/playlists/{pid}").json()["items"]) == 2)

    print("\nan empty playlist is legal")
    body = o.put(f"/playlists/{pid}/items", json={"items": []}).json()
    check("emptying returns 200 with no items", body["items"] == [] and body["item_count"] == 0)

    print("\nrename and shuffle")
    body = o.patch(f"/playlists/{pid}", json={"name": "Cafe Loop", "shuffle": True}).json()
    check("rename applies", body["name"] == "Cafe Loop")
    check("shuffle applies", body["shuffle"] is True)

    print("\ndelete is refused while a screen points at it")
    with Session(engine) as s:
        acct_id = s.get(Playlist, uuid.UUID(pid)).account_id
        s.add(Device(account_id=acct_id, name="Lobby screen", playlist_id=uuid.UUID(pid)))
        s.commit()
    r = o.delete(f"/playlists/{pid}")
    check("deleting an assigned playlist is 409", r.status_code == 409, str(r.status_code))
    check("...and the message names the screen", "Lobby screen" in r.json()["detail"], r.json()["detail"])
    check("detail reports which screens use it",
          o.get(f"/playlists/{pid}").json()["used_by"] == ["Lobby screen"])

    with Session(engine) as s:
        for d in s.exec(select(Device).where(Device.playlist_id == uuid.UUID(pid))).all():
            d.playlist_id = None; s.add(d)
        s.commit()

    print("\nmanager scoping")
    mine = m.post("/playlists", json={"name": "Manager's own"}).json()
    check("a manager can create a playlist", mine["name"] == "Manager's own")
    check("a manager cannot delete someone else's", m.delete(f"/playlists/{pid}").status_code == 403)
    check("a manager can delete their own", m.delete(f"/playlists/{mine['id']}").status_code == 204)
    check("an owner can delete anything", o.delete(f"/playlists/{pid}").status_code == 204)
    check("...and it is gone", o.get(f"/playlists/{pid}").status_code == 404)

    print("\nthe media it referenced survives")
    with Session(engine) as s:
        check("deleting a playlist does not delete media",
              s.get(Media, img_a) is not None and s.get(Media, vid) is not None)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All playlist checks passed.")


if __name__ == "__main__":
    main()
