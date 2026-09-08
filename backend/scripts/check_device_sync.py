"""Phase 10 checkpoint: the manifest, its version hash, ETag/304, and the heartbeat.

Run with:  .venv/bin/python -m scripts.check_device_sync
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.infra import storage
from app.infra.db import engine
from app.main import app
from app.models import (
    Account,
    Device,
    DeviceOrientation,
    Media,
    MediaKind,
    MediaStatus,
    Playlist,
    PlaylistItem,
    User,
    UserRole,
)
from app.services import devices as device_service
from app.services.passwords import hash_password

PREFIX = "chksync"
failures: list[str] = []

captured_ttls: list[int | None] = []
_real_presign_get = storage.presign_get


def fake_presign_get(key, ttl=None):
    captured_ttls.append(ttl)
    return f"https://fake-r2.invalid/{key}?ttl={ttl}"


storage.presign_get = fake_presign_get


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


def device_client(token: str) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def main() -> None:
    cleanup()
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner", password_hash=hash_password("x"),
                     display_name="O", role=UserRole.OWNER)
        s.add(owner); s.commit()

        m1 = Media(account_id=acct.id, filename="a.mp4", kind=MediaKind.VIDEO, mime_type="video/mp4",
                   size_bytes=1000, storage_key="k/a", thumbnail_key=None, checksum="md5:aaa",
                   status=MediaStatus.READY, duration_seconds=30)
        m2 = Media(account_id=acct.id, filename="b.png", kind=MediaKind.IMAGE, mime_type="image/png",
                   size_bytes=500, storage_key="k/b", thumbnail_key=None, checksum="md5:bbb",
                   status=MediaStatus.READY)
        s.add(m1); s.add(m2); s.flush()

        playlist = Playlist(account_id=acct.id, name="Loop")
        s.add(playlist); s.flush()
        i1 = PlaylistItem(playlist_id=playlist.id, media_id=m1.id, position=0, duration_seconds=30)
        i2 = PlaylistItem(playlist_id=playlist.id, media_id=m2.id, position=1, duration_seconds=10)
        i3 = PlaylistItem(playlist_id=playlist.id, media_id=m2.id, position=2, duration_seconds=5,
                          is_enabled=False)
        s.add(i1); s.add(i2); s.add(i3)

        assigned = Device(account_id=acct.id, name="Lobby", token_hash=device_service.hash_token("tok-a"),
                          playlist_id=playlist.id)
        unassigned = Device(account_id=acct.id, name="Spare", token_hash=device_service.hash_token("tok-b"))
        s.add(assigned); s.add(unassigned)
        s.commit()
        s.refresh(playlist); s.refresh(assigned); s.refresh(unassigned)
        playlist_id, device_id, unassigned_id = playlist.id, assigned.id, unassigned.id
        owner_id = owner.id
        m1_id, m2_id = m1.id, m2.id
        acct_id = acct.id

    lobby = device_client("tok-a")
    spare = device_client("tok-b")
    anon = TestClient(app)

    print("\nauthentication")
    check("no token is 401", anon.get("/device/manifest").status_code == 401)
    check("a wrong token is 401",
          device_client("not-a-real-token").get("/device/manifest").status_code == 401)

    print("\nan unassigned device gets a valid empty manifest, not a 404")
    r = spare.get("/device/manifest")
    body = r.json()
    check("status is 200", r.status_code == 200, str(r.status_code))
    check("playlist is null", body["playlist"] is None)
    check("items is empty", body["items"] == [])
    check("device info is still present", body["device"]["name"] == "Spare")

    print("\nan assigned device gets the full manifest")
    r = lobby.get("/device/manifest")
    body = r.json()
    v1 = body["version"]
    check("status is 200", r.status_code == 200)
    check("two items, disabled one excluded", len(body["items"]) == 2, str(len(body["items"])))
    check("order matches position", [i["duration_seconds"] for i in body["items"]] == [30, 10])
    check("kind is carried through", body["items"][0]["kind"] == "video")
    check("checksum is carried through", body["items"][0]["checksum"] == "md5:aaa")
    check("bytes is carried through", body["items"][0]["bytes"] == 1000)
    check("fit defaults through", body["items"][0]["fit"] == "contain")
    check("playlist name and shuffle are present", body["playlist"]["name"] == "Loop"
          and body["playlist"]["shuffle"] is False)
    check("an ETag header is set", r.headers.get("etag") == f'"{v1}"', r.headers.get("etag"))
    check(
        "item URLs are presigned with the DEVICE ttl, not the CMS one",
        any("ttl=21600" in i["url"] for i in body["items"]),
        str([i["url"] for i in body["items"]]),
    )

    print("\nconditional GET — the whole point of the version hash")
    r2 = lobby.get("/device/manifest", headers={"If-None-Match": f'"{v1}"'})
    check("a repeat with the matching ETag is 304", r2.status_code == 304, str(r2.status_code))
    check("a 304 has no body", r2.content == b"", repr(r2.content))
    check("a 304 still carries the ETag", r2.headers.get("etag") == f'"{v1}"')
    ttl_calls_before = len(captured_ttls)
    lobby.get("/device/manifest", headers={"If-None-Match": f'"{v1}"'})
    check(
        "a 304 does not presign anything (cheap by design)",
        len(captured_ttls) == ttl_calls_before,
        f"{len(captured_ttls) - ttl_calls_before} presigns happened",
    )
    r3 = lobby.get("/device/manifest", headers={"If-None-Match": '"sha256:not-the-real-one"'})
    check("a stale ETag is a normal 200, not a 304", r3.status_code == 200)

    print("\nthe version tracks content, and only content")
    # Through the real service, not raw ORM mutation: swapping two rows' positions with a
    # direct UPDATE collides with the UniqueConstraint mid-transaction (0,0 exists
    # momentarily), which is exactly what the delete-then-reinsert shape in
    # `playlist_service.replace_items` exists to avoid. Exercising the actual write path
    # here is also the more honest test.
    from app.services import playlists as playlist_service
    from app.services.playlists import ItemSpec

    with Session(engine) as s:
        owner_obj = s.get(User, owner_id)
        playlist_service.replace_items(
            s, user=owner_obj, playlist_id=playlist_id,
            items=[ItemSpec(media_id=m2_id, duration_seconds=10),
                   ItemSpec(media_id=m1_id, duration_seconds=30),
                   ItemSpec(media_id=m2_id, duration_seconds=5, is_enabled=False)],
        )
    v_reorder = lobby.get("/device/manifest").json()["version"]
    check("reordering changes the version", v_reorder != v1)

    with Session(engine) as s:
        owner_obj = s.get(User, owner_id)
        playlist_service.replace_items(
            s, user=owner_obj, playlist_id=playlist_id,
            items=[ItemSpec(media_id=m2_id, duration_seconds=999),
                   ItemSpec(media_id=m1_id, duration_seconds=30),
                   ItemSpec(media_id=m2_id, duration_seconds=5, is_enabled=False)],
        )
    v_duration = lobby.get("/device/manifest").json()["version"]
    check("editing a duration changes the version", v_duration != v_reorder)

    with Session(engine) as s:
        s.add(Playlist(id=uuid.uuid4(), account_id=acct_id, name="Other")); s.commit()
    with Session(engine) as s:
        other = s.exec(select(Playlist).where(Playlist.name == "Other")).first()
        dev = s.get(Device, device_id)
        dev.playlist_id = other.id
        s.add(dev); s.commit()
    v_reassigned = lobby.get("/device/manifest").json()["version"]
    check("reassigning the playlist changes the version", v_reassigned != v_duration)

    v_before_rename = v_reassigned
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        dev.name = "Renamed Lobby"
        s.add(dev); s.commit()
    v_after_rename = lobby.get("/device/manifest").json()["version"]
    check("renaming the DEVICE does not change the version", v_after_rename == v_before_rename)

    with Session(engine) as s:
        other = s.exec(select(Playlist).where(Playlist.name == "Other")).first()
        other.name = "Renamed playlist"
        s.add(other); s.commit()
    v_after_playlist_rename = lobby.get("/device/manifest").json()["version"]
    check("renaming the PLAYLIST does not change the version",
          v_after_playlist_rename == v_after_rename)

    with Session(engine) as s:
        dev = s.get(Device, device_id)
        dev.orientation = DeviceOrientation.PORTRAIT
        s.add(dev); s.commit()
    v_after_orientation = lobby.get("/device/manifest").json()["version"]
    check("changing orientation DOES change the version (extends the plan)",
          v_after_orientation != v_after_playlist_rename)

    print("\nheartbeat")
    r = lobby.post("/device/heartbeat", json={
        "app_version": "1.0.0", "screen": {"width": 3840, "height": 2160},
        "current_item_id": None, "errors": [],
    })
    check("heartbeat returns 200 with the current version", r.status_code == 200)
    check("heartbeat's version matches the manifest's",
          r.json()["version"] == lobby.get("/device/manifest").json()["version"])
    with Session(engine) as s:
        dev = s.get(Device, device_id)
        check("last_seen_at was set", dev.last_seen_at is not None)
        check("app_version was recorded", dev.app_version == "1.0.0")
        check("resolution was recorded", (dev.screen_width, dev.screen_height) == (3840, 2160))

    check("heartbeat without a token is 401",
          anon.post("/device/heartbeat", json={"errors": []}).status_code == 401)
    r = lobby.post("/device/heartbeat", json={"errors": ["decoder init failed"]})
    check("an error report does not fail the request", r.status_code == 200)

    print("\nself-update offers (Phase 12c)")
    from app.config import get_settings as _gs
    settings_obj = _gs()
    original = (settings_obj.player_latest_version, settings_obj.player_apk_key)
    try:
        # Unconfigured is the default, and must never offer anything: a blank version
        # cannot accidentally push an APK to every screen.
        settings_obj.player_latest_version = ""
        settings_obj.player_apk_key = ""
        r = lobby.post("/device/heartbeat", json={"app_version": "1.0.0", "errors": []})
        check("no update offered when unconfigured", r.json()["update"] is None)

        settings_obj.player_latest_version = "1.1.0"
        settings_obj.player_apk_key = "apks/fortu-player-1.1.0.apk"

        r = lobby.post("/device/heartbeat", json={"app_version": "1.0.0", "errors": []})
        upd = r.json()["update"]
        check("an out-of-date screen is offered the update", upd is not None)
        check("...with the published version", upd and upd["version"] == "1.1.0", str(upd))
        check("...and a presigned URL at the device TTL",
              upd and "ttl=21600" in upd["url"], str(upd and upd["url"])[:60])

        r = lobby.post("/device/heartbeat", json={"app_version": "1.1.0", "errors": []})
        check("a screen already on the published build is offered nothing",
              r.json()["update"] is None)

        # A rollback is a config change, not a field visit — so a *newer* device version
        # must still be offered the older published one.
        r = lobby.post("/device/heartbeat", json={"app_version": "2.0.0", "errors": []})
        check("a newer screen is offered the published build (rollback works)",
              r.json()["update"] is not None)

        # Pushing blind to a device that has never said what it runs would risk an install
        # loop on every heartbeat.
        with Session(engine) as s:
            d = s.get(Device, device_id); d.app_version = None; s.add(d); s.commit()
        r = lobby.post("/device/heartbeat", json={"errors": []})
        check("a screen that never reported a version is offered nothing",
              r.json()["update"] is None)
    finally:
        settings_obj.player_latest_version, settings_obj.player_apk_key = original

    print("\nno mixing credentials")
    with Session(engine) as s:
        u = s.get(User, owner.id)
    from app.services.session import create_session_token
    cookie_client = TestClient(app)
    cookie_client.cookies.set("scms_session", create_session_token(owner.id))
    check("a session cookie cannot call /device/manifest",
          cookie_client.get("/device/manifest").status_code == 401)
    check("a device token cannot call /devices",
          lobby.get("/devices").status_code == 401)

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All device sync checks passed.")


if __name__ == "__main__":
    main()
