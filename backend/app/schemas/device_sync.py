import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import DeviceOrientation, ItemFit, MediaKind


class ManifestDevice(BaseModel):
    name: str
    orientation: DeviceOrientation
    # IANA name the screen's schedules are expressed in — the player evaluates its power
    # schedule on it. An older player ignores the key.
    timezone: str = "UTC"


class ManifestPlaylist(BaseModel):
    id: uuid.UUID
    name: str
    shuffle: bool


class ManifestElement(BaseModel):
    id: uuid.UUID
    #: The underlying media, distinct from `id` (which identifies the *element*, not the
    #: scene). The device reports this back for proof-of-play, and the server resolves the
    #: filename from it — so the log stays authoritative rather than trusting a name the
    #: device made up. None for a website element.
    media_id: uuid.UUID | None = None
    #: "image", "video", or "web" — a website, loaded live from `url` (nothing to download;
    #: `checksum` is derived from the address and `bytes` is 0). Players older than 1.1.2 skip it.
    kind: str
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
    # Pan/zoom within the element's box — see PlaylistItemElement. Not applied by any player
    # build yet (rotation isn't either, until the multi-element rendering work lands), but
    # sent regardless so the wire shape doesn't need a second migration once it is.
    crop_x: float | None = None
    crop_y: float | None = None
    crop_zoom: float | None = None


class ManifestSlot(BaseModel):
    id: uuid.UUID
    duration_seconds: int
    elements: list[ManifestElement]


class ManifestItem(BaseModel):
    """The flat shape the player app actually deserializes (`Models.kt`'s `ManifestItem`) —
    one element per slot, everything about it lifted onto the slot itself. The player predates
    the multi-element scene model `ManifestSlot`/`ManifestElement` above were built for, and
    was never updated to render more than one layer per item, so a slot with more than one
    element degrades to its first (paint-order) element rather than being dropped outright —
    the common case (every slot today has exactly one) plays correctly either way."""

    id: uuid.UUID
    media_id: uuid.UUID
    kind: MediaKind
    url: str
    checksum: str
    bytes: int
    duration_seconds: int
    fit: ItemFit
    has_audio: bool


class ManifestResponse(BaseModel):
    version: str
    device: ManifestDevice
    # None, not a 404: an unassigned screen is a valid state, not an error.
    playlist: ManifestPlaylist | None
    # Named to match what `Models.kt` actually deserializes — see `ManifestItem`'s docstring.
    items: list[ManifestItem]
    # The real, multi-element shape — every element of every slot, unflattened. Additive: kept
    # alongside `items` rather than replacing it, so an already-deployed player build (which
    # only knows `items` and ignores unknown keys) is completely unaffected by this field's
    # existence. Only a player new enough to render more than one element per slot reads it.
    slots: list[ManifestSlot] = Field(default_factory=list)
    # The schedule currently overriding the default, if any.
    schedule_name: str | None = None
    # ISO-8601 UTC. The device re-polls at this moment rather than on its next 30s tick, so a
    # daypart boundary lands on time instead of up to 30 seconds late.
    valid_until: str | None = None
    # Every remotely-configurable value currently set — volume today, more later by the same
    # registry (services/device_settings.py). A key absent here means "use the player's own
    # default," not "set to nothing."
    settings: dict[str, Any] = Field(default_factory=dict)


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
    # What the device's settings actually are right now — distinct from `ManifestResponse
    # .settings`, which is what the CMS wants them to be. Absent entirely on a build that
    # predates reporting; an unrecognized key inside it is dropped, not rejected — see
    # services/device_settings.py::record_reported.
    reported_settings: dict[str, Any] | None = None


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
