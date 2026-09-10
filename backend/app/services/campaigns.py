"""Campaigns: assigning one or more playlists, each on its own schedule, to many devices at
once. A campaign owns the `Schedule` rows it produces — see `Schedule.campaign_id` — and every
edit regenerates that whole set rather than diffing it, so a campaign's schedules are always an
exact mirror of its current device list and rules.
"""

import uuid
from datetime import time

from sqlmodel import Session, delete, select

from app.models import (
    Campaign,
    CampaignDevice,
    Device,
    DeviceAccess,
    Playlist,
    Schedule,
    User,
    UserRole,
)
from app.models.base import utcnow
from app.services.errors import DomainError

MAX_RULE_PRIORITY = 100


class CampaignNotFound(DomainError):
    pass


class InvalidCampaign(DomainError):
    pass


class CampaignRuleInput:
    """Plain carrier for one rule — routes build these from `CampaignRuleWrite`."""

    def __init__(
        self, *, playlist_id: uuid.UUID, name: str, days_of_week: int,
        starts_at: time, ends_at: time, priority: int,
    ) -> None:
        self.playlist_id = playlist_id
        self.name = name
        self.days_of_week = days_of_week
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.priority = priority


def _reachable_device_ids(session: Session, *, user: User, device_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Same scoping as everywhere else a device is looked up: same account, and — for a
    manager — only devices they were granted. Unreachable ids are dropped, not rejected, for
    the usual reason: which ids exist outside the caller's scope must not be observable."""
    statement = select(Device.id).where(
        Device.id.in_(device_ids),
        Device.account_id == user.account_id,
        Device.account_id.is_not(None),
    )
    if user.role == UserRole.MANAGER:
        statement = statement.join(
            DeviceAccess,
            (DeviceAccess.device_id == Device.id) & (DeviceAccess.user_id == user.id),
        )
    return set(session.exec(statement).all())


def _write_schedules(
    session: Session, *, user: User, campaign: Campaign,
    device_ids: set[uuid.UUID], rules: list[CampaignRuleInput],
) -> None:
    for rule in rules:
        playlist = session.get(Playlist, rule.playlist_id)
        # 404-shaped rather than 403 elsewhere in this codebase — same reasoning applies, but
        # there is no HTTP layer this deep, so the message just has to be honest.
        if playlist is None or playlist.account_id != user.account_id:
            raise InvalidCampaign("that playlist is not available in this account")
        if rule.starts_at == rule.ends_at:
            raise InvalidCampaign("start and end must differ — use 00:00–23:59 for a whole day")

    for device_id in device_ids:
        for rule in rules:
            session.add(Schedule(
                account_id=user.account_id,
                device_id=device_id,
                playlist_id=rule.playlist_id,
                campaign_id=campaign.id,
                name=rule.name.strip(),
                days_of_week=rule.days_of_week,
                starts_at=rule.starts_at,
                ends_at=rule.ends_at,
                priority=rule.priority,
            ))


def _notify_many(session: Session, device_ids: set[uuid.UUID]) -> None:
    from app.infra import mqtt
    from app.services import device_sync

    for device_id in device_ids:
        device = session.get(Device, device_id)
        if device is not None:
            mqtt.notify_manifest_changed(
                device_id=device.id, version=device_sync.compute_version(session, device),
            )


def list_campaigns(session: Session, *, user: User) -> list[Campaign]:
    """Every campaign in the account. Account-wide like playlists, not scoped by device grant —
    a manager sees the same campaign library an owner does; only which devices they may *add*
    to one is scoped, at write time."""
    return list(
        session.exec(
            select(Campaign).where(Campaign.account_id == user.account_id).order_by(Campaign.name)
        ).all()
    )


def get(session: Session, *, user: User, campaign_id: uuid.UUID) -> Campaign:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None or campaign.account_id != user.account_id:
        raise CampaignNotFound(str(campaign_id))
    return campaign


def device_ids_for(session: Session, *, campaign_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.exec(
            select(CampaignDevice.device_id).where(CampaignDevice.campaign_id == campaign_id)
        ).all()
    )


def rules_for(session: Session, *, campaign_id: uuid.UUID) -> list[Schedule]:
    """The campaign's rules, read back off the `Schedule` rows it generated.

    Every device in a campaign carries an identical set of rows (see `_write_schedules`), so
    de-duplicating by rule shape across all of them recovers exactly the rule list the campaign
    was saved with — with no separate rule table needed."""
    rows = list(
        session.exec(
            select(Schedule)
            .where(Schedule.campaign_id == campaign_id)
            .order_by(Schedule.priority.desc(), Schedule.starts_at)
        ).all()
    )
    seen: set[tuple] = set()
    rules: list[Schedule] = []
    for row in rows:
        key = (row.playlist_id, row.name, row.days_of_week, row.starts_at, row.ends_at, row.priority)
        if key in seen:
            continue
        seen.add(key)
        rules.append(row)
    return rules


def create(
    session: Session, *, user: User, name: str,
    device_ids: list[uuid.UUID], rules: list[CampaignRuleInput],
) -> tuple[Campaign, list[uuid.UUID]]:
    reachable = _reachable_device_ids(session, user=user, device_ids=device_ids)
    if not reachable:
        raise InvalidCampaign("none of the selected devices are available")
    skipped = [d for d in device_ids if d not in reachable]

    campaign = Campaign(account_id=user.account_id, created_by=user.id, name=name.strip())
    session.add(campaign)
    session.flush()  # need campaign.id before the rows below can reference it

    for device_id in reachable:
        session.add(CampaignDevice(campaign_id=campaign.id, device_id=device_id))
    _write_schedules(session, user=user, campaign=campaign, device_ids=reachable, rules=rules)

    session.commit()
    session.refresh(campaign)
    _notify_many(session, reachable)
    return campaign, skipped


def update(
    session: Session, *, user: User, campaign: Campaign, name: str,
    device_ids: list[uuid.UUID], rules: list[CampaignRuleInput],
) -> tuple[Campaign, list[uuid.UUID]]:
    reachable = _reachable_device_ids(session, user=user, device_ids=device_ids)
    if not reachable:
        raise InvalidCampaign("none of the selected devices are available")
    skipped = [d for d in device_ids if d not in reachable]

    # Devices leaving the campaign need a nudge too — their schedule rows are about to
    # disappear, and that is just as much a change to what they play as one appearing.
    previously_targeted = set(device_ids_for(session, campaign_id=campaign.id))

    campaign.name = name.strip()
    campaign.updated_at = utcnow()
    session.add(campaign)

    session.exec(delete(Schedule).where(Schedule.campaign_id == campaign.id))
    session.exec(delete(CampaignDevice).where(CampaignDevice.campaign_id == campaign.id))
    session.flush()

    for device_id in reachable:
        session.add(CampaignDevice(campaign_id=campaign.id, device_id=device_id))
    _write_schedules(session, user=user, campaign=campaign, device_ids=reachable, rules=rules)

    session.commit()
    session.refresh(campaign)
    _notify_many(session, previously_targeted | reachable)
    return campaign, skipped


def remove(session: Session, *, campaign: Campaign) -> None:
    targeted = set(device_ids_for(session, campaign_id=campaign.id))
    session.exec(delete(Campaign).where(Campaign.id == campaign.id))
    session.commit()
    _notify_many(session, targeted)
