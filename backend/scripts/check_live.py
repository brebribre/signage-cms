"""Live control checkpoint: holding a screen on one scene reaches the manifest, moves its
version, refuses a scene that isn't on that screen, ends by hand and ends by itself.

Run with:  .venv/bin/python -m scripts.check_live
"""

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import (
    Account, Device, Media, MediaKind, Playlist, PlaylistItem, PlaylistItemElement, User, UserRole,
)
from app.models.base import utcnow
from app.services import devices as device_service
from app.services.passwords import hash_password
from app.services.session import create_session_token

PREFIX = "chklive"
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
        ids = [a.id for a in s.exec(select(Account).where(Account.name.startswith(PREFIX))).all()]
        if ids:
            s.exec(delete(Device).where(Device.account_id.in_(ids)))
            for p in s.exec(select(Playlist).where(Playlist.account_id.in_(ids))).all():
                for item in s.exec(select(PlaylistItem).where(PlaylistItem.playlist_id == p.id)).all():
                    s.exec(delete(PlaylistItemElement).where(PlaylistItemElement.playlist_item_id == item.id))
                s.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == p.id))
            s.exec(delete(Playlist).where(Playlist.account_id.in_(ids)))
            s.exec(delete(Media).where(Media.account_id.in_(ids)))
            s.exec(delete(Account).where(Account.id.in_(ids)))
        s.commit()


def main() -> None:
    cleanup()
    with Session(engine) as s:
        acct = Account(name=f"{PREFIX} account"); s.add(acct); s.flush()
        owner = User(account_id=acct.id, username=f"{PREFIX}-owner", password_hash=hash_password("x" * 12),
                     display_name="Owner", role=UserRole.OWNER)
        s.add(owner)
        pic = Media(account_id=acct.id, filename="a.png", kind=MediaKind.IMAGE, mime_type="image/png",
                    size_bytes=500, storage_key="k/a", thumbnail_key=None, checksum="md5:aaa")
        s.add(pic); s.flush()
        playing = Playlist(account_id=acct.id, name="On air"); s.add(playing); s.flush()
        other = Playlist(account_id=acct.id, name="Not on air"); s.add(other); s.flush()
        i1 = PlaylistItem(playlist_id=playing.id, position=0, duration_seconds=10)
        i2 = PlaylistItem(playlist_id=playing.id, position=1, duration_seconds=10)
        off = PlaylistItem(playlist_id=playing.id, position=2, duration_seconds=10, is_enabled=False)
        elsewhere = PlaylistItem(playlist_id=other.id, position=0, duration_seconds=10)
        for item in (i1, i2, off, elsewhere):
            s.add(item)
        s.flush()
        for item in (i1, i2, off, elsewhere):
            s.add(PlaylistItemElement(playlist_item_id=item.id, media_id=pic.id))
        token = "chklive-token-" + uuid.uuid4().hex
        device = Device(account_id=acct.id, name="Lobby", playlist_id=playing.id,
                        token_hash=device_service.hash_token(token), paired_at=utcnow())
        s.add(device)
        s.commit()
        for x in (owner, device, i1, i2, off, elsewhere):
            s.refresh(x)
        owner_id, device_id, playing_id = owner.id, device.id, playing.id
        slot1, slot2, slot_off, slot_elsewhere = i1.id, i2.id, off.id, elsewhere.id

    cms = TestClient(app)
    cms.cookies.set(settings.session_cookie_name, create_session_token(owner_id))
    screen = TestClient(app)
    bearer = {"Authorization": f"Bearer {token}"}

    def manifest():
        r = screen.get("/device/manifest", headers=bearer)
        assert r.status_code == 200, r.text
        return r.json()

    print("\nnothing live to begin with")
    before = manifest()
    check("manifest carries no live slot", before["live_slot_id"] is None)
    check("device read carries no live slot", cms.get(f"/devices/{device_id}").json()["live_slot_id"] is None)

    print("\nholding a scene")
    r = cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot1)})
    check("PUT live is 200", r.status_code == 200, r.text)
    check("device read shows the held scene", r.json()["live_slot_id"] == str(slot1))
    check("and since when", r.json()["live_started_at"] is not None)
    after = manifest()
    check("manifest carries the held scene", after["live_slot_id"] == str(slot1))
    check("manifest version moved", after["version"] != before["version"])
    check("the held scene is one of the manifest's slots", any(s["id"] == str(slot1) for s in after["slots"]))

    print("\nmoving the hold")
    r = cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot2)})
    check("picking another scene moves the hold", r.status_code == 200 and r.json()["live_slot_id"] == str(slot2))
    moved = manifest()
    check("manifest follows", moved["live_slot_id"] == str(slot2) and moved["version"] != after["version"])

    print("\nscenes that cannot be held")
    check("a disabled scene is refused (409)",
          cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot_off)}).status_code == 409)
    check("a scene from another playlist is refused (409)",
          cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot_elsewhere)}).status_code == 409)
    check("a made-up id is refused (409)",
          cms.put(f"/devices/{device_id}/live", json={"slot_id": str(uuid.uuid4())}).status_code == 409)
    check("the hold is untouched by refusals", manifest()["live_slot_id"] == str(slot2))

    print("\nending by hand")
    r = cms.delete(f"/devices/{device_id}/live")
    check("DELETE live is 200 and clears it", r.status_code == 200 and r.json()["live_slot_id"] is None)
    ended = manifest()
    check("manifest is back to the loop", ended["live_slot_id"] is None)
    check("version is back to the original", ended["version"] == before["version"])
    check("ending again is harmless", cms.delete(f"/devices/{device_id}/live").status_code == 200)

    print("\nending by itself")
    cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot1)})
    with Session(engine) as s:
        d = s.get(Device, device_id)
        d.live_started_at = utcnow() - timedelta(seconds=device_service.LIVE_MAX_SECONDS + 60)
        s.add(d); s.commit()
    check("an old hold reads as no hold", cms.get(f"/devices/{device_id}").json()["live_slot_id"] is None)
    expired = manifest()
    check("and the manifest is back to the loop", expired["live_slot_id"] is None and expired["version"] == before["version"])

    print("\na scene that opens with text (the manifest used to 500 on it)")
    with Session(engine) as s:
        first = PlaylistItem(playlist_id=playing_id, position=-1, duration_seconds=10)
        s.add(first); s.flush()
        s.add(PlaylistItemElement(playlist_item_id=first.id, media_id=None, text="Hello",
                                  text_style={"size": 0.1, "color": "#fff", "weight": "bold", "align": "center", "background": None}))
        s.commit()
        text_slot = first.id
    r = screen.get("/device/manifest", headers=bearer)
    check("manifest is still 200", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        check("the text scene is in slots", any(sl["id"] == str(text_slot) for sl in r.json()["slots"]))
        check("and left out of the old flat items", all(it["id"] != str(text_slot) for it in r.json()["items"]))
        check("it can be held", cms.put(f"/devices/{device_id}/live", json={"slot_id": str(text_slot)}).status_code == 200)
        cms.delete(f"/devices/{device_id}/live")

    print("\nthe playlist changing under a hold")
    cms.put(f"/devices/{device_id}/live", json={"slot_id": str(slot1)})
    with Session(engine) as s:
        d = s.get(Device, device_id)
        d.playlist_id = None
        s.add(d); s.commit()
    empty = manifest()
    check("a screen with nothing assigned sends no live slot", empty["live_slot_id"] is None and empty["slots"] == [])

    cleanup()
    print()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed: {failures}")
    print("all live control checks passed")


if __name__ == "__main__":
    main()
