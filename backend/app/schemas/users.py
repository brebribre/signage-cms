import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole
from app.schemas.auth import USERNAME_RE


class ManagerCreate(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    device_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def _valid(cls, value: str) -> str:
        value = value.strip().lower()
        if not USERNAME_RE.match(value):
            raise ValueError(
                "3-32 characters, starting with a letter or digit; "
                "letters, digits, dot, underscore and hyphen only"
            )
        return value


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class PasswordSet(BaseModel):
    password: str = Field(min_length=8, max_length=200)


class DeviceGrants(BaseModel):
    """The whole grant set, replaced."""

    device_ids: list[uuid.UUID] = Field(default_factory=list)


class AccountUserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    device_count: int
    device_ids: list[uuid.UUID]
