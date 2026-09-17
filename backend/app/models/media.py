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

    # --- A copy of a video laid out for streaming playback (fragmented MP4) ---
    # Made by services/video_streams.py after upload: the same audio and video, rearranged —
    # never re-encoded — so a player can feed it to the browser's Media Source Extensions piece
    # by piece. That is the only way a smart TV's browser plays video from its own offline cache
    # (its media player can't open a plain file stored in the browser). The original stays what
    # the Android player downloads; all four are null until the copy exists.
    stream_key: str | None = None
    stream_size_bytes: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    # sha256, "sha256:"-prefixed — the copy's own identity, which a web screen caches it by.
    stream_checksum: str | None = None
    # The full MSE type string, codecs included: video/mp4; codecs="avc1.640028,mp4a.40.2".
    stream_mime: str | None = None
    # Why the copy couldn't be made (not H.264, ffmpeg failed…). Set once, so a file that can't
    # be converted isn't retried on every restart; web screens stream the original instead.
    stream_error: str | None = None

    status: MediaStatus = Field(
        default=MediaStatus.PENDING,
        sa_column=enum_column(MediaStatus, nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
