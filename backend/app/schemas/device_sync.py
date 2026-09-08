import uuid

from pydantic import BaseModel, Field

from app.models import DeviceOrientation, ItemFit, MediaKind


class ManifestDevice(BaseModel):
    name: str
    orientation: DeviceOrientation


class ManifestPlaylist(BaseModel):
    id: uuid.UUID
    name: str
    shuffle: bool


class ManifestItem(BaseModel):
    id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    duration_seconds: int
    fit: ItemFit


class ManifestResponse(BaseModel):
    version: str
    device: ManifestDevice
    # None, not a 404: an unassigned screen is a valid state, not an error.
    playlist: ManifestPlaylist | None
    items: list[ManifestItem]
    # The schedule currently overriding the default, if any.
    schedule_name: str | None = None
    # ISO-8601 UTC. The device re-polls at this moment rather than on its next 30s tick, so a
    # daypart boundary lands on time instead of up to 30 seconds late.
    valid_until: str | None = None


class HeartbeatScreen(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class HeartbeatRequest(BaseModel):
    app_version: str | None = Field(default=None, max_length=32)
    screen: HeartbeatScreen | None = None
    current_item_id: uuid.UUID | None = None
    errors: list[str] = Field(default_factory=list, max_length=20)


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
