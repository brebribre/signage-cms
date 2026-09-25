import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import AccountKind, UserRole

# Used by schemas/admin.py's AdminAccountCreate — the one place a username is chosen, now that
# there is no public signup. Checked there as well as in the service: the schema is the
# earliest place a bad value can be refused, and the service is the place nothing can bypass.
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


class LoginRequest(BaseModel):
    # One field, not two. The server resolves it as a username or an email.
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class AccountRead(BaseModel):
    id: uuid.UUID
    name: str
    # owner / admin / client — see models/account.py::AccountKind. Display only here; the
    # monitoring app's routes check it again on every call.
    kind: AccountKind
    default_timezone: str
    # When the account stops accepting changes; None means never. Set by Paskall, never here.
    expires_at: datetime | None = None
    # Worked out on the server, so a wrong clock on the customer's computer cannot hide or
    # invent the "expired" notice. See models/account.py::Account.is_expired.
    is_expired: bool = False


class AccountUpdate(BaseModel):
    """Account-wide settings (Settings → General). Owner-only."""

    # IANA name. Checked against the tz database in the service, so a typo is a 422 rather than
    # every new screen quietly running on UTC.
    default_timezone: str | None = Field(default=None, min_length=1, max_length=64)


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class MeResponse(BaseModel):
    user: UserRead
    account: AccountRead
    # None means "every device in the account" — an owner's reach comes from the account,
    # not from grant rows. A manager gets the explicit list so the UI can hide what it must
    # not offer; the server enforces it regardless.
    device_ids: list[uuid.UUID] | None
