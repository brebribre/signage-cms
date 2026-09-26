"""Shapes for /admin/* — what the monitoring app sees and sends. Never served to customers."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import AccountKind, UserRole
from app.schemas.auth import USERNAME_RE


def _aware(value: datetime | None) -> datetime | None:
    """A time with no offset is read as UTC. The monitoring app always sends one; this only
    keeps a hand-written request from landing hours away from what was meant, silently."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class StaffRead(BaseModel):
    """Who is signed in to the monitoring app. `kind` is their account's kind — owner or
    admin, never client — and is what the app uses to offer only what they may do. The server
    checks again on every call regardless."""

    id: uuid.UUID
    username: str
    display_name: str
    kind: AccountKind


class AdminAccountUserRead(BaseModel):
    """One person who can sign in to the account: its main user (owner), or a sub account
    (manager) they created. No email or grants — staff need to see who is there, not manage
    them."""

    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    # Still on a password someone else chose; they haven't signed in to pick their own yet.
    must_change_password: bool = False


class AdminAccountRead(BaseModel):
    id: uuid.UUID
    name: str
    kind: AccountKind
    created_at: datetime
    # The first owner's username — what staff tell the customer to sign in with. None only
    # for an account somehow left with no owner.
    owner_username: str | None
    # Everyone in the account, owners first, so sub accounts sit under the owner in the list.
    users: list[AdminAccountUserRead]
    # Both limits: None means unlimited.
    max_screens: int | None
    screens_used: int
    storage_quota_bytes: int | None
    storage_used_bytes: int
    # When the account stops working; None means never. `is_expired` is worked out here on the
    # server, so a staff laptop with the wrong clock cannot mislabel an account.
    expires_at: datetime | None
    is_expired: bool


class AdminAccountCreate(BaseModel):
    """An account and its first owner, made together. Staff hand the person their username and
    password themselves — there is no invite email."""

    name: str = Field(min_length=1, max_length=100)
    # What sort of account. Who may issue which kind is services/admin.py::MAY_ISSUE; nobody
    # issues an owner account.
    kind: AccountKind = AccountKind.CLIENT
    username: str
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    # None = unlimited. Zero is legal (an account that may pair nothing yet). Left out entirely,
    # an admin account gets the standard 15 screens and 5 GB — the route tells "left out" from
    # "sent as null" with `model_fields_set`.
    max_screens: int | None = Field(default=None, ge=0)
    storage_quota_bytes: int | None = Field(default=None, ge=0)
    # None = no end date, for every kind. See models/account.py::Account.expires_at.
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def _aware_expiry(cls, value: datetime | None) -> datetime | None:
        return _aware(value)

    @field_validator("username")
    @classmethod
    def _valid_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not USERNAME_RE.match(value):
            raise ValueError(
                "3-32 characters, starting with a letter or digit; "
                "letters, digits, dot, underscore and hyphen only"
            )
        return value


class AdminPasswordReset(BaseModel):
    """A temporary password for the account's main user. Staff hand it over themselves; the
    person replaces it at their next sign-in."""

    password: str = Field(min_length=8, max_length=200)


class AdminLimitsUpdate(BaseModel):
    """Only the fields sent change. Sending a field as `null` sets it to unlimited (or, for the
    end date, to none); leaving it out leaves it alone — the route tells the two apart with
    `model_fields_set`."""

    max_screens: int | None = Field(default=None, ge=0)
    storage_quota_bytes: int | None = Field(default=None, ge=0)
    # `null` = no end date. A moment already past switches the account to read-only at once.
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def _aware_expiry(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


# --- Infrastructure -------------------------------------------------------------------------


class StoragePartRead(BaseModel):
    key: str
    label: str
    bytes: int
    # None when the bucket could not be walked and the figure came from the database.
    objects: int | None


class AccountStorageRead(BaseModel):
    id: uuid.UUID
    name: str
    bytes: int


class MonthStorageRead(BaseModel):
    month: str  # "2026-09"
    bytes: int


class StorageReportRead(BaseModel):
    """How full the R2 bucket is. `limit_bytes` is our own upgrade line (settings
    `r2_storage_limit_gb`), not a ceiling R2 enforces."""

    limit_bytes: int
    used_bytes: int
    source: str  # "bucket" | "database"
    object_count: int | None
    measured_at: datetime
    parts: list[StoragePartRead]
    added_30d_bytes: int
    monthly: list[MonthStorageRead]
    top_accounts: list[AccountStorageRead]
    bucket_error: str | None = None


class UserReportRead(BaseModel):
    total: int
    active: int
    main_users: int
    sub_accounts: int
    new_30d: int
    accounts: int
    client_accounts: int


class ScreenReportRead(BaseModel):
    paired: int
    online: int
    android: int
    web: int
    new_30d: int


class InfrastructureRead(BaseModel):
    storage: StorageReportRead
    users: UserReportRead
    screens: ScreenReportRead
    generated_at: datetime
