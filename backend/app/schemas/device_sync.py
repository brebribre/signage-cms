import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DeviceOrientation, ItemFit, MediaKind


class ManifestDevice(BaseModel):
    name: str
    orientation: DeviceOrientation


class ManifestPlaylist(BaseModel):
    id: uuid.UUID
    name: str
    shuffle: bool


class ManifestElement(BaseModel):
    id: uuid.UUID
    #: The underlying media, distinct from `id` (which identifies the *element*, not the
    #: scene). The device reports this back for proof-of-play, and the server resolves the
    #: filename from it — so the log stays authoritative rather than trusting a name the
    #: device made up.
    media_id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    z_index: int
    x: float
    y: float
    width: float
    height: float
    fit: ItemFit
    has_audio: bool
    rotation_degrees: int


class ManifestSlot(BaseModel):
    id: uuid.UUID
    duration_seconds: int
    elements: list[ManifestElement]


class ManifestResponse(BaseModel):
    version: str
    device: ManifestDevice
    # None, not a 404: an unassigned screen is a valid state, not an error.
    playlist: ManifestPlaylist | None
    slots: list[ManifestSlot]
    # The schedule currently overriding the default, if any.
    schedule_name: str | None = None
    # ISO-8601 UTC. The device re-polls at this moment rather than on its next 30s tick, so a
    # daypart boundary lands on time instead of up to 30 seconds late.
    valid_until: str | None = None


class HeartbeatScreen(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class PlayReport(BaseModel):
    """One item the screen actually showed. Batched by the device and sent on the next
    heartbeat, because an item can be shorter than the heartbeat interval — reporting only
    what is on screen *right now* would miss most of the loop."""

    media_id: uuid.UUID | None = None
    filename: str = Field(default="", max_length=255)
    started_at: datetime
    seconds: int = Field(default=0, ge=0, le=86_400)


class HeartbeatRequest(BaseModel):
    app_version: str | None = Field(default=None, max_length=32)
    screen: HeartbeatScreen | None = None
    current_item_id: uuid.UUID | None = None
    errors: list[str] = Field(default_factory=list, max_length=20)
    # Proof of play. Capped so a device with a runaway loop or a broken clock cannot flood
    # the table in one request.
    plays: list[PlayReport] = Field(default_factory=list, max_length=50)


class UpdateInfo(BaseModel):
    """An APK the screen should install. Only ever sent to a Device Owner-provisioned screen
    in practice — anything else declines to install it, since a non-owner install shows a
    confirmation dialog nobody is standing in front of."""

    version: str
    url: str


class HeartbeatResponse(BaseModel):
    """The current version, so a device heartbeating more often than it polls the manifest
    learns early that it should re-fetch."""

    version: str
    # null in the overwhelmingly common case: updates unconfigured, or the screen already
    # runs the published build.
    update: UpdateInfo | None = None
