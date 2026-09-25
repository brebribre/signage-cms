"""Shared FastAPI dependencies.

`CurrentUser`, `RequireOwner` and `DeviceForUser` are the whole authorization model. Every
protected route takes one of them, and every service query filters by `account_id`.
"""

import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.config import get_settings
from app.infra.db import session_scope
from app.models import Account, Device, DeviceAccess, User, UserRole
from app.services import admin as admin_service
from app.services import devices as device_service
from app.services.session import read_session_token


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()


DbSession = Annotated[Session, Depends(get_db)]


#: What an expired account may still send besides reading. Asking a screen to check in changes
#: nothing it shows; it only refreshes the status on the screen's page.
EXPIRED_MAY_STILL = frozenset({("POST", "/devices/{device_id}/probe")})

#: Read-only methods. An expired account keeps all of these.
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

ACCOUNT_EXPIRED = (
    "This account has expired, so changes are switched off. Your screens keep showing what "
    "they have now. Contact Paskall to renew it."
)


#: All a person with a temporary password may do: learn that they must change it, change it,
#: and sign out (which needs no session at all).
OWN_PASSWORD_FIRST_MAY = frozenset({("GET", "/me"), ("POST", "/auth/password")})

OWN_PASSWORD_REQUIRED = "Choose your own password before continuing."


def _refuse_until_own_password(request: Request, user: User) -> None:
    """Someone else chose this password — staff issuing or resetting the account, or an owner
    making a sub account — so nothing else is allowed until the person picks their own. Checked
    here, where every signed-in request passes, so no route can forget it: whoever handed the
    password over can't use it to do anything but choose a new one, which they'd then know
    and the owner would find they didn't."""
    if not user.must_change_password:
        return
    route = request.scope.get("route")
    if (request.method, getattr(route, "path", None)) in OWN_PASSWORD_FIRST_MAY:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=OWN_PASSWORD_REQUIRED)


def _refuse_if_expired(request: Request, session: Session, user: User) -> None:
    """An expired account is read-only. Checked here, where every signed-in request passes, so
    no route can forget it and a new route is covered the day it is written.

    Read-only means: sign in, look at everything, sign out. Anything that would change what a
    screen shows, add a screen, upload, or change who is in the account is refused. The screens
    themselves never pass through here (they use `CurrentDevice`), so they keep playing.
    """
    if request.method in READ_METHODS:
        return
    account = session.get(Account, user.account_id)
    if account is None or not account.is_expired():
        return
    route = request.scope.get("route")
    if (request.method, getattr(route, "path", None)) in EXPIRED_MAY_STILL:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_EXPIRED)


def get_current_user(request: Request, session: DbSession) -> User:
    """Resolve the signed-in user from the session cookie, or 401.

    Role and active status are read here, per request, rather than carried in the token —
    so deactivating a subuser takes effect on their *next call*, not on their next login.
    The same goes for an account's end date: once it passes, the next change is refused.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )

    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthorized

    read = read_session_token(token)
    if read is None:
        raise unauthorized
    user_id, version = read

    user = session.get(User, user_id)
    if user is None:
        # Validly signed cookie for a user that no longer exists.
        raise unauthorized
    if not user.is_active:
        raise unauthorized
    # A cookie from before the password last changed — someone else's copy, or the session a
    # temporary password was used in. See services/session.py.
    if version != user.session_version:
        raise unauthorized
    _refuse_until_own_password(request, user)
    _refuse_if_expired(request, session, user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_owner(user: CurrentUser) -> User:
    """User management only. Everything else a manager may do too."""
    if user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required"
        )
    return user


RequireOwner = Annotated[User, Depends(require_owner)]


def require_staff(user: CurrentUser, session: DbSession) -> User:
    """Paskall staff only — the /admin/* routes, which reach across every account.

    Staff means the main user of an owner or admin account (services/admin.py::is_staff). This
    is the one place the "you only ever see your own account" rule is set aside, so it is its
    own dependency rather than a widening of `require_owner`: nothing a customer can call ever
    passes through here. What a given member of staff may *do* is decided per call, from their
    account's kind, inside services/admin.py.
    """
    if not admin_service.is_staff(session, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return user


RequireStaff = Annotated[User, Depends(require_staff)]


def device_for_user(device_id: uuid.UUID, user: CurrentUser, session: DbSession) -> Device:
    """Resolve a device this user may act on, or 404.

    **404, never 403**, for a device the user was not granted — including one that plainly
    exists in another account. A manager should not be able to probe which screens exist
    outside their scope, and "you may not see this" and "this does not exist" must look
    identical from outside.
    """
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screen not found")

    device = session.get(Device, device_id)
    if device is None or device.account_id is None:
        raise not_found
    if device.account_id != user.account_id:
        raise not_found

    # Owners reach every device in their account without a grant row; only managers are
    # scoped, so there is no grant an owner can forget to give themselves.
    if user.role == UserRole.MANAGER:
        if session.get(DeviceAccess, (user.id, device_id)) is None:
            raise not_found

    return device


DeviceForUser = Annotated[Device, Depends(device_for_user)]


def get_current_device(request: Request, session: DbSession) -> Device:
    """Resolve a screen from its `Authorization: Bearer <token>` header, or 401.

    **Device auth and user auth never overlap.** A device token cannot call `/media`, and a
    session cookie cannot call `/device/manifest` — they are separate dependencies reading
    separate credentials, so there is no path by which one is mistaken for the other.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid device token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized

    try:
        device = device_service.authenticate(session, bearer=token)
    except device_service.DeviceNotFound:
        raise unauthorized from None

    # Disconnected from the CMS: say so once, unmistakably, and finish the job as the answer
    # goes out. 410 rather than 401 because a 401 can be a transient fault the screen is right
    # to ride out — this cannot be. The screen resets itself on this answer; the CMS, polling
    # for the row, sees a 404 and knows the screen has heard. See Device.disconnect_requested_at.
    if device.disconnect_requested_at is not None:
        device_service.remove(session, device=device)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This screen was disconnected from the CMS. Pair it again to reconnect.",
        )
    return device


CurrentDevice = Annotated[Device, Depends(get_current_device)]
