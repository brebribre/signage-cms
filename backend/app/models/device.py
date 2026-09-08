import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class DeviceOrientation(StrEnum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


class Device(SQLModel, table=True):
    """A screen.

    A device row is created by the *device* — unauthenticated — when it first boots and asks
    for a pairing code, so `account_id` is nullable until a human claims it. That is the one
    place in the schema where a row legitimately belongs to nobody.
    """

    __tablename__ = "devices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Nullable until claimed. Everything that lists devices filters on it, so an unclaimed
    # row is invisible to every account by construction rather than by remembering a WHERE.
    account_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True),
    )
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    name: str = Field(default="")
    location: str = Field(default="")

    # --- Pairing ---
    # Six characters from an unambiguous alphabet: it gets read off a TV across a room.
    # Cleared once claimed, so a code can never be reused to hijack a live screen.
    pairing_code: str | None = Field(default=None, unique=True, index=True)
    # The device polls with this instead of the human-readable code, so a shoulder-surfed
    # code cannot be used to collect the token.
    poll_token: str | None = Field(default=None, unique=True, index=True)
    pairing_expires_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))

    # sha256 of the device token, never the token itself — the plaintext is shown to the
    # device exactly once and is unrecoverable from here.
    token_hash: str | None = Field(default=None, unique=True, index=True)
    paired_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))

    # --- Content ---
    # SET NULL: deleting a playlist must not delete the hardware. The screen falls back to
    # its idle card, which is a valid state rather than an error.
    playlist_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    # IANA name, e.g. "Asia/Jakarta". Schedules are expressed in the screen's local wall
    # clock, so this is what makes "until 11am" mean the same thing in two cities. UTC is a
    # safe default rather than a guess at the operator's locale.
    timezone: str = Field(default="UTC")
    orientation: DeviceOrientation = Field(
        default=DeviceOrientation.LANDSCAPE,
        sa_column=enum_column(DeviceOrientation, nullable=False),
    )

    # --- Reported by the device on each heartbeat ---
    screen_width: int | None = None
    screen_height: int | None = None
    app_version: str | None = None
    last_seen_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))

    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class DeviceAccess(SQLModel, table=True):
    """Which devices a manager may reach.

    Consulted **only** for role='manager'. An owner reaches every device in their account
    without a row here, so granting access is never something you can forget to do for
    yourself.

    Cascades from both sides: deleting a user or a device removes its grants, and a grant is
    never the reason a delete fails.
    """

    __tablename__ = "device_access"

    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    )
    device_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, index=True
        )
    )
    granted_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
