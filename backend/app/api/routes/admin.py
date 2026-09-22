"""The monitoring app's routes: its sign-in, and issuing accounts and their limits.

Every route here takes `RequireStaff` (or, for sign-in itself, refuses anyone who isn't staff)
and nothing else for authorization; what a given member of staff may do to a given account is
then decided inside services/admin.py from their account's kind. These are the only routes
that reach across accounts, and they live in their own file so that stays obvious — no
customer-facing route is ever widened to "also works for staff". The monitoring frontend calls
nothing outside `/admin/*`.
"""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.auth_common import UNAUTHORIZED, clear_session_cookie, set_session_cookie
from app.api.deps import DbSession, RequireStaff
from app.models import User
from app.schemas.admin import (
    AdminAccountCreate,
    AdminAccountRead,
    AdminAccountUserRead,
    AdminLimitsUpdate,
    StaffRead,
)
from app.schemas.auth import LoginRequest
from app.services import admin as admin_service
from app.services import auth as auth_service
from app.services.admin import AccountNotFound, NotAllowed
from app.services.errors import EmailTaken, InvalidCredentials, UsernameTaken

router = APIRouter(prefix="/admin", tags=["admin"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")


def _staff(session, user: User) -> StaffRead:
    return StaffRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        kind=admin_service.kind_of(session, user),
    )


# --- Sign-in for the monitoring app --------------------------------------------------------


@router.post("/auth/login", response_model=StaffRead)
def admin_login(body: LoginRequest, response: Response, session: DbSession) -> StaffRead:
    """Same username and password as the CMS, but only staff get in — the main user of an
    owner or admin account.

    A customer who tries gets the *same* 401 as a wrong password — same status, same body —
    so trying tells them nothing, not even that a staff sign-in exists.
    """
    try:
        user = auth_service.authenticate(
            session, identifier=body.identifier, password=body.password
        )
    except InvalidCredentials:
        raise UNAUTHORIZED from None
    if not admin_service.is_staff(session, user):
        raise UNAUTHORIZED
    set_session_cookie(response, user.id)
    return _staff(session, user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def admin_logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=StaffRead)
def admin_me(staff: RequireStaff, session: DbSession) -> StaffRead:
    """Who is signed in to the monitoring app, and their kind. 403 for a customer's session,
    401 for none."""
    return _staff(session, staff)


# --- Accounts ------------------------------------------------------------------------------


def _read(summary: admin_service.AccountSummary) -> AdminAccountRead:
    return AdminAccountRead(
        **{**summary.__dict__, "users": [AdminAccountUserRead(**u.__dict__) for u in summary.users]}
    )


@router.get("/accounts", response_model=list[AdminAccountRead])
def list_accounts(staff: RequireStaff, session: DbSession) -> list[AdminAccountRead]:
    return [_read(s) for s in admin_service.list_accounts(session)]


@router.post("/accounts", response_model=AdminAccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AdminAccountCreate, staff: RequireStaff, session: DbSession
) -> AdminAccountRead:
    """Make an account and its first owner. Staff pass the username and password on to the
    person themselves. A limit left out of the request gets the kind's default — 15 screens
    and 5 GB for an admin account, no limit for a client — while one sent as null is
    explicitly unlimited."""
    max_screens, storage_quota_bytes = admin_service.default_limits(body.kind)
    if "max_screens" in body.model_fields_set:
        max_screens = body.max_screens
    if "storage_quota_bytes" in body.model_fields_set:
        storage_quota_bytes = body.storage_quota_bytes
    try:
        summary = admin_service.create_account(
            session,
            admin=staff,
            kind=body.kind,
            name=body.name,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            email=body.email,
            max_screens=max_screens,
            storage_quota_bytes=storage_quota_bytes,
        )
    except NotAllowed as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from None
    except UsernameTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken") from None
    except EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None
    return _read(summary)


@router.get("/accounts/{account_id}", response_model=AdminAccountRead)
def get_account(
    account_id: uuid.UUID, staff: RequireStaff, session: DbSession
) -> AdminAccountRead:
    try:
        return _read(admin_service.get_account(session, account_id=account_id))
    except AccountNotFound:
        raise NOT_FOUND from None


@router.patch("/accounts/{account_id}", response_model=AdminAccountRead)
def set_limits(
    account_id: uuid.UUID, body: AdminLimitsUpdate, staff: RequireStaff, session: DbSession
) -> AdminAccountRead:
    """Change one or both limits. A field sent as `null` becomes unlimited; a field left out
    is untouched. 403 when this member of staff may not touch this kind of account."""
    changes = {k: getattr(body, k) for k in body.model_fields_set}
    try:
        summary = admin_service.set_limits(session, admin=staff, account_id=account_id, changes=changes)
    except AccountNotFound:
        raise NOT_FOUND from None
    except NotAllowed as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from None
    return _read(summary)
