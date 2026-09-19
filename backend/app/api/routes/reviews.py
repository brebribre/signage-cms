"""The Reviews page: a manager's screen-changing saves, waiting for the owner.

Approving replays the stored request as the manager who sent it — same service call, same
screen grants, same validation — so an approved change is exactly what a direct save by that
manager would have been, had they been allowed one. If the replay fails (the playlist was
deleted meanwhile, the manager was deactivated, a rule no longer validates) the review stays
pending and the owner sees why; nothing is marked approved for a change that did not land.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api import deps
from app.api.deps import CurrentUser, DbSession, RequireOwner
from app.api.review_gate import read
from app.api.routes.campaigns import _rule_inputs
from app.api.routes.playlists import item_specs
from app.models import ContentReview, ReviewKind, ReviewStatus, User
from app.schemas.campaigns import CampaignWrite
from app.schemas.playlists import ItemsWrite
from app.schemas.reviews import PendingCount, ReviewDecision, ReviewRead
from app.schemas.schedules import ScheduleUpdate, ScheduleWrite
from app.services import campaigns as campaign_service
from app.services import devices as device_service
from app.services import playlists as playlist_service
from app.services import reviews as review_service
from app.services import schedules as schedule_service
from app.services.errors import DomainError
from app.services.reviews import NotPending, ReviewNotFound

router = APIRouter(tags=["reviews"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")


class CannotApply(Exception):
    """The change no longer applies as sent. The review stays pending; the owner reads why."""


def _apply(session: DbSession, review: ContentReview, requester: User) -> None:
    kind = review.kind
    payload = review.payload
    try:
        if kind == ReviewKind.PLAYLIST_ITEMS:
            body = ItemsWrite.model_validate(payload)
            playlist_service.replace_items(
                session, user=requester, playlist_id=review.target_id, items=item_specs(body),
            )
        elif kind == ReviewKind.PLAYLIST_SHUFFLE:
            playlist_service.update(
                session, user=requester, playlist_id=review.target_id, shuffle=bool(payload["shuffle"]),
            )
        elif kind == ReviewKind.CAMPAIGN_CREATE:
            body = CampaignWrite.model_validate(payload)
            campaign_service.create(
                session, user=requester, name=body.name, device_ids=body.device_ids, rules=_rule_inputs(body),
            )
        elif kind == ReviewKind.CAMPAIGN_UPDATE:
            body = CampaignWrite.model_validate(payload)
            campaign = campaign_service.get(session, user=requester, campaign_id=review.target_id)
            campaign_service.update(
                session, user=requester, campaign=campaign, name=body.name,
                device_ids=body.device_ids, rules=_rule_inputs(body),
            )
        elif kind == ReviewKind.CAMPAIGN_DELETE:
            campaign = campaign_service.get(session, user=requester, campaign_id=review.target_id)
            campaign_service.remove(session, campaign=campaign)
        elif kind == ReviewKind.SCHEDULE_CREATE:
            body = ScheduleWrite.model_validate(payload)
            device = deps.device_for_user(review.target_id, requester, session)
            schedule_service.create(
                session, user=requester, device=device, playlist_id=body.playlist_id,
                name=body.name, days_of_week=body.days_of_week,
                starts_at=body.starts_at, ends_at=body.ends_at, priority=body.priority,
            )
        elif kind == ReviewKind.SCHEDULE_UPDATE:
            body = ScheduleUpdate.model_validate(payload)
            schedule = schedule_service.get(session, user=requester, schedule_id=review.target_id)
            schedule_service.update(
                session, user=requester, schedule=schedule,
                playlist_id=body.playlist_id, name=body.name,
                days_of_week=body.days_of_week, starts_at=body.starts_at,
                ends_at=body.ends_at, priority=body.priority, is_enabled=body.is_enabled,
            )
        elif kind == ReviewKind.SCHEDULE_DELETE:
            schedule = schedule_service.get(session, user=requester, schedule_id=review.target_id)
            schedule_service.remove(session, schedule=schedule)
        elif kind == ReviewKind.DEVICE_PLAYLIST:
            device = deps.device_for_user(review.target_id, requester, session)
            playlist_id = payload.get("playlist_id")
            device_service.update(
                session, user=requester, device=device,
                playlist_id=uuid.UUID(playlist_id) if playlist_id else None,
                clear_playlist=bool(payload.get("clear_playlist")),
            )
        else:  # pragma: no cover — a kind added without a branch here
            raise CannotApply(f"unknown change kind {kind}")
    except HTTPException as exc:
        # deps.device_for_user answers 404 the way the route would.
        raise CannotApply(str(exc.detail)) from None
    except DomainError as exc:
        raise CannotApply(str(exc) or exc.__class__.__name__) from None
    except (KeyError, ValueError) as exc:
        raise CannotApply(f"the stored change is not valid any more: {exc}") from None


@router.get("/reviews", response_model=list[ReviewRead])
def list_reviews(user: CurrentUser, session: DbSession) -> list[ReviewRead]:
    """The owner sees the account's queue; a manager sees what they sent."""
    return [read(r) for r in review_service.list_for(session, user=user)]


@router.get("/reviews/pending-count", response_model=PendingCount)
def pending_count(user: CurrentUser, session: DbSession) -> PendingCount:
    """For the badge in the sidebar."""
    return PendingCount(count=review_service.pending_count(session, user=user))


@router.get("/reviews/{review_id}", response_model=ReviewRead)
def get_review(review_id: uuid.UUID, user: CurrentUser, session: DbSession) -> ReviewRead:
    """One review with its full payload — what the review page previews. A manager can open
    only their own; the owner any in the account."""
    try:
        return read(review_service.get(session, user=user, review_id=review_id))
    except ReviewNotFound:
        raise NOT_FOUND from None


@router.post("/reviews/{review_id}/approve", response_model=ReviewRead)
def approve(review_id: uuid.UUID, body: ReviewDecision, owner: RequireOwner, session: DbSession) -> ReviewRead:
    try:
        review = review_service.get(session, user=owner, review_id=review_id)
    except ReviewNotFound:
        raise NOT_FOUND from None
    if review.status != ReviewStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This review was already {review.status}")
    requester = review_service.requester(session, review)
    if requester is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The person who sent this is no longer an active user, so it can only be rejected",
        )
    try:
        _apply(session, review, requester)
    except CannotApply as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Could not apply this change: {exc}") from None
    return read(review_service.mark_approved(session, owner=owner, review=review, note=body.note))


@router.post("/reviews/{review_id}/reject", response_model=ReviewRead)
def reject(review_id: uuid.UUID, body: ReviewDecision, owner: RequireOwner, session: DbSession) -> ReviewRead:
    try:
        review = review_service.get(session, user=owner, review_id=review_id)
        return read(review_service.reject(session, owner=owner, review=review, note=body.note))
    except ReviewNotFound:
        raise NOT_FOUND from None
    except NotPending as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This review was already {exc}") from None


@router.post("/reviews/{review_id}/withdraw", response_model=ReviewRead)
def withdraw(review_id: uuid.UUID, user: CurrentUser, session: DbSession) -> ReviewRead:
    """A manager taking back their own pending request. An owner may too, on any."""
    try:
        review = review_service.get(session, user=user, review_id=review_id)
        return read(review_service.withdraw(session, user=user, review=review))
    except ReviewNotFound:
        raise NOT_FOUND from None
    except NotPending as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This review was already {exc}") from None
