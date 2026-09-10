import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DeviceOrientation


class DeviceRead(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    timezone: str
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
    `mqtt_password` rides along the same way, same reasoning — see
    services/devices.py::poll_pairing. Absent (not just None) when MQTT is disabled or
    provisioning failed; a screen with no password simply never connects for push and
    polls exactly as it always has.
    """

    claimed: bool
    device_id: uuid.UUID
    device_token: str | None = None
    mqtt_password: str | None = None
    name: str | None = None


class ClaimRequest(BaseModel):
    pairing_code: str = Field(min_length=4, max_length=12)
    name: str = Field(min_length=1, max_length=80)
    location: str = Field(default="", max_length=120)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=120)
    # IANA name. Validated in the service against the system's tz database, so a typo is a
    # 422 here rather than a screen silently running on UTC.
    timezone: str | None = Field(default=None, max_length=64)
    orientation: DeviceOrientation | None = None
    playlist_id: uuid.UUID | None = None
    # Explicit, because `playlist_id: null` is indistinguishable from "not supplied" in a
    # PATCH body — without this there is no way to say "play nothing".
    clear_playlist: bool = False


class DeviceResolutionRead(BaseModel):
    """What one device is playing right now — the read-only counterpart to Campaign, which is
    the only place that can change it. Same shape as `ResolutionRead` plus which device."""

    device_id: uuid.UUID
    playlist_id: uuid.UUID | None
    schedule_id: uuid.UUID | None
    schedule_name: str | None
    valid_until: datetime | None
    timezone: str
    device_local_time: datetime
