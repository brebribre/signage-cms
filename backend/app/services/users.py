"""Subusers and device grants.

Every function here is owner-only — the routes enforce that with `RequireOwner`, and the
guardrails below are the ones that would otherwise let an owner lock themselves out of their
own account.
"""

import uuid

from sqlmodel import Session, delete, func, select

from app.models import Device, DeviceAccess, User, UserRole
from app.services import auth as auth_service
from app.services import passwords
from app.services.errors import DomainError, EmailTaken, UsernameTaken


class UserNotFound(DomainError):
    pass


class CannotActOnSelf(DomainError):
    """An owner deleting or deactivating themselves would leave nobody who can undo it."""


class LastOwner(DomainError):
    """An account with no active owner cannot be administered by anyone, ever again."""


class UnknownDevice(DomainError):
    """Reported as 404, like every other cross-account reference."""


def list_users(session: Session, *, account_id: uuid.UUID) -> list[tuple[User, int]]:
    users = list(
        session.exec(
            select(User).where(User.account_id == account_id).order_by(User.created_at)
        ).all()
    )
    if not users:
        return []
    # One grouped query rather than one per user — the list page shows a count for every row.
    counts = {
        uid: n
        for uid, n in session.exec(
            select(DeviceAccess.user_id, func.count(DeviceAccess.device_id))
            .where(DeviceAccess.user_id.in_([u.id for u in users]))
            .group_by(DeviceAccess.user_id)
        ).all()
    }
    return [(u, counts.get(u.id, 0)) for u in users]


def grants_for(session: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.exec(select(DeviceAccess.device_id).where(DeviceAccess.user_id == user_id)).all()
    )


def get_user(session: Session, *, owner: User, user_id: uuid.UUID) -> User:
    """Public accessor — routes must not reach for the private helper below."""
    return _target(session, owner, user_id)


def _target(session: Session, owner: User, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None or user.account_id != owner.account_id:
        raise UserNotFound(str(user_id))
    return user


def _validate_devices(
    session: Session, *, account_id: uuid.UUID, device_ids: list[uuid.UUID]
) -> None:
    if not device_ids:
        return
    found = session.exec(
        select(Device.id).where(Device.id.in_(device_ids), Device.account_id == account_id)
    ).all()
    missing = set(device_ids) - set(found)
    if missing:
        # 404, not 400: naming a device that exists in another account as "invalid" would
        # confirm it exists. Same rule as DeviceForUser.
        raise UnknownDevice(str(next(iter(missing))))


def _active_owners(session: Session, account_id: uuid.UUID, exclude: uuid.UUID | None = None) -> int:
    statement = select(User).where(
        User.account_id == account_id,
        User.role == UserRole.OWNER,
        User.is_active.is_(True),
    )
    return len([u for u in session.exec(statement).all() if u.id != exclude])


def create_manager(
    session: Session,
    *,
    owner: User,
    username: str,
    password: str,
    display_name: str,
    email: str | None = None,
    device_ids: list[uuid.UUID] | None = None,
) -> User:
    """Create a subuser and its grants in one transaction."""
    username = auth_service.normalise_username(username)
    email = auth_service.normalise_email(email)
    device_ids = device_ids or []

    if auth_service.get_by_username(session, username) is not None:
        raise UsernameTaken(username)
    if email and auth_service.get_by_email(session, email) is not None:
        raise EmailTaken(email)
    _validate_devices(session, account_id=owner.account_id, device_ids=device_ids)

    manager = User(
        account_id=owner.account_id,
        username=username,
        email=email,
        password_hash=passwords.hash_password(password),
        display_name=display_name,
        role=UserRole.MANAGER,
        created_by=owner.id,
    )
    session.add(manager)
    session.flush()
    for device_id in device_ids:
        session.add(DeviceAccess(user_id=manager.id, device_id=device_id))
    session.commit()
    session.refresh(manager)
    return manager


def update_user(
    session: Session,
    *,
    owner: User,
    user_id: uuid.UUID,
    display_name: str | None = None,
    is_active: bool | None = None,
) -> User:
    user = _target(session, owner, user_id)

    if is_active is not None and not is_active:
        if user.id == owner.id:
            raise CannotActOnSelf(str(user_id))
        if user.role == UserRole.OWNER and _active_owners(session, owner.account_id, exclude=user.id) == 0:
            raise LastOwner(str(user_id))

    if display_name is not None:
        user.display_name = display_name.strip()
    if is_active is not None:
        user.is_active = is_active

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_password(session: Session, *, owner: User, user_id: uuid.UUID, password: str) -> None:
    """The owner is the recovery path.

    There is no email reset flow, and that is the point of allowing username-only accounts: a
    subuser may have no address to send one to.
    """
    user = _target(session, owner, user_id)
    user.password_hash = passwords.hash_password(password)
    session.add(user)
    session.commit()


def set_device_grants(
    session: Session, *, owner: User, user_id: uuid.UUID, device_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Replace the whole grant set.

    Same whole-array shape as `PUT /playlists/{id}/items`, for the same reason: the UI is a
    checkbox list that produces a complete set anyway.
    """
    user = _target(session, owner, user_id)
    unique = list(dict.fromkeys(device_ids))
    _validate_devices(session, account_id=owner.account_id, device_ids=unique)

    session.exec(delete(DeviceAccess).where(DeviceAccess.user_id == user.id))
    for device_id in unique:
        session.add(DeviceAccess(user_id=user.id, device_id=device_id))
    session.commit()
    return unique


def delete_user(session: Session, *, owner: User, user_id: uuid.UUID) -> None:
    user = _target(session, owner, user_id)
    if user.id == owner.id:
        raise CannotActOnSelf(str(user_id))
    if user.role == UserRole.OWNER and _active_owners(session, owner.account_id, exclude=user.id) == 0:
        raise LastOwner(str(user_id))

    # Grants cascade. Their media, playlists and devices survive with created_by nulled —
    # that SET NULL is the whole reason resources hang off the account, not the person.
    session.exec(delete(User).where(User.id == user.id))
    session.commit()
