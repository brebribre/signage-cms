import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class UserRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"


class User(SQLModel, table=True):
    """A person who signs in. Exactly one owner per account at minimum; managers are subusers.

    Roles go through `enum_column`, which stores the enum's *value* in a VARCHAR with a
    CHECK constraint. SQLModel's default would create a native Postgres ENUM holding member
    names — see the note on `enum_column` for why that is the wrong trade here.

    Note that SQLModel skips validation on `table=True` models, so lowercasing `username`
    and `email` is the service layer's job (app/services/users.py) — the unique index here
    is case-sensitive and would happily accept "Alvin" beside "alvin".
    """

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # Globally unique, so login can take one field and resolve it itself.
    username: str = Field(unique=True, index=True)
    # Optional: a subuser is created by the owner and often has no address of their own.
    # Postgres allows many NULLs under a unique index, which is exactly what we want.
    email: str | None = Field(default=None, unique=True, index=True)
    password_hash: str
    display_name: str
    role: UserRole = Field(
        default=UserRole.MANAGER,
        sa_column=enum_column(UserRole, nullable=False, index=True),
    )
    is_active: bool = Field(default=True)
    # SET NULL: deleting the owner who created a manager must not delete the manager.
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
