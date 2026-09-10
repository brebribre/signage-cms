"""Which player build is live right now, and what's scheduled to replace it.

Replaces the old `PLAYER_LATEST_VERSION`/`PLAYER_APK_KEY` env vars — those could only be
changed by redeploying and had no notion of "later." A rollout row is created for "now" or a
future time; the active one is always just the most recent row whose time has passed, so
scheduling ahead, rolling back, or superseding a not-yet-active rollout are all the same
operation — create (or delete) a row. See `PlayerRollout`'s docstring for why this needs no
background job to "flip a switch" when the clock hits it.
"""

import uuid
from datetime import datetime

from sqlmodel import Session, select

from app.models import PlayerRollout, User
from app.models.base import utcnow
from app.services import player_releases
from app.services.errors import DomainError


class UnknownRelease(DomainError):
    pass


class RolloutNotFound(DomainError):
    pass


class RolloutAlreadyActive(DomainError):
    pass


def active_rollout(session: Session, *, now: datetime | None = None) -> PlayerRollout | None:
    """What every screen should be running right now — the most recently *scheduled* rollout
    among those whose time has already passed. `now` is injectable for tests, the same reason
    `scheduling.resolve()` takes it."""
    now = now or utcnow()
    return session.exec(
        select(PlayerRollout)
        .where(PlayerRollout.scheduled_at <= now)
        .order_by(PlayerRollout.scheduled_at.desc())
        .limit(1)
    ).first()


def list_rollouts(session: Session) -> list[PlayerRollout]:
    """Every rollout, newest-scheduled first — past and upcoming together, so the CMS can
    show one timeline instead of two separate lists."""
    return list(
        session.exec(select(PlayerRollout).order_by(PlayerRollout.scheduled_at.desc())).all()
    )


def schedule(
    session: Session, *, user: User, version: str, scheduled_at: datetime | None = None,
) -> PlayerRollout:
    """`scheduled_at=None` publishes immediately — stored as `now()`, same shape as every
    other row, just with nothing between creation and activation."""
    release = player_releases.find_release(version)
    if release is None:
        raise UnknownRelease(version)

    rollout = PlayerRollout(
        version=release.version,
        apk_key=release.key,
        scheduled_at=scheduled_at or utcnow(),
        created_by=user.id,
    )
    session.add(rollout)
    session.commit()
    session.refresh(rollout)
    return rollout


def cancel(session: Session, *, rollout_id: uuid.UUID) -> None:
    """Only a rollout that hasn't activated yet can be cancelled. Deleting one already live
    would silently roll every screen back to whatever was active before it — a decision that
    deserves its own explicit rollout, not a side effect of tidying up a list."""
    rollout = session.get(PlayerRollout, rollout_id)
    if rollout is None:
        raise RolloutNotFound(str(rollout_id))
    if rollout.scheduled_at <= utcnow():
        raise RolloutAlreadyActive(str(rollout_id))
    session.delete(rollout)
    session.commit()
