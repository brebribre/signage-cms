"""CMS-side scheduling of player rollouts — owner-only, session-cookie authenticated.

Deliberately a separate router (and a separate prefix) from `routes/player.py`, which is
public and unauthenticated by design. Nothing here should ever be reachable without a session
— mixing the two under one prefix would make that boundary easy to blur by accident later,
same reasoning as `/device` vs `/devices`.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequireOwner
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
    material a rollout is scheduled from."""
    active = rollout_service.active_rollout(session)
    current_key = active.apk_key if active else None
    return [
        PlayerReleaseRead.model_validate(r, from_attributes=True)
        for r in player_releases.list_releases(current_key=current_key)
    ]


@router.get("/rollouts", response_model=list[PlayerRolloutRead])
def list_rollouts(user: RequireOwner, session: DbSession) -> list[PlayerRolloutRead]:
    """Every rollout ever scheduled, past and upcoming — one timeline, newest-scheduled
    first."""
    active = rollout_service.active_rollout(session)
    active_id = active.id if active else None
    return [_read_rollout(r, active_id) for r in rollout_service.list_rollouts(session)]


@router.post("/rollouts", response_model=PlayerRolloutRead, status_code=status.HTTP_201_CREATED)
def create_rollout(
    body: PlayerRolloutWrite, user: RequireOwner, session: DbSession
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
def cancel_rollout(rollout_id: uuid.UUID, user: RequireOwner, session: DbSession) -> None:
    try:
        rollout_service.cancel(session, rollout_id=rollout_id)
    except RolloutNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rollout not found") from None
    except RolloutAlreadyActive:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This rollout is already live and can't be cancelled"
        ) from None
