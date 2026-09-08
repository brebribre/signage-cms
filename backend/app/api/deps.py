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
from app.models import Device, DeviceAccess, User, UserRole
from app.services.session import read_session_token


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, session: DbSession) -> User:
    """Resolve the signed-in user from the session cookie, or 401.

    Role and active status are read here, per request, rather than carried in the token —
    so deactivating a subuser takes effect on their *next call*, not on their next login.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )

    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthorized

    user_id = read_session_token(token)
    if user_id is None:
        raise unauthorized

    user = session.get(User, user_id)
    if user is None:
        # Validly signed cookie for a user that no longer exists.
        raise unauthorized
    if not user.is_active:
        raise unauthorized
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


def device_for_user(device_id: uuid.UUID, user: CurrentUser, session: DbSession) -> Device:
    """Resolve a device this user may act on, or 404.

    **404, never 403**, for a device the user was not granted — including one that plainly
    exists in another account. A manager should not be able to probe which screens exist
    outside their scope, and "you may not see this" and "this does not exist" must look
    identical from outside.
    """
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

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
