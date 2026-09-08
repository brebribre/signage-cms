"""Phase 5 checkpoint: the three-step upload, listing rules, and delete refusals.

Storage is stubbed by patching `app.infra.storage` — the one module that talks to boto3 —
so this runs with no R2 credentials and no network. What it cannot prove is that R2 accepts
our presigned URLs; that needs the browser in Phase 6.

Run with:  .venv/bin/python -m scripts.check_media
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
    Media,
    MediaStatus,
    Playlist,
    PlaylistItem,
    User,
    UserRole,
)
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkmedia"
settings = get_settings()
failures: list[str] = []

# --- storage stub -----------------------------------------------------------------------
# Objects that "exist", key -> size. Tests add and remove entries to simulate an upload
# landing, never landing, or landing at the wrong size.
FAKE_OBJECTS: dict[str, int] = {}
DELETED: list[str] = []


def fake_presign_put(key, content_type, ttl=None):
    return f"https://fake-r2.invalid/{key}?sig=put&ct={content_type}"


def fake_presign_get(key, ttl=None):
    return f"https://fake-r2.invalid/{key}?sig=get"


def fake_head_object(key):
    return {"ContentLength": FAKE_OBJECTS[key]} if key in FAKE_OBJECTS else None


def fake_delete_object(key):
    DELETED.append(key)
    FAKE_OBJECTS.pop(key, None)


storage.presign_put = fake_presign_put
storage.presign_get = fake_presign_get
storage.head_object = fake_head_object
storage.delete_object = fake_delete_object
# ----------------------------------------------------------------------------------------


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
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def client_for(user_id: uuid.UUID) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(user_id))
    return c


def upload(client: TestClient, filename: str, ct: str, size: int, *, land=True, land_size=None,
           thumb=True) -> tuple[int, dict]:
    """Run the whole three-step flow, optionally simulating a PUT that never landed."""
    r = client.post("/media/uploads", json={
        "filename": filename, "content_type": ct, "size_bytes": size
    })
    if r.status_code != 201:
        return r.status_code, r.json()
    media_id = r.json()["media_id"]
    with Session(engine) as s:
        m = s.get(Media, uuid.UUID(media_id))
        key, thumb_key = m.storage_key, m.thumbnail_key
    if land:
        FAKE_OBJECTS[key] = land_size if land_size is not None else size
        if thumb:
            FAKE_OBJECTS[thumb_key] = 2048
    r2 = client.post(f"/media/{media_id}/complete", json={"checksum": f"sha256:{filename}"})
    return r2.status_code, {"media_id": media_id, **(r2.json() if r2.content else {})}


def main() -> None:
    cleanup()
    with Session(engine) as s:
        account = Account(name=f"{PREFIX} account")
        s.add(account); s.flush()
        owner = User(account_id=account.id, username=f"{PREFIX}-owner",
                     password_hash=hash_password("x"), display_name="Owner", role=UserRole.OWNER)
        colleague = User(account_id=account.id, username=f"{PREFIX}-mgr",
                         password_hash=hash_password("x"), display_name="Mgr", role=UserRole.MANAGER)
        other_acct = Account(name=f"{PREFIX} other")
        s.add(other_acct); s.flush()
        outsider = User(account_id=other_acct.id, username=f"{PREFIX}-out",
                        password_hash=hash_password("x"), display_name="Out", role=UserRole.OWNER)
        s.add(owner); s.add(colleague); s.add(outsider)
        s.commit()
        for u in (owner, colleague, outsider):
            s.refresh(u)
        owner_id, mgr_id, out_id = owner.id, colleague.id, outsider.id

    o, m, x = client_for(owner_id), client_for(mgr_id), client_for(out_id)
    anon = TestClient(app)

    print("\nvalidation")
    code, body = upload(o, "notes.pdf", "application/pdf", 100)
    check("an unsupported type is 415", code == 415, str(code))
    check("the error names what is allowed", "video/mp4" in str(body), "")
    code, _ = upload(o, "huge.mp4", "video/mp4", settings.media_max_bytes + 1)
    check("a file over the limit is 413", code == 413, str(code))
    check("anonymous upload is 401", anon.post("/media/uploads", json={
        "filename": "a.png", "content_type": "image/png", "size_bytes": 10}).status_code == 401)

    print("\nthe three-step upload")
    code, ready = upload(o, "lobby.mp4", "video/mp4", 48_210_233)
    check("complete returns 200", code == 200, str(code))
    check("kind is inferred from the mime type", ready.get("kind") == "video", str(ready.get("kind")))
    check("a thumbnail url is presigned", bool(ready.get("thumbnail_url")))
    ready_id = ready["media_id"]

    print("\npending rows are invisible until confirmed")
    r = o.post("/media/uploads", json={
        "filename": "abandoned.png", "content_type": "image/png", "size_bytes": 500})
    abandoned_id = r.json()["media_id"]
    listed = [x_["id"] for x_ in o.get("/media").json()]
    check("an unconfirmed upload is not listed", abandoned_id not in listed)
    check("...but the confirmed one is", ready_id in listed)
    check("an unconfirmed upload 404s by id", o.get(f"/media/{abandoned_id}").status_code == 404)

    print("\ncompletion is verified against storage, not trusted")
    code, _ = upload(o, "never-landed.png", "image/png", 900, land=False)
    check("completing an upload that never landed is 409", code == 409, str(code))
    code, _ = upload(o, "wrong-size.png", "image/png", 900, land_size=123)
    check("completing at the wrong size is 409", code == 409, str(code))
    code, body = upload(o, "no-thumb.png", "image/png", 700, thumb=False)
    check("a missing thumbnail does not fail the upload", code == 200, str(code))
    check("...and thumbnail_url is null", body.get("thumbnail_url") is None)

    print("\nthe library is account-scoped and shared")
    upload(m, "colleague.png", "image/png", 400)
    names = sorted(i["filename"] for i in o.get("/media").json())
    check("an owner sees a manager's upload", "colleague.png" in names, str(names))
    check("a manager sees the whole account library", len(m.get("/media").json()) == len(names))
    check("another account sees none of it", x.get("/media").json() == [])
    check("another account's media 404s by id", x.get(f"/media/{ready_id}").status_code == 404)
    check("filtering by kind works", all(
        i["kind"] == "image" for i in o.get("/media?kind=image").json()))

    print("\ndetail")
    detail = o.get(f"/media/{ready_id}").json()
    check("detail carries a presigned view url", "sig=get" in detail.get("url", ""))
    check("detail reports what uses it (nothing yet)", detail.get("used_in") == [])

    print("\ndelete")
    colleague_media = next(i for i in o.get("/media").json() if i["filename"] == "colleague.png")
    check(
        "a manager cannot delete a colleague's upload (403)",
        m.delete(f"/media/{next(i for i in o.get('/media').json() if i['filename'] == 'lobby.mp4')['id']}").status_code == 403,
    )
    check(
        "a manager can delete their own",
        m.delete(f"/media/{colleague_media['id']}").status_code == 204,
    )

    print("\ndelete is refused while the file is on air")
    with Session(engine) as s:
        media = s.get(Media, uuid.UUID(ready_id))
        pl = Playlist(account_id=media.account_id, name=f"{PREFIX} Lobby Loop")
        s.add(pl); s.flush()
        s.add(PlaylistItem(playlist_id=pl.id, media_id=media.id, position=0, duration_seconds=30))
        s.commit()
    r = o.delete(f"/media/{ready_id}")
    check("deleting on-air media is 409", r.status_code == 409, str(r.status_code))
    check("...and the message names the playlist", "Lobby Loop" in r.json()["detail"], r.json()["detail"])

    with Session(engine) as s:
        s.exec(delete(PlaylistItem).where(PlaylistItem.media_id == uuid.UUID(ready_id)))
        s.commit()
    DELETED.clear()
    check("once free, delete returns 204", o.delete(f"/media/{ready_id}").status_code == 204)
    check("...and both objects are removed from storage", len(DELETED) == 2, str(DELETED))
    check("...and it is gone from the library", o.get(f"/media/{ready_id}").status_code == 404)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All media checks passed.")


if __name__ == "__main__":
    main()
