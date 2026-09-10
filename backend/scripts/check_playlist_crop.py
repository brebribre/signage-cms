"""Checkpoint for scenes: multiple positioned elements per slot, crop/placement, has_audio,
rotation_degrees, and the one-video-per-scene rule.

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
        vid2 = mk("clip2.mp4", MediaKind.VIDEO, dur=8.0)
        img = mk("a.png", MediaKind.IMAGE)
        img2 = mk("b.png", MediaKind.IMAGE)
        s.commit()

    o = client_for(owner_id)

    pl = o.post("/playlists", json={"name": f"{PREFIX} loop"}).json()
    pid = pl["id"]

    print("\ncrop fields round-trip regardless of fit")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [
            {"media_id": str(img), "fit": "contain", "crop_x": 0.3, "crop_y": 0.7, "crop_zoom": 1.5},
        ]},
    ]}).json()
    element = body["items"][0]["elements"][0]
    check("crop_x round-trips", element["crop_x"] == 0.3, str(element["crop_x"]))
    check("crop_y round-trips", element["crop_y"] == 0.7, str(element["crop_y"]))
    check("crop_zoom round-trips", element["crop_zoom"] == 1.5, str(element["crop_zoom"]))
    check("stored even though fit is contain, not cover", element["fit"] == "contain")

    print("\nhas_audio round-trips, video only")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [{"media_id": str(vid), "has_audio": True}]},
    ]}).json()
    check("has_audio round-trips true", body["items"][0]["elements"][0]["has_audio"] is True, str(body))
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [{"media_id": str(img)}]},
    ]}).json()
    check("has_audio defaults to false for a fresh element",
          body["items"][0]["elements"][0]["has_audio"] is False)

    print("\nrotation_degrees round-trips, video only")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [{"media_id": str(vid), "rotation_degrees": 90}]},
    ]}).json()
    check("rotation_degrees round-trips",
          body["items"][0]["elements"][0]["rotation_degrees"] == 90, str(body))
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [{"media_id": str(img)}]},
    ]}).json()
    check("rotation_degrees defaults to 0 for a fresh element",
          body["items"][0]["elements"][0]["rotation_degrees"] == 0)

    print("\na scene can hold multiple positioned elements")
    body = o.put(f"/playlists/{pid}/items", json={"items": [
        {"elements": [
            {"media_id": str(vid), "z_index": 0, "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            {"media_id": str(img), "z_index": 1, "x": 0.6, "y": 0.7, "width": 0.3, "height": 0.2},
            {"media_id": str(img2), "z_index": 2, "x": -0.1, "y": -0.1, "width": 0.25, "height": 0.25},
        ]},
    ]}).json()
    els = body["items"][0]["elements"]
    check("all three elements round-trip", len(els) == 3, str(len(els)))
    check("z_index order is preserved", [e["z_index"] for e in els] == [0, 1, 2], str(els))
    check("independent x/y/width/height per element",
          (els[1]["x"], els[1]["y"], els[1]["width"], els[1]["height"]) == (0.6, 0.7, 0.3, 0.2))
    check("a partially-off-canvas element is NOT clamped",
          (els[2]["x"], els[2]["y"]) == (-0.1, -0.1), str(els[2]))
    check("scene duration defaults to its one video's length (rounded)",
          body["items"][0]["duration_seconds"] == 42, str(body["items"][0]["duration_seconds"]))

    print("\nan empty scene is legal")
    body = o.put(f"/playlists/{pid}/items", json={"items": [{"elements": []}]}).json()
    check("a scene with zero elements round-trips",
          body["items"][0]["elements"] == [], str(body["items"][0]))
    check("...and falls back to the image default duration",
          body["items"][0]["duration_seconds"] == 10, str(body["items"][0]["duration_seconds"]))

    print("\nrejections")
    for label, payload in [
        ("crop_zoom below 1.0 is refused (schema-level)",
         {"items": [{"elements": [{"media_id": str(img), "crop_zoom": 0.5}]}]}),
        ("crop_zoom above MAX_CROP_ZOOM is refused (schema-level)",
         {"items": [{"elements": [{"media_id": str(img), "crop_zoom": 10.0}]}]}),
        ("crop_x out of [0,1] is refused (schema-level)",
         {"items": [{"elements": [{"media_id": str(img), "crop_x": 1.5}]}]}),
        ("has_audio on an image is refused",
         {"items": [{"elements": [{"media_id": str(img), "has_audio": True}]}]}),
        ("rotation_degrees on an image is refused",
         {"items": [{"elements": [{"media_id": str(img), "rotation_degrees": 90}]}]}),
        ("rotation_degrees not a multiple of 90 is refused (schema-level)",
         {"items": [{"elements": [{"media_id": str(vid), "rotation_degrees": 45}]}]}),
        ("a second video element in one scene is refused (hardware cap)",
         {"items": [{"elements": [
             {"media_id": str(vid)}, {"media_id": str(vid2)},
         ]}]}),
    ]:
        r = o.put(f"/playlists/{pid}/items", json=payload)
        check(label, r.status_code == 422, f"got {r.status_code}: {r.text}")

    print("\na rejected write leaves the list untouched")
    check("still the empty scene from before",
          o.get(f"/playlists/{pid}").json()["items"][0]["elements"] == [])

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All scene/crop/has_audio/rotation checks passed.")


if __name__ == "__main__":
    main()
