"""Signup and login.

Ownership rule for the whole application, enforced here and in api/deps.py: every resource
belongs to an **account**, and a user reaches it through their `account_id`. Services filter
on it so no route has to remember a WHERE clause.
"""

import uuid

from sqlmodel import Session, select

from app.models import Account, User, UserRole
from app.services import passwords
from app.services.errors import EmailTaken, InvalidCredentials, UsernameTaken


def normalise_username(username: str) -> str:
    """SQLModel skips validation on `table=True` models and the unique index is
    case-sensitive, so 'Alvin' and 'alvin' would both be accepted as distinct users unless
    something normalises first. That something is this function, and every write path calls
    it."""
    return username.strip().lower()


def normalise_email(email: str | None) -> str | None:
    return email.strip().lower() if email and email.strip() else None


def get_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == normalise_username(username))).first()


def get_by_email(session: Session, email: str) -> User | None:
    normalised = normalise_email(email)
    if not normalised:
        return None
    return session.exec(select(User).where(User.email == normalised)).first()


def signup(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str,
    email: str | None = None,
    account_name: str | None = None,
) -> User:
    """Create an account and its owner together.

    One transaction: an account with no owner is unreachable forever, and a user with no
    account cannot own anything.
    """
    username = normalise_username(username)
    email = normalise_email(email)

    if get_by_username(session, username) is not None:
        raise UsernameTaken(username)
    if email and get_by_email(session, email) is not None:
        raise EmailTaken(email)

    account = Account(name=account_name or f"{display_name}'s account")
    session.add(account)
    session.flush()  # assigns account.id without committing

    owner = User(
        account_id=account.id,
        username=username,
        email=email,
        password_hash=passwords.hash_password(password),
        display_name=display_name,
        role=UserRole.OWNER,
    )
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return owner


def authenticate(session: Session, *, identifier: str, password: str) -> User:
    """Resolve one field to a user, or raise InvalidCredentials.

    The identifier is tried as a username first and as an email second, so the login form
    needs one box. Asking the person which kind of thing they are typing is a question the
    server can answer itself.
    """
    user = get_by_username(session, identifier) or get_by_email(session, identifier)

    if user is None:
        # Spend a verify's worth of CPU anyway; see passwords._DUMMY_HASH.
        passwords.waste_time_like_a_verify()
        raise InvalidCredentials()

    if not passwords.verify_password(user.password_hash, password):
        raise InvalidCredentials()

    # Same error, same 401: a suspended subuser must not be able to tell that they are
    # suspended rather than simply wrong.
    if not user.is_active:
        raise InvalidCredentials()

    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


def accessible_device_ids(session: Session, user: User) -> list[uuid.UUID] | None:
    """Device ids a user may reach, or None meaning 'every device in the account'.

    None rather than an exhaustive list for owners: an owner's reach is defined by the
    account, not by grant rows, so materialising it would invent state that can drift.
    """
    from app.models import DeviceAccess  # local import keeps this module's surface small

    if user.role == UserRole.OWNER:
        return None
    rows = session.exec(
        select(DeviceAccess.device_id).where(DeviceAccess.user_id == user.id)
    ).all()
    return list(rows)
