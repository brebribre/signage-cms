"""Platform admin: the monitoring app's sign-in, and issuing customer accounts and their limits.

Every route here takes `RequirePlatformAdmin` (or, for sign-in itself, refuses anyone who
isn't one) and nothing else for authorization. These are the only routes that reach across
accounts, and they live in their own file so that stays obvious — no customer-facing route
is ever widened to "also works for admins". The monitoring frontend calls nothing outside
`/admin/*`.
"""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.auth_common import UNAUTHORIZED, clear_session_cookie, set_session_cookie
from app.api.deps import DbSession, RequirePlatformAdmin
from app.schemas.admin import (
    AdminAccountCreate,
    AdminAccountRead,
    AdminAccountUserRead,
    AdminLimitsUpdate,
)
from app.schemas.auth import LoginRequest, UserRead
from app.services import admin as admin_service
from app.services import auth as auth_service
from app.services.admin import AccountNotFound
from app.services.errors import EmailTaken, InvalidCredentials, UsernameTaken

router = APIRouter(prefix="/admin", tags=["admin"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")


# --- Sign-in for the monitoring app --------------------------------------------------------


@router.post("/auth/login", response_model=UserRead)
def admin_login(body: LoginRequest, response: Response, session: DbSession) -> UserRead:
    """Same username and password as the CMS, but only a platform admin gets in.

    A customer who tries gets the *same* 401 as a wrong password — same status, same body —
    so trying tells them nothing, not even that an admin sign-in exists.
    """
    try:
        user = auth_service.authenticate(
            session, identifier=body.identifier, password=body.password
        )
    except InvalidCredentials:
        raise UNAUTHORIZED from None
    if not user.is_platform_admin:
        raise UNAUTHORIZED
    set_session_cookie(response, user.id)
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def admin_logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=UserRead)
def admin_me(admin: RequirePlatformAdmin) -> UserRead:
    """Who is signed in to the monitoring app. 403 for a customer's session, 401 for none."""
    return UserRead.model_validate(admin, from_attributes=True)


# --- Customer accounts ---------------------------------------------------------------------


def _read(summary: admin_service.AccountSummary) -> AdminAccountRead:
    return AdminAccountRead(
        **{**summary.__dict__, "users": [AdminAccountUserRead(**u.__dict__) for u in summary.users]}
    )


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
