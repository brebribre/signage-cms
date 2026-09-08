import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DeviceOrientation


class DeviceRead(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    orientation: DeviceOrientation
    playlist_id: uuid.UUID | None
    screen_width: int | None
    screen_height: int | None
    app_version: str | None
    last_seen_at: datetime | None
    paired_at: datetime | None


class PairStartResponse(BaseModel):
    """Handed to the device on first boot. It shows the code and polls with the token."""

    device_id: uuid.UUID
    pairing_code: str
    poll_token: str
    expires_at: datetime
    poll_seconds: int


class PairPollResponse(BaseModel):
    """`claimed` is false while nobody has typed the code yet.

    `device_token` is present exactly once, on the first poll after a human claims it.
    """

    claimed: bool
    device_id: uuid.UUID
    device_token: str | None = None
    name: str | None = None


class ClaimRequest(BaseModel):
    pairing_code: str = Field(min_length=4, max_length=12)
    name: str = Field(min_length=1, max_length=80)
    location: str = Field(default="", max_length=120)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=120)
    orientation: DeviceOrientation | None = None
    playlist_id: uuid.UUID | None = None
    # Explicit, because `playlist_id: null` is indistinguishable from "not supplied" in a
    # PATCH body — without this there is no way to say "play nothing".
    clear_playlist: bool = False
