"""SQLModel tables.

Every table module must be imported here: Alembic's autogenerate walks
`SQLModel.metadata`, and a table nobody imported is invisible to it — the migration comes
out empty and the omission is silent.
"""

from app.models.account import Account
from app.models.campaign import Campaign, CampaignDevice
from app.models.device import Device, DeviceAccess, DeviceOrientation
from app.models.device_setting import DeviceSetting
from app.models.events import DeviceEvent, EventLevel, PlayEvent
from app.models.media import Media, MediaKind, MediaStatus
from app.models.playlist import ItemFit, Playlist, PlaylistItem, PlaylistItemElement
from app.models.player_rollout import PlayerRollout
from app.models.schedule import ALL_DAYS, WEEKDAYS, WEEKENDS, Schedule
from app.models.user import User, UserRole

__all__ = [
    "Account",
    "Campaign",
    "CampaignDevice",
    "Device",
    "DeviceAccess",
    "DeviceSetting",
    "DeviceEvent",
    "DeviceOrientation",
    "EventLevel",
    "PlayEvent",
    "ItemFit",
    "Media",
    "MediaKind",
    "MediaStatus",
    "Playlist",
    "PlaylistItem",
    "PlaylistItemElement",
    "PlayerRollout",
    "Schedule",
    "ALL_DAYS",
    "WEEKDAYS",
    "WEEKENDS",
    "User",
    "UserRole",
]
