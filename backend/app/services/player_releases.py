"""Every player APK ever published.

`scripts/publish_player_apk.py` never deletes an old build when it uploads a new one — it
only adds, under `apks/fortu-player-{version}.apk` — so the full version history already
lives in R2. This module just lists and sorts what's there; nothing here writes anything.
"""

import re
from dataclasses import dataclass

from app.infra import storage

_KEY_RE = re.compile(r"^apks/fortu-player-(.+)\.apk$")


@dataclass
class PlayerRelease:
    version: str
    key: str
    size_bytes: int
    uploaded_at: str  # ISO-8601, from R2's LastModified
    #: Whether this is the build `services/player_rollouts.py::active_rollout` currently
    #: says every screen should be running — not just the newest upload. A rollback (an
    #: earlier version scheduled as a new rollout) means those two can disagree, and this
    #: page should show what's actually live. Callers pass the active rollout's key in
    #: (this module has no DB access of its own — it only knows what R2 holds), so it
    #: defaults to False when the caller doesn't care.
    is_current: bool = False


def list_releases(*, current_key: str | None = None) -> list[PlayerRelease]:
    """Newest first. Skips any object under the prefix that doesn't match the naming
    convention rather than raising — a stray file in that folder must not break this page."""
    releases = []
    for obj in storage.list_objects("apks/"):
        m = _KEY_RE.match(obj["Key"])
        if not m:
            continue
        releases.append(PlayerRelease(
            version=m.group(1),
            key=obj["Key"],
            size_bytes=obj["Size"],
            uploaded_at=obj["LastModified"].isoformat(),
            is_current=obj["Key"] == current_key,
        ))
    releases.sort(key=lambda r: r.uploaded_at, reverse=True)
    return releases


def find_release(version: str, *, current_key: str | None = None) -> PlayerRelease | None:
    """Looked up by the same naming convention `publish_player_apk.py` uploads under —
    trusting the version string in the URL, verified against R2 rather than the DB, since
    there is no table of what was ever uploaded, only what's actually there."""
    key = f"apks/fortu-player-{version}.apk"
    head = storage.head_object(key)
    if head is None:
        return None
    return PlayerRelease(
        version=version,
        key=key,
        size_bytes=head["ContentLength"],
        uploaded_at=head["LastModified"].isoformat(),
        is_current=key == current_key,
    )
