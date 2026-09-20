import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class AdminAction(SQLModel, table=True):
    """One row per thing a platform admin did to a customer account: who, what, when.

    Both foreign keys SET NULL rather than CASCADE — the record of an admin creating or
    changing an account must outlive the admin's user row and the account itself, or the
    history vanishes exactly when someone wants to read it. `account_name` is a snapshot for
    the same reason.
    """

    __tablename__ = "admin_actions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admin_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    account_name: str
    # Short verb: "create_account", "set_limits".
    action: str
    # Plain-words description of the change, e.g. "max_screens 5 → 10".
    detail: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
