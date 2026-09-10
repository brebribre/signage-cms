import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class Campaign(SQLModel, table=True):
    """A named set of devices plus the playlist-on-schedule rules that play across all of them.

    Owns its rules by generating one `Schedule` row per (device, rule) pair — see
    `Schedule.campaign_id`. Editing a campaign deletes and regenerates that whole set rather
    than diffing it, so the schedules a campaign produced are always an exact mirror of its
    current device list and rules, never a stale partial update.
    """

    __tablename__ = "campaigns"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    created_by: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    name: str
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class CampaignDevice(SQLModel, table=True):
    """Which devices a campaign targets. Composite key — a device is either in a campaign or
    not, there is nothing else to say about the membership row itself."""

    __tablename__ = "campaign_devices"

    campaign_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    )
    device_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    )
