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


class HeartbeatScreen(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class HeartbeatRequest(BaseModel):
    app_version: str | None = Field(default=None, max_length=32)
    screen: HeartbeatScreen | None = None
    current_item_id: uuid.UUID | None = None
    errors: list[str] = Field(default_factory=list, max_length=20)


class HeartbeatResponse(BaseModel):
    """The current version, so a device heartbeating more often than it polls the manifest
    learns early that it should re-fetch."""

    version: str
