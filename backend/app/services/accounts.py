"""Account-wide settings — what Settings → General edits."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session

from app.models import Account
from app.services.errors import DomainError


class InvalidTimezone(DomainError):
    pass


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def update(session: Session, *, account: Account, default_timezone: str | None = None) -> Account:
    """Only what was sent changes. The default timezone applies to screens paired from now on;
    screens already paired keep their own (see services/devices.py::claim)."""
    if default_timezone is not None:
        if not valid_timezone(default_timezone):
            raise InvalidTimezone(default_timezone)
        account.default_timezone = default_timezone
    session.add(account)
    session.commit()
    session.refresh(account)
    return account
