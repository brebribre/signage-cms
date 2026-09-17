"""The signed-in user's account: its settings. Reading comes with GET /me."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequireOwner
from app.models import Account
from app.schemas.auth import AccountRead, AccountUpdate
from app.services import accounts as account_service

router = APIRouter(tags=["auth"])


@router.patch("/account", response_model=AccountRead)
def update_account(body: AccountUpdate, user: RequireOwner, session: DbSession) -> AccountRead:
    """Account-wide settings. Owner-only, like the rest of Settings."""
    account = session.get(Account, user.account_id)
    try:
        account = account_service.update(session, account=account, default_timezone=body.default_timezone)
    except account_service.InvalidTimezone as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown timezone: {exc}") from None
    return AccountRead.model_validate(account, from_attributes=True)
