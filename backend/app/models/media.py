import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class MediaStatus(StrEnum):
    # A row exists and a presigned PUT was issued, but nothing confirmed the upload.
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Media(SQLModel, table=True):
    """One uploaded file.

    A row is created before the browser uploads anything, and only reaches `ready` when
    `POST /media/{id}/complete` verifies the object exists in R2. Rows that never get there
    stay `pending` and are never listed — which is what makes an abandoned upload harmless
    rather than a broken tile in the library.
    """

    __tablename__ = "media"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # Attribution only. SET NULL so deleting a subuser never deletes their uploads.
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    filename: str
    kind: MediaKind = Field(sa_column=enum_column(MediaKind, nullable=False, index=True))
    mime_type: str
    # BIGINT: a 500 MB file is comfortably inside int32, but a future limit need not be.
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    width: int | None = None
    height: int | None = None
    # Images have no duration; a video's is what a playlist item defaults to.
    duration_seconds: float | None = None

    storage_key: str
    thumbnail_key: str | None = None
    # sha256 hex. Not unique: two accounts may legitimately hold the same file, and the
    # device cache keys on it, so it must stay the file's identity rather than a row's.
    checksum: str = Field(index=True)

    status: MediaStatus = Field(
        default=MediaStatus.PENDING,
        sa_column=enum_column(MediaStatus, nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
