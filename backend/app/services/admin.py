"""What a platform admin does to customer accounts: list them, make them, set their limits.

Every function here takes an explicit `account_id`, never a `user` whose account is implied.
That is the whole difference from the rest of services/: customer code asks "show me my
things", this asks "show me account X's things". Keeping the two apart is what stops an admin
path from ever being reachable through a customer route by accident.

Each write also leaves an `AdminAction` row — who did what, to which account, when.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from app.models import Account, AdminAction, User, UserRole
from app.services import auth as auth_service
from app.services import devices as device_service
from app.services import operations
from app.services.errors import DomainError


class AccountNotFound(DomainError):
    pass


@dataclass(frozen=True)
class UserSummary:
    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    is_platform_admin: bool = False


@dataclass(frozen=True)
class AccountSummary:
    id: uuid.UUID
    name: str
    created_at: datetime
    owner_username: str | None
    users: list[UserSummary]
    max_screens: int | None
    screens_used: int
    storage_quota_bytes: int | None
    storage_used_bytes: int


def _users(session: Session, account_id: uuid.UUID) -> list[UserSummary]:
    """Everyone in the account. Owners first, then the sub accounts they made, each group
    oldest first — so the list reads as "the owner, and under them, who they added"."""
    rows = list(
        session.exec(select(User).where(User.account_id == account_id).order_by(User.created_at)).all()
    )
    rows.sort(key=lambda u: (u.role != UserRole.OWNER, u.created_at))
    return [
        UserSummary(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            is_platform_admin=u.is_platform_admin,
        )
        for u in rows
    ]


def _summary(session: Session, account: Account) -> AccountSummary:
    users = _users(session, account.id)
    return AccountSummary(
        id=account.id,
        name=account.name,
        created_at=account.created_at,
        owner_username=next((u.username for u in users if u.role == UserRole.OWNER), None),
        users=users,
        max_screens=account.max_screens,
        screens_used=device_service.count_claimed(session, account_id=account.id),
        storage_quota_bytes=account.storage_quota_bytes,
        storage_used_bytes=operations.storage_used(session, account.id),
    )


def _log(session: Session, *, admin: User, account: Account, action: str, detail: str) -> None:
    session.add(
        AdminAction(
            admin_user_id=admin.id,
            account_id=account.id,
            account_name=account.name,
            action=action,
            detail=detail,
        )
    )


def _limit_text(value: int | None) -> str:
    return "unlimited" if value is None else str(value)


def list_accounts(session: Session) -> list[AccountSummary]:
    accounts = session.exec(select(Account).order_by(Account.created_at.desc())).all()
    return [_summary(session, a) for a in accounts]


def get_account(session: Session, *, account_id: uuid.UUID) -> AccountSummary:
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(str(account_id))
    return _summary(session, account)


def create_account(
    session: Session,
    *,
    admin: User,
    name: str,
    username: str,
    password: str,
    display_name: str,
    email: str | None,
    max_screens: int | None,
    storage_quota_bytes: int | None,
) -> AccountSummary:
    """The account and its owner come from `auth.signup` — now its only caller, since there is
    no public signup — so there is exactly one way an account gets born. The limits and the
    log row go on afterwards, in the same session, before anything is committed."""
    owner = auth_service.signup(
        session,
        username=username,
        password=password,
        display_name=display_name,
        email=email,
        account_name=name,
    )
    account = session.get(Account, owner.account_id)
    account.max_screens = max_screens
    account.storage_quota_bytes = storage_quota_bytes
    session.add(account)
    _log(
        session,
        admin=admin,
        account=account,
        action="create_account",
        detail=(
            f"owner {owner.username}; screens {_limit_text(max_screens)}; "
            f"storage {_limit_text(storage_quota_bytes)} bytes"
        ),
    )
    session.commit()
    session.refresh(account)
    return _summary(session, account)


def set_limits(
    session: Session, *, admin: User, account_id: uuid.UUID, changes: dict[str, int | None]
) -> AccountSummary:
    """`changes` holds only the limits that were actually sent — a key present with value
    None means "make it unlimited", a key absent means "leave it"."""
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(str(account_id))

    described: list[str] = []
    if "max_screens" in changes:
        before, after = account.max_screens, changes["max_screens"]
        if before != after:
            account.max_screens = after
            described.append(f"max_screens {_limit_text(before)} → {_limit_text(after)}")
    if "storage_quota_bytes" in changes:
        before, after = account.storage_quota_bytes, changes["storage_quota_bytes"]
        if before != after:
            account.storage_quota_bytes = after
            described.append(f"storage_quota_bytes {_limit_text(before)} → {_limit_text(after)}")

    if described:
        session.add(account)
        _log(session, admin=admin, account=account, action="set_limits", detail="; ".join(described))
        session.commit()
        session.refresh(account)
    return _summary(session, account)
