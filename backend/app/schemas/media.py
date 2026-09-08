import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import MediaKind


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)


class UploadResponse(BaseModel):
    media_id: uuid.UUID
    # The browser PUTs the file here, then the poster JPEG to the second URL, then calls
    # /media/{id}/complete. Nothing is visible in the library until that third call.
    upload_url: str
    thumbnail_upload_url: str


class CompleteRequest(BaseModel):
    """Metadata the browser read from the file itself.

    Read client-side on purpose: it avoids an ffmpeg dependency in the API image, and this is
    single-tenant, so it needs no adversarial hardening. The one thing that *is* verified
    server-side is that the object exists and is the declared size.
    """

    checksum: str = Field(min_length=1, max_length=128)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, gt=0)


class MediaRead(BaseModel):
    id: uuid.UUID
    filename: str
    kind: MediaKind
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    duration_seconds: float | None
    checksum: str
    created_at: datetime
    created_by: uuid.UUID | None
    thumbnail_url: str | None
    used_in: list[str] = []


class MediaDetail(MediaRead):
    url: str
