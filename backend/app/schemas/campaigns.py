import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field

from app.models.schedule import ALL_DAYS
from app.services.schedules import MAX_PRIORITY


class CampaignRuleWrite(BaseModel):
    playlist_id: uuid.UUID
    name: str = Field(default="", max_length=80)
    # Bit 0 = Monday … bit 6 = Sunday, same bitmask as Schedule. Defaults to every day so the
    # common case — one playlist, no dayparting — needs only a playlist and a time range.
    days_of_week: int = Field(default=ALL_DAYS, ge=1, le=ALL_DAYS)
    starts_at: time = time(0, 0)
    ends_at: time = time(23, 59)
    priority: int = Field(default=0, ge=0, le=MAX_PRIORITY)


class CampaignRuleRead(CampaignRuleWrite):
    pass


class CampaignWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    device_ids: list[uuid.UUID] = Field(min_length=1)
    # At least one rule: a campaign with none would be indistinguishable from not existing —
    # there would be nothing for it to make any device play.
    rules: list[CampaignRuleWrite] = Field(min_length=1)


class CampaignSummary(BaseModel):
    id: uuid.UUID
    name: str
    device_count: int
    rule_count: int
    created_at: datetime
    updated_at: datetime


class CampaignRead(BaseModel):
    id: uuid.UUID
    name: str
    device_ids: list[uuid.UUID]
    rules: list[CampaignRuleRead]
    created_at: datetime
    updated_at: datetime


class CampaignSaveResult(BaseModel):
    campaign: CampaignRead
    # Requested device ids the caller couldn't reach — dropped rather than failing the whole
    # save, same reasoning as the device bulk-assign endpoint.
    skipped_device_ids: list[uuid.UUID]
