"""Phase 14 checkpoint: storage quotas, device events, proof of play, health and pruning.

Run with:  .venv/bin/python -m scripts.check_operations
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import storage
from app.infra.db import engine
from app.main import app
from app.models import (
    Account,
    Device,
    DeviceAccess,
    DeviceEvent,
    EventLevel,
    Media,
    MediaKind,
    MediaStatus,
    PlayEvent,
    User,
    UserRole,
)
from app.services import operations
from app.services.devices import hash_token
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chkops"
settings = get_settings()
failures: list[str] = []

storage.presign_put = lambda key, content_type, ttl=None: f"https://fake/{key}"
storage.presign_get = lambda key, ttl=None: f"https://fake/{key}"
storage.head_object = lambda key: {"ContentLength": 0}


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
            devs = s.exec(select(Device).where(Device.account_id.in_(ids))).all()
            if devs:
                dids = [d.id for d in devs]
                s.exec(delete(PlayEvent).where(PlayEvent.device_id.in_(dids)))
                s.exec(delete(DeviceEvent).where(DeviceEvent.device_id.in_(dids)))
                s.exec(delete(DeviceAccess).where(DeviceAccess.device_id.in_(dids)))
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
            s.commit()


def main() -> None:
    cleanup()
    MB = 1_048_576
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account", storage_quota_bytes=10 * MB)
        s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner",
                     password_hash=hash_password("x"), display_name="O", role=UserRole.OWNER)
        s.add(owner)
        device = Device(account_id=acct.id, name="Lobby", token_hash=hash_token("ops-tok"))
        other = Device(account_id=acct.id, name="Cafe", token_hash=hash_token("ops-tok-2"))
        s.add(device); s.add(other)
        # 6 MB already used.
        s.add(Media(account_id=acct.id, filename="big.mp4", kind=MediaKind.VIDEO,
                    mime_type="video/mp4", size_bytes=6 * MB, storage_key="k/big",
                    checksum="md5:big", status=MediaStatus.READY))
        # A pending row must not be counted — it may never have been uploaded.
        s.add(Media(account_id=acct.id, filename="ghost.mp4", kind=MediaKind.VIDEO,
                    mime_type="video/mp4", size_bytes=50 * MB, storage_key="k/ghost",
                    checksum="md5:ghost", status=MediaStatus.PENDING))
        s.commit()
        for o in (owner, device, other):
            s.refresh(o)
        owner_id, acct_id, device_id, other_id = owner.id, acct.id, device.id, other.id

    cms = TestClient(app)
    cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))
    screen = TestClient(app)
    screen.headers.update({"Authorization": "Bearer ops-tok"})

    print("\nstorage accounting")
    r = cms.get("/storage").json()
    check("counts only ready media", r["used_bytes"] == 6 * MB, f"{r['used_bytes'] / MB:.0f} MB")
    check("a pending upload is not billed", r["used_bytes"] != 56 * MB)
    check("reports the quota", r["quota_bytes"] == 10 * MB)
    check("reports the file count", r["file_count"] == 1, str(r["file_count"]))

    print("\nquota is enforced before a URL is issued")
    ok = cms.post("/media/uploads", json={
        "filename": "small.png", "content_type": "image/png", "size_bytes": 1 * MB})
    check("an upload that fits is allowed", ok.status_code == 201, str(ok.status_code))
    too_big = cms.post("/media/uploads", json={
        "filename": "huge.mp4", "content_type": "video/mp4", "size_bytes": 8 * MB})
    check("an upload that would exceed the quota is 507", too_big.status_code == 507,
          str(too_big.status_code))
    check("...and the message says how full it is",
          "MB" in too_big.json()["detail"], too_big.json()["detail"])
    check("no presigned URL is handed out when refused", "upload_url" not in too_big.json())

    with Session(engine) as s:
        a = s.get(Account, acct_id); a.storage_quota_bytes = None; s.add(a); s.commit()
    # 400 MB: comfortably over the 10 MB quota that was just lifted, but still under the
    # separate per-file MEDIA_MAX_BYTES limit. The two are independent, and a test that
    # exceeds both cannot tell which one refused it.
    check("no quota means unlimited",
          cms.post("/media/uploads", json={"filename": "x.mp4", "content_type": "video/mp4",
                                           "size_bytes": 400 * MB}).status_code == 201)
    check("the per-file limit still applies with no quota",
          cms.post("/media/uploads", json={"filename": "y.mp4", "content_type": "video/mp4",
                                           "size_bytes": 900 * MB}).status_code == 413)
    with Session(engine) as s:
        a = s.get(Account, acct_id); a.storage_quota_bytes = 10 * MB; s.add(a); s.commit()

    print("\ndevice errors are persisted, not just logged")
    screen.post("/device/heartbeat", json={
        "app_version": "1.0.0", "errors": ["decoder init failed", "download timeout"]})
    events = cms.get(f"/devices/{device_id}/events").json()
    check("both errors are stored", len(events) == 2, str(len(events)))
    check("the message survives", any("decoder init failed" == e["message"] for e in events))
    check("they are recorded as errors", all(e["level"] == "error" for e in events))

    print("\nproof of play")
    started = datetime.now(UTC) - timedelta(minutes=5)
    with Session(engine) as s:
        media = s.exec(select(Media).where(Media.filename == "big.mp4")).first()
        media_id = media.id
    screen.post("/device/heartbeat", json={
        "app_version": "1.0.0", "errors": [],
        "plays": [
            {"media_id": str(media_id), "filename": "big.mp4",
             "started_at": started.isoformat(), "seconds": 30},
            {"media_id": None, "filename": "gone.png",
             "started_at": started.isoformat(), "seconds": 10},
        ],
    })
    plays = cms.get(f"/devices/{device_id}/plays").json()
    check("both plays are recorded", len(plays) == 2, str(len(plays)))
    check("duration is kept", any(p["seconds"] == 30 for p in plays))
    check("a play with no media id is still recorded",
          any(p["media_id"] is None and p["filename"] == "gone.png" for p in plays))

    print("\na play record outlives the media it refers to")
    with Session(engine) as s:
        s.exec(delete(Media).where(Media.id == media_id))
        s.commit()
    plays_after = cms.get(f"/devices/{device_id}/plays").json()
    check("the record survives the media being deleted", len(plays_after) == 2)
    check("...with media_id nulled", any(p["media_id"] is None for p in plays_after))
    check("...but the filename still says what ran",
          any(p["filename"] == "big.mp4" for p in plays_after))

    print("\nfleet health")
    health = cms.get("/health/devices").json()
    by_name = {h["name"]: h for h in health}
    check("every reachable screen appears", set(by_name) == {"Lobby", "Cafe"}, str(set(by_name)))
    check("the heartbeating screen is online", by_name["Lobby"]["is_online"] is True)
    check("a screen that never checked in is offline", by_name["Cafe"]["is_online"] is False)
    check("errors are counted over 24h", by_name["Lobby"]["error_count_24h"] == 2,
          str(by_name["Lobby"]["error_count_24h"]))
    check("plays are counted over 24h", by_name["Lobby"]["plays_24h"] == 2,
          str(by_name["Lobby"]["plays_24h"]))
    check("app version is reported", by_name["Lobby"]["app_version"] == "1.0.0")

    print("\nhealth is scoped like everything else")
    with Session(engine) as s:
        mgr = User(account_id=acct_id, username=f"{PREFIX}-mgr",
                   password_hash=hash_password("x"), display_name="M", role=UserRole.MANAGER)
        s.add(mgr); s.commit(); s.refresh(mgr)
        mgr_id = mgr.id
        s.add(DeviceAccess(user_id=mgr_id, device_id=device_id)); s.commit()
    mgr_client = TestClient(app)
    mgr_client.cookies.set(settings.session_cookie_name, create_session_token(mgr_id))
    mgr_health = mgr_client.get("/health/devices").json()
    check("a manager sees only granted screens",
          [h["name"] for h in mgr_health] == ["Lobby"], str([h["name"] for h in mgr_health]))
    check("a manager cannot read an ungranted screen's events",
          mgr_client.get(f"/devices/{other_id}/events").status_code == 404)
    check("a device token cannot read the health page",
          screen.get("/health/devices").status_code == 401)
    check("anonymous cannot read storage", TestClient(app).get("/storage").status_code == 401)

    print("\nretention")
    with Session(engine) as s:
        old = datetime.now(UTC) - timedelta(days=operations.PLAY_EVENT_RETENTION_DAYS + 5)
        s.add(PlayEvent(device_id=device_id, account_id=acct_id, filename="ancient.png",
                        started_at=old, seconds=5))
        s.add(DeviceEvent(device_id=device_id, account_id=acct_id, level=EventLevel.ERROR,
                          message="ancient error",
                          created_at=datetime.now(UTC) - timedelta(
                              days=operations.DEVICE_EVENT_RETENTION_DAYS + 5)))
        s.commit()
        pruned_plays, pruned_events = operations.prune(s)
        check("old play events are pruned", pruned_plays >= 1, str(pruned_plays))
        check("old device events are pruned", pruned_events >= 1, str(pruned_events))
        remaining = s.exec(select(PlayEvent).where(PlayEvent.device_id == device_id)).all()
        check("recent play events are kept", len(remaining) == 2, str(len(remaining)))

    cleanup()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All operations checks passed.")


if __name__ == "__main__":
    main()
