"""Checkpoint for the playlist item crop/placement and video-trim fields.

Run with:  .venv/bin/python -m scripts.check_playlist_crop
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

PREFIX = "chkcrop"
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
                s.exec(delete(Playlist).where(Playlist.id.in_([p.id for p in pls])))
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Media).where(Media.account_id.in_(ids)))
            s.exec(delete(User).where(User.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def client_for(uid: uuid.UUID) -> TestClient:
    c = TestClient(app)
    c.cookies.set(settings.session_cookie_name, create_session_token(uid))
    return c


def main() -> None:
    cleanup()
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account")
        s.add(acct)
        s.flush()
        owner = User(
            account_id=acct.id, username=f"{PREFIX}-owner", password_hash=hash_password("x"),
            display_name="O", role=UserRole.OWNER,
        )
        s.add(owner)
        s.commit()
        s.refresh(owner)
        owner_id = owner.id

        def mk(name, kind, dur=None):
            m = Media(
                account_id=acct.id, created_by=owner.id, filename=name, kind=kind,
                mime_type="video/mp4" if kind == MediaKind.VIDEO else "image/png",
                size_bytes=1000, storage_key=f"k/{name}", thumbnail_key=f"t/{name}",
                checksum=f"md5:{name}", status=MediaStatus.READY, duration_seconds=dur,
            )
            s.add(m)
            s.flush()
            return m.id

        vid = mk("clip.mp4", MediaKind.VIDEO, dur=42.4)
        img = mk("a.png", MediaKind.IMAGE)
        s.commit()

    o = client_for(owner_id)

    pl = o.post("/playlists", json={"name": f"{PREFIX} loop"}).json()
    pid = pl["id"]

    print("\ncrop fields round-trip regardless of fit")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(img), "fit": "contain", "crop_x": 0.3, "crop_y": 0.7, "crop_zoom": 1.5},
    ]}).json()
    item = body["items"][0]
    check("crop_x round-trips", item["crop_x"] == 0.3, str(item["crop_x"]))
    check("crop_y round-trips", item["crop_y"] == 0.7, str(item["crop_y"]))
    check("crop_zoom round-trips", item["crop_zoom"] == 1.5, str(item["crop_zoom"]))
    check("stored even though fit is contain, not cover", item["fit"] == "contain")
    check("trim defaults to 0 / null for a non-trimmed item",
          item["trim_start_seconds"] == 0.0 and item["trim_end_seconds"] is None)

    print("\nvideo trim round-trips")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(vid), "trim_start_seconds": 2.5, "trim_end_seconds": 10.0},
    ]}).json()
    item = body["items"][0]
    check("trim_start_seconds round-trips", item["trim_start_seconds"] == 2.5, str(item))
    check("trim_end_seconds round-trips", item["trim_end_seconds"] == 10.0, str(item))

    print("\nhas_audio round-trips, video only")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(vid), "has_audio": True},
    ]}).json()
    item = body["items"][0]
    check("has_audio round-trips true", item["has_audio"] is True, str(item))
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"media_id": str(img)},
    ]}).json()
    check("has_audio defaults to false for a fresh item", body["items"][0]["has_audio"] is False)

    print("\nrejections")
    for label, payload in [
        ("trim on an image is refused",
         {"items": [{"media_id": str(img), "trim_start_seconds": 1.0}]}),
        ("trim_end at or before trim_start is refused",
         {"items": [{"media_id": str(vid), "trim_start_seconds": 5.0, "trim_end_seconds": 5.0}]}),
        ("trim_end past the media's real duration is refused",
         {"items": [{"media_id": str(vid), "trim_end_seconds": 999.0}]}),
        ("crop_zoom below 1.0 is refused (schema-level)",
         {"items": [{"media_id": str(img), "crop_zoom": 0.5}]}),
        ("crop_zoom above MAX_CROP_ZOOM is refused (schema-level)",
         {"items": [{"media_id": str(img), "crop_zoom": 10.0}]}),
        ("crop_x out of [0,1] is refused (schema-level)",
         {"items": [{"media_id": str(img), "crop_x": 1.5}]}),
        ("has_audio on an image is refused",
         {"items": [{"media_id": str(img), "has_audio": True}]}),
    ]:
        r = o.put(f"/playlists/{pid}/items", json=payload)
        check(label, r.status_code == 422, f"got {r.status_code}: {r.text}")

    print("\na rejected write leaves the list untouched")
    check("still the 1 video item from before",
          len(o.get(f"/playlists/{pid}").json()["items"]) == 1)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All crop/trim checks passed.")


if __name__ == "__main__":
    main()
