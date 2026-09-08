import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequireOwner
from app.models import User
from app.schemas.users import (
    AccountUserRead,
    DeviceGrants,
    ManagerCreate,
    PasswordSet,
    UserUpdate,
)
from app.services import users as user_service
from app.services.errors import EmailTaken, UsernameTaken
from app.services.users import CannotActOnSelf, LastOwner, UnknownDevice, UserNotFound

router = APIRouter(tags=["users"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "User not found")


def _read(session, user: User, device_count: int | None = None) -> AccountUserRead:
    ids = user_service.grants_for(session, user.id)
    return AccountUserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        device_count=device_count if device_count is not None else len(ids),
        device_ids=ids,
    )


@router.get("/users", response_model=list[AccountUserRead])
def list_users(owner: RequireOwner, session: DbSession) -> list[AccountUserRead]:
    return [
        _read(session, u, count)
        for u, count in user_service.list_users(session, account_id=owner.account_id)
    ]


@router.post("/users", response_model=AccountUserRead, status_code=status.HTTP_201_CREATED)
def create_user(body: ManagerCreate, owner: RequireOwner, session: DbSession) -> AccountUserRead:
    try:
        manager = user_service.create_manager(
            session,
            owner=owner,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            email=body.email,
            device_ids=body.device_ids,
        )
    except UsernameTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken") from None
    except EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None
    except UnknownDevice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found") from None
    return _read(session, manager)


@router.patch("/users/{user_id}", response_model=AccountUserRead)
def update_user(
    user_id: uuid.UUID, body: UserUpdate, owner: RequireOwner, session: DbSession
) -> AccountUserRead:
    try:
        user = user_service.update_user(
            session,
            owner=owner,
            user_id=user_id,
            display_name=body.display_name,
            is_active=body.is_active,
        )
    except UserNotFound:
        raise NOT_FOUND from None
    except CannotActOnSelf:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You cannot deactivate your own account"
        ) from None
    except LastOwner:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account must keep at least one active owner"
        ) from None
    return _read(session, user)


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(
    user_id: uuid.UUID, body: PasswordSet, owner: RequireOwner, session: DbSession
) -> None:
    """The owner sets a subuser's password directly — there is no email reset flow."""
    try:
        user_service.set_password(session, owner=owner, user_id=user_id, password=body.password)
    except UserNotFound:
        raise NOT_FOUND from None


@router.put("/users/{user_id}/devices", response_model=AccountUserRead)
def set_grants(
    user_id: uuid.UUID, body: DeviceGrants, owner: RequireOwner, session: DbSession
) -> AccountUserRead:
    try:
        user_service.set_device_grants(
            session, owner=owner, user_id=user_id, device_ids=body.device_ids
        )
        user = user_service.get_user(session, owner=owner, user_id=user_id)
    except UserNotFound:
        raise NOT_FOUND from None
    except UnknownDevice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found") from None
    return _read(session, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, owner: RequireOwner, session: DbSession) -> None:
    try:
        user_service.delete_user(session, owner=owner, user_id=user_id)
    except UserNotFound:
        raise NOT_FOUND from None
    except CannotActOnSelf:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You cannot delete your own account"
        ) from None
    except LastOwner:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account must keep at least one active owner"
        ) from None
