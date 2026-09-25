"""End-to-end check of the review flow through the real HTTP routes, on the dev database.

    .venv/bin/python -m scripts.check_reviews <owner-user-id> <screen-id> <playlist-id>

Creates a throwaway manager granted the screen, drives every branch of the review gate as
that manager and as the owner, prints PASS/FAIL per step, and removes what it made. The
playlist is restored to its scenes afterwards. See ACCOUNTS.md for how sub accounts and reviews work.
"""
import secrets, uuid, sys
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.infra.db import engine
from app.models import User, ContentReview, Campaign
from app.services import users as user_service
from app.services.session import create_session_token
from app.config import get_settings

if len(sys.argv) != 4:
    sys.exit(__doc__)
OWNER = uuid.UUID(sys.argv[1])
SCREEN = sys.argv[2]
PLAYLIST = sys.argv[3]
COOKIE = get_settings().session_cookie_name

with Session(engine) as s:
    owner = s.get(User, OWNER)
    mgr = s.exec(select(User).where(User.username == "review-test-mgr")).first()
    if mgr is None:
        mgr = user_service.create_manager(
            s, owner=owner, username="review-test-mgr", password=secrets.token_urlsafe(16),
            display_name="Review Test Manager", email=None, device_ids=[uuid.UUID(SCREEN)],
        )
    # Its password was chosen by the owner, so it's temporary and every route but changing it is
    # refused; these checks are about reviews, so the manager stands in as having picked their own.
    mgr.must_change_password = False
    s.add(mgr)
    s.commit()
    MGR = mgr.id
    # Clean slate for the test account's reviews.
    for r in s.exec(select(ContentReview).where(ContentReview.account_id == owner.account_id)).all():
        s.delete(r)
    for c in s.exec(select(Campaign).where(Campaign.name.in_(["Review test campaign", "Manager campaign", "Doomed"]))).all():
        s.delete(c)
    s.commit()

def client(uid):
    c = TestClient(app, raise_server_exceptions=True)
    c.cookies.set(COOKIE, create_session_token(uid))
    return c

o, m = client(OWNER), client(MGR)
ok = lambda cond, msg: print(("PASS " if cond else "FAIL ") + msg) or cond
results = []

# Owner: put the playlist on the screen through a campaign, so it reaches a screen.
r = o.post("/campaigns", json={"name": "Review test campaign", "device_ids": [SCREEN],
                               "rules": [{"playlist_id": PLAYLIST}]})
results.append(ok(r.status_code == 201, f"owner creates campaign directly: {r.status_code}"))
camp_id = r.json()["campaign"]["id"]
detail = o.get(f"/playlists/{PLAYLIST}").json()
results.append(ok(detail["used_by"] == ["UI Test Screen"], f"playlist reaches the screen: {detail['used_by']}"))
items = [{"duration_seconds": i["duration_seconds"], "is_enabled": i["is_enabled"], "background": i["background"],
          "elements": [dict({k: e.get(k) for k in ("web_url","z_index","x","y","width","height","fit","crop_x","crop_y","crop_zoom","has_audio","rotation_degrees")},
                            media_id=(e.get("media") or {}).get("id") or e.get("media_id")) for e in i["elements"]]}
         for i in detail["items"]]

# Manager: saving the on-air playlist is parked.
r = m.put(f"/playlists/{PLAYLIST}/items", json={"items": items[:1]})
results.append(ok(r.status_code == 202 and "pending_review" in r.json(), f"manager's on-air playlist save is parked: {r.status_code}"))
rev1 = r.json()["pending_review"]
results.append(ok(rev1["screens"] == ["UI Test Screen"] and rev1["kind"] == "playlist_items", f"review names the screen: {rev1['summary']} → {rev1['screens']}"))
results.append(ok(len(o.get(f"/playlists/{PLAYLIST}").json()["items"]) == len(items), "playlist unchanged until approved"))

# Manager: a playlist nobody plays saves directly.
r = m.post("/playlists", json={"name": "Review test scratch"})
scratch = r.json()["id"]
r = m.put(f"/playlists/{scratch}/items", json={"items": items[:1]})
results.append(ok(r.status_code == 200, f"manager's unused playlist saves at once: {r.status_code}"))

# Manager: a campaign is always parked; the owner rejects it with a note.
r = m.post("/campaigns", json={"name": "Manager campaign", "device_ids": [SCREEN], "rules": [{"playlist_id": scratch}]})
results.append(ok(r.status_code == 202, f"manager's campaign is parked: {r.status_code}"))
rev2 = r.json()["pending_review"]
r = m.get("/reviews"); results.append(ok(len(r.json()) == 2 and all(x["requested_by"] == str(MGR) for x in r.json()), "manager sees their two reviews"))
r = o.get("/reviews/pending-count"); results.append(ok(r.json()["count"] == 2, f"owner badge count: {r.json()}"))
r = m.post(f"/reviews/{rev2['id']}/approve", json={}); results.append(ok(r.status_code == 403, f"manager cannot approve: {r.status_code}"))
r = o.post(f"/reviews/{rev2['id']}/reject", json={"note": "Not this week"}); results.append(ok(r.status_code == 200 and r.json()["status"] == "rejected" and r.json()["note"] == "Not this week", "owner rejects with a note"))
with Session(engine) as s:
    results.append(ok(s.exec(select(Campaign).where(Campaign.name == "Manager campaign")).first() is None, "rejected campaign was never created"))

# Owner approves the playlist change: it lands, attributed to the manager's request.
r = o.post(f"/reviews/{rev1['id']}/approve", json={}); results.append(ok(r.status_code == 200 and r.json()["status"] == "approved", f"owner approves: {r.status_code} {r.json().get('detail','')}"))
results.append(ok(len(o.get(f"/playlists/{PLAYLIST}").json()["items"]) == 1, "approved change is on the playlist"))
r = o.post(f"/reviews/{rev1['id']}/approve", json={}); results.append(ok(r.status_code == 409, f"approving twice is refused: {r.status_code}"))

# Shuffle on an on-air playlist is parked; the manager withdraws it.
r = m.patch(f"/playlists/{PLAYLIST}", json={"shuffle": True}); results.append(ok(r.status_code == 202, f"shuffle change parked: {r.status_code}"))
rev3 = r.json()["pending_review"]
r = m.post(f"/reviews/{rev3['id']}/withdraw", json={}); results.append(ok(r.status_code == 200 and r.json()["status"] == "withdrawn", "manager withdraws")) 
r = m.patch(f"/playlists/{PLAYLIST}", json={"name": "test"}); results.append(ok(r.status_code == 200, f"rename applies at once: {r.status_code}"))

# A review whose target vanished cannot be applied, and stays pending.
r = m.put(f"/playlists/{scratch}/items", json={"items": []})  # unused → direct
r = m.post("/campaigns", json={"name": "Doomed", "device_ids": [SCREEN], "rules": [{"playlist_id": scratch}]})
rev4 = r.json()["pending_review"]
o.delete(f"/playlists/{scratch}")
r = o.post(f"/reviews/{rev4['id']}/approve", json={}); results.append(ok(r.status_code == 409, f"stale review refused with reason: {r.status_code} {r.json().get('detail')}"))
r = o.get("/reviews"); results.append(ok([x["status"] for x in r.json()][:1] == ["pending"], "stale review still pending at the top of the queue"))

# Restore the playlist to its original scenes and clean up.
o.put(f"/playlists/{PLAYLIST}/items", json={"items": items})
o.delete(f"/campaigns/{camp_id}")
with Session(engine) as s:
    for r in s.exec(select(ContentReview).where(ContentReview.requested_by_name == "Review Test Manager")).all():
        s.delete(r)
    mgr = s.exec(select(User).where(User.username == "review-test-mgr")).first()
    if mgr is not None:
        user_service.delete_user(s, owner=s.get(User, OWNER), user_id=mgr.id)
    s.commit()
print(f"\n{sum(results)}/{len(results)} passed")
