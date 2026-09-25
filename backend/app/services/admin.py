"""What staff do to accounts from the monitoring app: list them, issue them, set their limits.

Who may do what is one table, `MAY_ISSUE`, keyed by the kind of account the signed-in person
belongs to (models/account.py::AccountKind):

    owner  → issues admin and client accounts, and changes the limits of both
    admin  → issues client accounts, and changes client limits only

An account's end date (`expires_at`) counts as one of its limits: the same table decides who may
set it, so the owner account never has one and a technician cannot extend their own.

Nobody issues a second owner account, and nobody sets limits on the one there is: `owner` is
in nobody's row of the table, and that is the whole rule. Both are checked here, in the
service, so no route can forget.

Every function here takes an explicit `account_id`, never a `user` whose account is implied.
That is the whole difference from the rest of services/: customer code asks "show me my
things", this asks "show me account X's things". Keeping the two apart is what stops a staff
path from ever being reachable through a customer route by accident.

Each write also leaves an `AdminAction` row — who did what, to which account, when.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from app.models import Account, AccountKind, AdminAction, User, UserRole
from app.services import auth as auth_service
from app.services import devices as device_service
from app.services import operations
from app.services.errors import DomainError

#: Which kinds of account each kind of staff may issue — and, the same table, whose limits
#: they may change. A kind absent as a key is not staff at all.
MAY_ISSUE: dict[AccountKind, frozenset[AccountKind]] = {
    AccountKind.OWNER: frozenset({AccountKind.ADMIN, AccountKind.CLIENT}),
    AccountKind.ADMIN: frozenset({AccountKind.CLIENT}),
}

#: What a new admin account gets when the request leaves the limits out.
ADMIN_DEFAULT_MAX_SCREENS = 15
ADMIN_DEFAULT_STORAGE_BYTES = 5 * 1024**3


class AccountNotFound(DomainError):
    pass


class NotAllowed(DomainError):
    """The signed-in staff member may not do this to this kind of account. The message is
    written for the person who tried, and the route shows it as it is."""


@dataclass(frozen=True)
class UserSummary:
    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    # Still on a password staff (or their owner) chose — they haven't signed in to pick theirs.
    must_change_password: bool


@dataclass(frozen=True)
class AccountSummary:
    id: uuid.UUID
    name: str
    kind: AccountKind
    created_at: datetime
    owner_username: str | None
    users: list[UserSummary]
    max_screens: int | None
    screens_used: int
    storage_quota_bytes: int | None
    storage_used_bytes: int
    expires_at: datetime | None
    is_expired: bool


# --- Who is staff, and what they may do ----------------------------------------------------


def kind_of(session: Session, user: User) -> AccountKind:
    account = session.get(Account, user.account_id)
    # A user always has an account (the foreign key says so); the fallback only keeps a
    # half-deleted row from ever reading as staff.
    return account.kind if account is not None else AccountKind.CLIENT


def is_staff(session: Session, user: User) -> bool:
    """May this person use the monitoring app? The main user of an owner or admin account
    that has not expired. A sub account (manager) never may, whatever account it is in.

    An expired admin account loses the monitoring app entirely, not just its buttons: the app
    shows every customer, and a technician whose time is up should not keep seeing them."""
    if user.role != UserRole.OWNER:
        return False
    account = session.get(Account, user.account_id)
    return account is not None and account.kind in MAY_ISSUE and not account.is_expired()


def is_expired_staff(session: Session, user: User) -> bool:
    """The main user of an admin account whose end date has passed — who would be staff but
    for that. Lets the sign-in say why, rather than "wrong password"."""
    account = session.get(Account, user.account_id)
    return (
        user.role == UserRole.OWNER
        and account is not None
        and account.kind in MAY_ISSUE
        and account.is_expired()
    )


def may_issue(session: Session, user: User) -> frozenset[AccountKind]:
    """The kinds this staff member may issue and set limits on. Empty for a non-staff user."""
    return MAY_ISSUE.get(kind_of(session, user), frozenset())


def default_limits(kind: AccountKind) -> tuple[int | None, int | None]:
    """(max_screens, storage_quota_bytes) for a new account of this kind when the request
    says nothing. An admin account starts with the standard allowance; a client is unlimited
    until staff type a number, as before."""
    if kind == AccountKind.ADMIN:
        return ADMIN_DEFAULT_MAX_SCREENS, ADMIN_DEFAULT_STORAGE_BYTES
    return None, None


def _check_may_issue(session: Session, *, admin: User, kind: AccountKind) -> None:
    if kind == AccountKind.OWNER:
        raise NotAllowed("There is only one owner account, and it already exists")
    if kind not in may_issue(session, admin):
        raise NotAllowed(f"An {kind_of(session, admin)} account can only issue client accounts")


def _check_may_limit(session: Session, *, admin: User, account: Account) -> None:
    if account.kind == AccountKind.OWNER:
        raise NotAllowed("The owner account has no limits")
    if account.kind not in may_issue(session, admin):
        raise NotAllowed(
            f"An {kind_of(session, admin)} account can only change a client account's limits"
        )


# --- Reading ------------------------------------------------------------------------------


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
            must_change_password=u.must_change_password,
        )
        for u in rows
    ]


def _summary(session: Session, account: Account) -> AccountSummary:
    users = _users(session, account.id)
    return AccountSummary(
        id=account.id,
        name=account.name,
        kind=account.kind,
        created_at=account.created_at,
        owner_username=next((u.username for u in users if u.role == UserRole.OWNER), None),
        users=users,
        max_screens=account.max_screens,
        screens_used=device_service.count_claimed(session, account_id=account.id),
        storage_quota_bytes=account.storage_quota_bytes,
        storage_used_bytes=operations.storage_used(session, account.id),
        expires_at=account.expires_at,
        is_expired=account.is_expired(),
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


def _end_text(value: datetime | None) -> str:
    return "no end date" if value is None else value.isoformat()


def list_accounts(session: Session) -> list[AccountSummary]:
    """Every account, whoever asks — an admin sees the owner and other admins too, and the
    app simply offers no actions on the ones they may not touch."""
    accounts = session.exec(select(Account).order_by(Account.created_at.desc())).all()
    return [_summary(session, a) for a in accounts]


def get_account(session: Session, *, account_id: uuid.UUID) -> AccountSummary:
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(str(account_id))
    return _summary(session, account)


# --- Writing ------------------------------------------------------------------------------


def create_account(
    session: Session,
    *,
    admin: User,
    kind: AccountKind,
    name: str,
    username: str,
    password: str,
    display_name: str,
    email: str | None,
    max_screens: int | None,
    storage_quota_bytes: int | None,
    expires_at: datetime | None = None,
) -> AccountSummary:
    """The account and its owner come from `auth.signup` — now its only caller, since there is
    no public signup — so there is exactly one way an account gets born. The kind, the limits
    and the log row go on afterwards, in the same session, before anything is committed."""
    _check_may_issue(session, admin=admin, kind=kind)
    owner = auth_service.signup(
        session,
        username=username,
        password=password,
        display_name=display_name,
        email=email,
        account_name=name,
    )
    # Staff typed this password, so it's temporary: the person picks their own at first sign-in.
    owner.must_change_password = True
    session.add(owner)
    account = session.get(Account, owner.account_id)
    account.kind = kind
    account.max_screens = max_screens
    account.storage_quota_bytes = storage_quota_bytes
    account.expires_at = expires_at
    session.add(account)
    _log(
        session,
        admin=admin,
        account=account,
        action="create_account",
        detail=(
            f"{kind} account; owner {owner.username}; screens {_limit_text(max_screens)}; "
            f"storage {_limit_text(storage_quota_bytes)} bytes; ends {_end_text(expires_at)}"
        ),
    )
    session.commit()
    session.refresh(account)
    return _summary(session, account)


def reset_password(
    session: Session, *, admin: User, account_id: uuid.UUID, password: str
) -> AccountSummary:
    """Give the account's main user a new temporary password, for a customer who has forgotten
    theirs. Same rule as the limits — the owner resets admin and client accounts, a technician
    client accounts, nobody the owner account — since whoever may reset a password may take the
    account over. The person picks their own at next sign-in, and every session they had ends.
    The log says it happened and to whom, never what the password was."""
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(str(account_id))
    if account.kind == AccountKind.OWNER:
        raise NotAllowed("The owner account's password can only be changed by signing in to it")
    if account.kind not in may_issue(session, admin):
        raise NotAllowed(
            f"An {kind_of(session, admin)} account can only reset a client account's password"
        )
    main = session.exec(
        select(User)
        .where(User.account_id == account_id, User.role == UserRole.OWNER)
        .order_by(User.created_at)
    ).first()
    if main is None:
        raise AccountNotFound(str(account_id))
    auth_service.set_temporary_password(main, password)
    session.add(main)
    _log(
        session, admin=admin, account=account, action="reset_password",
        detail=f"temporary password for {main.username}; they choose their own at next sign-in",
    )
    session.commit()
    session.refresh(account)
    return _summary(session, account)


def set_limits(
    session: Session,
    *,
    admin: User,
    account_id: uuid.UUID,
    changes: dict[str, int | datetime | None],
) -> AccountSummary:
    """`changes` holds only the limits that were actually sent — a key present with value
    None means "make it unlimited" (or, for `expires_at`, "no end date"), a key absent means
    "leave it". An end date in the past is allowed: it is how staff switch an account off now."""
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(str(account_id))
    _check_may_limit(session, admin=admin, account=account)

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
    if "expires_at" in changes:
        before, after = account.expires_at, changes["expires_at"]
        if before != after:
            account.expires_at = after
            described.append(f"expires_at {_end_text(before)} → {_end_text(after)}")

    if described:
        session.add(account)
        _log(session, admin=admin, account=account, action="set_limits", detail="; ".join(described))
        session.commit()
        session.refresh(account)
    return _summary(session, account)
