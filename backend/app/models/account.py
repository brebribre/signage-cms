import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class Account(SQLModel, table=True):
    """The tenant. Media, playlists and devices belong to an account, never to a user.

    This is what makes subusers safe: a manager's upload has to stay visible to the owner
    and to their colleagues, so deleting the person must not take the content with them.
    """

    __tablename__ = "accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    # Bytes. None means unlimited, which is the default — a quota that appears without anyone
    # setting it would block uploads for reasons nobody chose.
    storage_quota_bytes: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
