import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DeviceOrientation, DevicePlatform, DeviceUpdateState


class DeviceRead(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    timezone: str
    orientation: DeviceOrientation
    # "android" or "web" — web screens update by reloading, so APK rollouts skip them.
    platform: DevicePlatform
    playlist_id: uuid.UUID | None
    screen_width: int | None
    screen_height: int | None
    app_version: str | None
    last_seen_at: datetime | None
    paired_at: datetime | None
    # A single-device update pinned from the Devices page, independent of the fleet rollout —
    # None means nothing is pending. Cleared automatically once the screen reports running it.
    forced_update_version: str | None
    # When that pinned update may start; None means on the screen's next check-in.
    forced_update_at: datetime | None = None
    # What the screen itself last said about installing a build — see Device.update_state.
    # All None until a screen running a player new enough to report has been offered one.
    # Read alongside `forced_update_version`: a pin with no report yet is "pending", a report
    # for a version other than the pin is about an earlier attempt or a fleet rollout.
    update_state: DeviceUpdateState | None = None
    update_version: str | None = None
    update_progress_pct: int | None = None
    update_detail: str | None = None
    update_reported_at: datetime | None = None
    # Playback health from the last heartbeat — see Device.playback_dropped_frames.
    playback_dropped_frames: int | None = None
    playback_decoder: str | None = None
    download_bytes_per_second: int | None = None
    playback_reported_at: datetime | None = None
    # Whether the player runs as Android Device Owner — see Device.device_owner. Null on web
    # screens and on players that predate reporting.
    device_owner: bool | None = None
    # Set once "Disconnect" has been clicked and the screen is being told; the row disappears
    # (GET → 404) the moment the screen has heard. See Device.disconnect_requested_at.
    disconnect_requested_at: datetime | None = None


class PairStartRequest(BaseModel):
    """Optional: the Android player posts an empty body, which is read as "android"."""

    platform: DevicePlatform = DevicePlatform.ANDROID


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


class DeviceUpdateVersionWrite(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    # None installs on the next check-in; a future instant holds the update until then.
    scheduled_at: datetime | None = None


class ProbeResponse(BaseModel):
    """Baseline for the frontend to watch: it polls `GET /devices/{id}` afterward and treats
    `last_seen_at` moving past `probed_at` as "the screen just checked in" — a live confirmation
    rather than whatever `last_seen_at` already said before this was called."""

    probed_at: datetime
    previous_last_seen_at: datetime | None


class DeviceResolutionRead(BaseModel):
    """What one device is playing right now — the read-only counterpart to Campaign, which is
    the only place that can change it. Same shape as `ResolutionRead` plus which device."""

    device_id: uuid.UUID
    playlist_id: uuid.UUID | None
    schedule_id: uuid.UUID | None
    schedule_name: str | None
    campaign_id: uuid.UUID | None
    valid_until: datetime | None
    timezone: str
    device_local_time: datetime
