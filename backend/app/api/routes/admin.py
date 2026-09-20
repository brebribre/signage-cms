"""Platform admin: issue customer accounts and set their limits.

Every route here takes `RequirePlatformAdmin` and nothing else for authorization. These are
the only routes that reach across accounts, and they live in their own file so that stays
obvious — no customer-facing route is ever widened to "also works for admins".
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequirePlatformAdmin
from app.schemas.admin import AdminAccountCreate, AdminAccountRead, AdminLimitsUpdate
from app.services import admin as admin_service
from app.services.admin import AccountNotFound
from app.services.errors import EmailTaken, UsernameTaken

router = APIRouter(prefix="/admin", tags=["admin"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")


def _read(summary: admin_service.AccountSummary) -> AdminAccountRead:
    return AdminAccountRead(**summary.__dict__)


@router.get("/accounts", response_model=list[AdminAccountRead])
def list_accounts(admin: RequirePlatformAdmin, session: DbSession) -> list[AdminAccountRead]:
    return [_read(s) for s in admin_service.list_accounts(session)]


@router.post("/accounts", response_model=AdminAccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AdminAccountCreate, admin: RequirePlatformAdmin, session: DbSession
) -> AdminAccountRead:
    """Make an account and its first owner. The admin passes the username and password on to
    the customer themselves."""
    try:
        summary = admin_service.create_account(
            session,
            admin=admin,
            name=body.name,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            email=body.email,
            max_screens=body.max_screens,
            storage_quota_bytes=body.storage_quota_bytes,
        )
    except UsernameTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken") from None
    except EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None
    return _read(summary)


@router.get("/accounts/{account_id}", response_model=AdminAccountRead)
def get_account(
    account_id: uuid.UUID, admin: RequirePlatformAdmin, session: DbSession
) -> AdminAccountRead:
    try:
        return _read(admin_service.get_account(session, account_id=account_id))
    except AccountNotFound:
        raise NOT_FOUND from None


@router.patch("/accounts/{account_id}", response_model=AdminAccountRead)
def set_limits(
    account_id: uuid.UUID, body: AdminLimitsUpdate, admin: RequirePlatformAdmin, session: DbSession
) -> AdminAccountRead:
    """Change one or both limits. A field sent as `null` becomes unlimited; a field left out
    is untouched."""
    changes = {k: getattr(body, k) for k in body.model_fields_set}
    try:
        summary = admin_service.set_limits(session, admin=admin, account_id=account_id, changes=changes)
    except AccountNotFound:
        raise NOT_FOUND from None
    return _read(summary)
