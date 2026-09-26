"""The review gate: what a write route does instead of applying a manager's change.

Routes call `needs_review(user)` and, when the change would reach a screen, `park(...)` — which
stores the request and answers 202 with the review, so the CMS can say "sent for review"
rather than "saved". Approval replays the stored body through the same route logic (see
routes/reviews.py), which is why the payload is the request body exactly as validated.
"""

import uuid
from collections.abc import Iterable
from typing import Any

from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models import Device, DeviceOrientation, Playlist, ReviewKind, User
from app.schemas.reviews import PendingReview, ReviewRead
from app.services import reviews as review_service
from app.services.reviews import needs_review  # re-exported for routes

__all__ = ["needs_review", "park", "read", "device_names", "playlist_names", "screen_specs"]


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
    screen_ids: Iterable[uuid.UUID] = (),
) -> JSONResponse:
    """`screen_ids` are the screens the change reaches — the same ones `screens` names — saved
    with their size and orientation so the review can preview them later (screen_specs)."""
    review = review_service.submit(
        session, user=user, kind=kind, target_id=target_id, target_name=target_name,
        summary=summary, screens=screens, payload=payload, playlists=playlists,
        screen_specs=screen_specs(session, account_id=user.account_id, device_ids=screen_ids),
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


PORTRAIT = {DeviceOrientation.DEG_90, DeviceOrientation.DEG_270}


def screen_specs(session: Session, *, account_id: uuid.UUID, device_ids: Iterable[uuid.UUID]) -> list[dict[str, Any]]:
    """The screens a change reaches, as the review's preview needs them, in name order.

    The size is the canvas content is laid out on: the panel's reported resolution turned to its
    orientation — a panel stood on its side reports landscape pixels, but the player turns content
    to portrait. Mirrors the CMS's useScreenPresets.ts::orientedSize, so a review previews the
    same shape the screen's own page does. None until the screen has reported a resolution."""
    ids = list(dict.fromkeys(device_ids))
    if not ids:
        return []
    rows = session.exec(
        select(Device).where(Device.id.in_(ids), Device.account_id == account_id).order_by(Device.name)
    ).all()
    out = []
    for d in rows:
        width = height = None
        if d.screen_width and d.screen_height:
            long, short = max(d.screen_width, d.screen_height), min(d.screen_width, d.screen_height)
            width, height = (short, long) if d.orientation in PORTRAIT else (long, short)
        out.append({
            "id": str(d.id), "name": d.name or "Unnamed screen",
            "width": width, "height": height, "orientation": d.orientation.value,
        })
    return out
