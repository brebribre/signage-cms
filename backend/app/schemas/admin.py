"""Shapes for /admin/* — what a platform admin sees and sends. Never served to customers."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole
from app.schemas.auth import USERNAME_RE


class AdminAccountUserRead(BaseModel):
    """One person who can sign in to the account: the owner, or a sub account (manager) the
    owner created. No email or grants — the admin needs to see who is there, not manage them."""

    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class AdminAccountRead(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    # The first owner's username — what the admin tells the customer to sign in with. None only
    # for an account somehow left with no owner.
    owner_username: str | None
    # Everyone in the account, owners first, so sub accounts sit under the owner in the list.
    users: list[AdminAccountUserRead]
    # Both limits: None means unlimited.
    max_screens: int | None
    screens_used: int
    storage_quota_bytes: int | None
    storage_used_bytes: int


class AdminAccountCreate(BaseModel):
    """An account and its first owner, made together. The admin hands the customer the
    username and password themselves — there is no invite email."""

    name: str = Field(min_length=1, max_length=100)
    username: str
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    # None = unlimited. Zero is legal (an account that may pair nothing yet).
    max_screens: int | None = Field(default=None, ge=0)
    storage_quota_bytes: int | None = Field(default=None, ge=0)

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


class AdminLimitsUpdate(BaseModel):
    """Only the fields sent change. Sending a field as `null` sets it to unlimited; leaving it
    out leaves it alone — the route tells the two apart with `model_fields_set`."""

    max_screens: int | None = Field(default=None, ge=0)
    storage_quota_bytes: int | None = Field(default=None, ge=0)
