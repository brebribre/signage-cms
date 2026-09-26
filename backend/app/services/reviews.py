"""Content reviews: storage and state. Applying an approved review lives in the routes layer
(api/routes/reviews.py), because approval is a replay of the original request.

The rule in one line: **a manager's save that would change a screen waits for the owner.**
Everything that does not reach a screen — uploads, a playlist nobody plays, a rename — applies
at once, as before. See ACCOUNTS.md.
"""

import uuid
from typing import Any

from sqlmodel import Session, func, select

from app.models import ContentReview, ReviewKind, ReviewStatus, User, UserRole
from app.models.base import utcnow
from app.services.errors import DomainError

#: How many decided reviews the list keeps showing, newest first. Pending ones always show.
HISTORY_LIMIT = 100


class ReviewNotFound(DomainError):
    pass


class NotPending(DomainError):
    """Approve, reject and withdraw only make sense once."""


def needs_review(user: User) -> bool:
    """Whether this user's screen-changing saves go through the owner. Managers only —
    owners publish directly. The one knob for "who is reviewed"."""
    return user.role == UserRole.MANAGER


def submit(
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
    screen_specs: list[dict[str, Any]] | None = None,
    before: dict[str, Any] | None = None,
) -> ContentReview:
    review = ContentReview(
        account_id=user.account_id,
        requested_by=user.id,
        requested_by_name=user.display_name,
        kind=kind,
        target_id=target_id,
        target_name=target_name,
        summary=summary,
        screens=screens,
        screen_specs=screen_specs or [],
        before=before,
        playlists=playlists or [],
        payload=payload,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def list_for(session: Session, *, user: User) -> list[ContentReview]:
    """The owner sees the account's reviews; a manager sees only what they sent. Pending
    first, oldest pending at the top (the queue), then decided ones newest first."""
    base = select(ContentReview).where(ContentReview.account_id == user.account_id)
    if user.role != UserRole.OWNER:
        base = base.where(ContentReview.requested_by == user.id)
    pending = session.exec(
        base.where(ContentReview.status == ReviewStatus.PENDING).order_by(ContentReview.created_at)
    ).all()
    decided = session.exec(
        base.where(ContentReview.status != ReviewStatus.PENDING)
        .order_by(ContentReview.created_at.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    return list(pending) + list(decided)


def pending_count(session: Session, *, user: User) -> int:
    statement = select(func.count(ContentReview.id)).where(
        ContentReview.account_id == user.account_id,
        ContentReview.status == ReviewStatus.PENDING,
    )
    if user.role != UserRole.OWNER:
        statement = statement.where(ContentReview.requested_by == user.id)
    return int(session.exec(statement).one())


def get(session: Session, *, user: User, review_id: uuid.UUID) -> ContentReview:
    review = session.get(ContentReview, review_id)
    if review is None or review.account_id != user.account_id:
        raise ReviewNotFound(str(review_id))
    if user.role != UserRole.OWNER and review.requested_by != user.id:
        raise ReviewNotFound(str(review_id))
    return review


def _decide(session: Session, review: ContentReview, *, by: User, status: ReviewStatus, note: str | None) -> ContentReview:
    if review.status != ReviewStatus.PENDING:
        raise NotPending(review.status)
    review.status = status
    review.note = (note or "").strip() or None
    review.reviewed_by = by.id
    review.reviewed_at = utcnow()
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def mark_approved(session: Session, *, owner: User, review: ContentReview, note: str | None = None) -> ContentReview:
    """Record the approval. The caller has already applied the change — this is never called
    when applying failed, so a review that could not be applied stays pending with the reason
    shown, rather than being marked approved for a change that did not happen."""
    return _decide(session, review, by=owner, status=ReviewStatus.APPROVED, note=note)


def reject(session: Session, *, owner: User, review: ContentReview, note: str | None) -> ContentReview:
    return _decide(session, review, by=owner, status=ReviewStatus.REJECTED, note=note)


def withdraw(session: Session, *, user: User, review: ContentReview) -> ContentReview:
    """A manager taking back their own request before it is decided."""
    return _decide(session, review, by=user, status=ReviewStatus.WITHDRAWN, note=None)


def requester(session: Session, review: ContentReview) -> User | None:
    """The manager to replay the change as — None once they are gone or deactivated, in
    which case the review can only be rejected."""
    if review.requested_by is None:
        return None
    user = session.get(User, review.requested_by)
    if user is None or not user.is_active or user.account_id != review.account_id:
        return None
    return user
