"""The review gate: what a write route does instead of applying a manager's change.

Routes call `needs_review(user)` and, when the change would reach a screen, `park(...)` — which
stores the request and answers 202 with the review, so the CMS can say "sent for review"
rather than "saved". Approval replays the stored body through the same route logic (see
routes/reviews.py), which is why the payload is the request body exactly as validated.
"""

import uuid
from typing import Any

from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models import Device, Playlist, ReviewKind, User
from app.schemas.reviews import PendingReview, ReviewRead
from app.services import reviews as review_service
from app.services.reviews import needs_review  # re-exported for routes

__all__ = ["needs_review", "park", "read", "device_names", "playlist_names"]


def read(review) -> ReviewRead:
    return ReviewRead.model_validate(review, from_attributes=True)


def park(
    session: Session,
    *,
    user: User,
    kind: ReviewKind,
    target_id: uuid.UUID | None,
    target_name: str,
    summary: str,
    screens: list[str],
    payload: dict[str, Any],
    playlists: list[str] | None = None,
) -> JSONResponse:
    review = review_service.submit(
        session, user=user, kind=kind, target_id=target_id, target_name=target_name,
        summary=summary, screens=screens, payload=payload, playlists=playlists,
    )
    body = PendingReview(pending_review=read(review))
    return JSONResponse(status_code=202, content=body.model_dump(mode="json"))


def device_names(session: Session, *, account_id: uuid.UUID, device_ids: list[uuid.UUID] | set[uuid.UUID]) -> list[str]:
    """Names for the screens a change reaches, in name order. Ids outside the account are
    simply absent, same as everywhere else."""
    if not device_ids:
        return []
    return list(
        session.exec(
            select(Device.name)
            .where(Device.id.in_(list(device_ids)), Device.account_id == account_id)
            .order_by(Device.name)
        ).all()
    )


def playlist_names(session: Session, *, account_id: uuid.UUID, playlist_ids: list[uuid.UUID | None]) -> list[str]:
    """Names for the playlists a change touches, in the order given, without repeats. Ids
    outside the account, or None, are simply absent."""
    wanted = [i for i in dict.fromkeys(playlist_ids) if i is not None]
    if not wanted:
        return []
    found = {
        p.id: p.name for p in session.exec(
            select(Playlist).where(Playlist.id.in_(wanted), Playlist.account_id == account_id)
        ).all()
    }
    return [found[i] for i in wanted if i in found]
