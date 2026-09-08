import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


class SignupRequest(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    account_name: str | None = Field(default=None, max_length=100)

    @field_validator("username")
    @classmethod
    def _valid_username(cls, value: str) -> str:
        # Lowercased here as well as in the service: the schema is the earliest place a bad
        # value can be refused, and the service is the place nothing can bypass.
        value = value.strip().lower()
        if not USERNAME_RE.match(value):
            raise ValueError(
                "3-32 characters, starting with a letter or digit; "
                "letters, digits, dot, underscore and hyphen only"
            )
        return value


class LoginRequest(BaseModel):
    # One field, not two. The server resolves it as a username or an email.
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class AccountRead(BaseModel):
    id: uuid.UUID
    name: str


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
