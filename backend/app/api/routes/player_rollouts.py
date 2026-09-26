"""CMS-side scheduling of player rollouts — Marien only, session-cookie authenticated.

**A rollout is not scoped to an account.** There is one rollout timeline for the whole platform
and every screen, in every account, resolves against the same active row (services/
player_rollouts.py::active_rollout). So the guard on these routes is the only thing standing
between one caller and the software running on every screen we have.

That guard is `RequirePlatformOwner`, not `RequireOwner`. The two read almost the same and mean
very different things: `RequireOwner` is the main user of *any* account, every customer included,
which is what this file used to require. See SECURITY_REVIEW.md, C1 — with that guard an ordinary
customer could schedule a fleet-wide downgrade and cancel a rollout Marien had scheduled. It is
also narrower than `RequireStaff`: a technician services their own clients and has no business
changing what every other customer's screens run.

`GET /releases` is the exception and stays open to any account's main user, because the per-screen
version picker in the CMS reads it. It lists published build names and sizes and changes nothing.

Deliberately a separate router (and a separate prefix) from `routes/player.py`, which is
public and unauthenticated by design. Nothing here should ever be reachable without a session
— mixing the two under one prefix would make that boundary easy to blur by accident later,
same reasoning as `/device` vs `/devices`.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequireOwner, RequirePlatformOwner
from app.models import PlayerRollout
from app.schemas.player_rollouts import PlayerReleaseRead, PlayerRolloutRead, PlayerRolloutWrite
from app.services import player_releases
from app.services import player_rollouts as rollout_service
from app.services.player_rollouts import RolloutAlreadyActive, RolloutNotFound, UnknownRelease

router = APIRouter(prefix="/player-rollouts", tags=["player-rollouts"])


def _read_rollout(rollout: PlayerRollout, active_id: uuid.UUID | None) -> PlayerRolloutRead:
    return PlayerRolloutRead(
        id=rollout.id,
        version=rollout.version,
        scheduled_at=rollout.scheduled_at,
        created_at=rollout.created_at,
        is_active=rollout.id == active_id,
    )


@router.get("/releases", response_model=list[PlayerReleaseRead])
def list_releases(user: RequireOwner, session: DbSession) -> list[PlayerReleaseRead]:
    """Every build in R2, flagged with whichever one is actually live right now — the raw
    material a rollout is scheduled from.

    `RequireOwner` rather than `RequirePlatformOwner`, unlike everything else here: the CMS's
    per-screen version picker reads this, so any account's main user needs it. It is a read of
    published build names and sizes and grants nothing."""
    active = rollout_service.active_rollout(session)
    current_key = active.apk_key if active else None
    return [
        PlayerReleaseRead.model_validate(r, from_attributes=True)
        for r in player_releases.list_releases(current_key=current_key)
    ]


@router.get("/rollouts", response_model=list[PlayerRolloutRead])
def list_rollouts(user: RequirePlatformOwner, session: DbSession) -> list[PlayerRolloutRead]:
    """Every rollout ever scheduled, past and upcoming — one timeline, newest-scheduled
    first."""
    active = rollout_service.active_rollout(session)
    active_id = active.id if active else None
    return [_read_rollout(r, active_id) for r in rollout_service.list_rollouts(session)]


@router.post("/rollouts", response_model=PlayerRolloutRead, status_code=status.HTTP_201_CREATED)
def create_rollout(
    body: PlayerRolloutWrite, user: RequirePlatformOwner, session: DbSession
) -> PlayerRolloutRead:
    try:
        rollout = rollout_service.schedule(
            session, user=user, version=body.version, scheduled_at=body.scheduled_at,
        )
    except UnknownRelease:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "That version hasn't been uploaded to R2"
        ) from None
    active = rollout_service.active_rollout(session)
    return _read_rollout(rollout, active.id if active else None)


@router.delete("/rollouts/{rollout_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_rollout(rollout_id: uuid.UUID, user: RequirePlatformOwner, session: DbSession) -> None:
    """Drop a rollout that has not started yet. There is nothing to scope the id against — the
    table is deliberately platform-wide — so `RequirePlatformOwner` above is the whole check."""
    try:
        rollout_service.cancel(session, rollout_id=rollout_id)
    except RolloutNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rollout not found") from None
    except RolloutAlreadyActive:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This rollout is already live and can't be cancelled"
        ) from None
