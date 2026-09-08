"""Running a fleet: storage accounting, device health, and proof of play."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, delete, func, select

from app.models import (
    Account,
    Device,
    DeviceEvent,
    EventLevel,
    Media,
    MediaStatus,
    PlayEvent,
    User,
)
from app.services.errors import DomainError

# How long event history is kept. Play events are the high-volume table — a screen showing a
# 10-second image generates ~8,600 rows a day — so this is a retention policy, not a
# suggestion. `scripts/prune_events.py` enforces it.
PLAY_EVENT_RETENTION_DAYS = 90
DEVICE_EVENT_RETENTION_DAYS = 30

# Cap on what one heartbeat may report, so a device with a broken clock or a runaway loop
# cannot flood the table in a single request.
MAX_EVENTS_PER_HEARTBEAT = 50


class QuotaExceeded(DomainError):
    def __init__(self, used: int, quota: int, incoming: int):
        self.used, self.quota, self.incoming = used, quota, incoming
        super().__init__(f"{used} + {incoming} > {quota}")


# --- Storage ----------------------------------------------------------------------------


def storage_used(session: Session, account_id: uuid.UUID) -> int:
    """Bytes held by ready media in this account.

    Counts `ready` only. A pending row has a presigned URL but may never have been uploaded,
    so charging for it would bill people for uploads that never happened — and an abandoned
    upload already costs nothing until the sweep finds it.
    """
    total = session.exec(
        select(func.coalesce(func.sum(Media.size_bytes), 0)).where(
            Media.account_id == account_id, Media.status == MediaStatus.READY
        )
    ).one()
    return int(total)


def check_quota(session: Session, *, account: Account, incoming_bytes: int) -> None:
    """Raise if this upload would exceed the account's quota.

    Called at `POST /media/uploads`, before a presigned URL is issued — the only point where
    refusing is still clean. Once the browser has started PUTting to R2 the bytes are already
    being paid for, and rejecting at `complete` would leave the object orphaned.
    """
    if account.storage_quota_bytes is None:
        return
    used = storage_used(session, account.id)
    if used + incoming_bytes > account.storage_quota_bytes:
        raise QuotaExceeded(used, account.storage_quota_bytes, incoming_bytes)


# --- Events -----------------------------------------------------------------------------


def record_event(
    session: Session, *, device: Device, level: EventLevel, message: str, commit: bool = True
) -> None:
    if device.account_id is None:
        return  # unclaimed device: nothing to attribute it to
    session.add(
        DeviceEvent(
            device_id=device.id,
            account_id=device.account_id,
            level=level,
            message=message[:500],
        )
    )
    if commit:
        session.commit()


def record_plays(
    session: Session, *, device: Device, plays: list[tuple[uuid.UUID | None, str, datetime, int]]
) -> int:
    """Append proof-of-play rows. Returns how many were stored.

    `filename` is copied in rather than joined at read time, so the record still means
    something after the media is deleted — a play log that goes blank when someone tidies the
    library is not evidence of anything.
    """
    if device.account_id is None:
        return 0
    stored = 0
    # Resolve names here rather than trusting what the device sent: the server knows what a
    # media id is called, and a log built from device-supplied names would drift the moment
    # anything is renamed.
    ids = [mid for mid, _, _, _ in plays if mid is not None]
    names: dict[uuid.UUID, str] = {}
    if ids:
        for m in session.exec(select(Media).where(Media.id.in_(ids))).all():
            names[m.id] = m.filename

    for media_id, filename, started_at, seconds in plays[:MAX_EVENTS_PER_HEARTBEAT]:
        resolved = names.get(media_id) if media_id else None
        filename = resolved or filename
        session.add(
            PlayEvent(
                device_id=device.id,
                account_id=device.account_id,
                media_id=media_id,
                filename=filename[:255],
                started_at=started_at,
                seconds=max(0, seconds),
            )
        )
        stored += 1
    if stored:
        session.commit()
    return stored


def recent_events(
    session: Session, *, device: Device, limit: int = 50
) -> list[DeviceEvent]:
    return list(
        session.exec(
            select(DeviceEvent)
            .where(DeviceEvent.device_id == device.id)
            .order_by(DeviceEvent.created_at.desc())
            .limit(limit)
        ).all()
    )


def recent_plays(session: Session, *, device: Device, limit: int = 100) -> list[PlayEvent]:
    return list(
        session.exec(
            select(PlayEvent)
            .where(PlayEvent.device_id == device.id)
            .order_by(PlayEvent.started_at.desc())
            .limit(limit)
        ).all()
    )


# --- Health -----------------------------------------------------------------------------


@dataclass
class DeviceHealth:
    device_id: uuid.UUID
    name: str
    last_seen_at: datetime | None
    minutes_since_seen: float | None
    is_online: bool
    error_count_24h: int
    plays_24h: int
    app_version: str | None


def fleet_health(session: Session, *, user: User) -> list[DeviceHealth]:
    """One row per screen the user may reach, with 24-hour counters.

    Aggregated in two grouped queries rather than per-device loops — the whole reason to have
    a health page is to scan a fleet at once, and N+1 there is the difference between a page
    and a wait.
    """
    from app.services import devices as device_service

    devices = device_service.list_devices(session, user=user)
    if not devices:
        return []
    ids = [d.id for d in devices]
    since = datetime.now(UTC) - timedelta(hours=24)

    errors = dict(
        session.exec(
            select(DeviceEvent.device_id, func.count(DeviceEvent.id))
            .where(
                DeviceEvent.device_id.in_(ids),
                DeviceEvent.level == EventLevel.ERROR,
                DeviceEvent.created_at >= since,
            )
            .group_by(DeviceEvent.device_id)
        ).all()
    )
    plays = dict(
        session.exec(
            select(PlayEvent.device_id, func.count(PlayEvent.id))
            .where(PlayEvent.device_id.in_(ids), PlayEvent.started_at >= since)
            .group_by(PlayEvent.device_id)
        ).all()
    )

    now = datetime.now(UTC)
    out = []
    for d in devices:
        mins = (now - d.last_seen_at).total_seconds() / 60 if d.last_seen_at else None
        out.append(
            DeviceHealth(
                device_id=d.id,
                name=d.name or "Unnamed screen",
                last_seen_at=d.last_seen_at,
                minutes_since_seen=mins,
                # Two missed 30s polls plus slack. Matches the CMS's green dot so the two
                # never disagree about whether a screen is up.
                is_online=mins is not None and mins < 2,
                error_count_24h=errors.get(d.id, 0),
                plays_24h=plays.get(d.id, 0),
                app_version=d.app_version,
            )
        )
    return out


def prune(session: Session, *, now: datetime | None = None) -> tuple[int, int]:
    """Delete event rows past their retention window. Returns (plays, events) deleted."""
    now = now or datetime.now(UTC)
    plays = session.exec(
        delete(PlayEvent).where(
            PlayEvent.started_at < now - timedelta(days=PLAY_EVENT_RETENTION_DAYS)
        )
    ).rowcount or 0
    events = session.exec(
        delete(DeviceEvent).where(
            DeviceEvent.created_at < now - timedelta(days=DEVICE_EVENT_RETENTION_DAYS)
        )
    ).rowcount or 0
    session.commit()
    return plays, events
