"""The platform in numbers, for the monitoring app's Infrastructure page: how full the R2 bucket
is, how many people can sign in, and how many screens are paired and online.

Read-only and platform-wide. Nothing here is scoped to an account, so nothing here may ever be
reached from a customer route — the one caller is routes/admin.py, behind `RequireStaff`.

**Two different storage numbers, on purpose.** The bucket total comes from walking R2 itself:
it is what Cloudflare bills, and it includes what no account is charged for — thumbnails,
playback copies, player builds, and anything orphaned. The per-account figures come from the
database, the same sum the quotas use. The page shows both, so the gap between them is visible
rather than a surprise on the invoice.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.config import get_settings
from app.infra import storage
from app.models import Account, Device, DevicePlatform, Media, MediaStatus, User, UserRole

logger = logging.getLogger(__name__)

#: Walking the bucket costs one billed List call per 1,000 objects, and its size moves slowly,
#: so one measurement serves every page load for this long.
BUCKET_CACHE_SECONDS = 5 * 60

#: A screen that checked in this recently is online. Two missed 30s polls plus slack — the same
#: line as services/operations.py and the CMS's green dot, so the three never disagree.
ONLINE_WITHIN = timedelta(minutes=2)

#: How far back the monthly chart reaches, counting the current month.
TREND_MONTHS = 6

# What each part of the bucket is, read from its key. The key layouts are set in
# services/media.py, services/video_streams.py and services/player_releases.py.
PART_LABELS = {
    "media": "Uploaded media",
    "copies": "Playback copies",
    "thumbnails": "Thumbnails",
    "builds": "Player builds",
    "other": "Other",
}


def _part_of(key: str) -> str:
    if key.startswith("apks/"):
        return "builds"
    if key.startswith("media/"):
        name = key.rsplit("/", 1)[-1]
        if name == "thumb.jpg":
            return "thumbnails"
        if name in ("playback.mp4", "stream.mp4"):
            return "copies"
        return "media"
    return "other"


@dataclass(frozen=True)
class StoragePart:
    key: str
    label: str
    bytes: int
    objects: int | None


@dataclass(frozen=True)
class BucketMeasure:
    used_bytes: int
    object_count: int
    parts: list[StoragePart]
    measured_at: datetime


_cache: BucketMeasure | None = None
_cache_at = 0.0
_lock = threading.Lock()


def _measure_bucket() -> BucketMeasure:
    totals = {k: [0, 0] for k in PART_LABELS}
    for obj in storage.iter_objects():
        part = totals[_part_of(obj["Key"])]
        part[0] += int(obj.get("Size", 0))
        part[1] += 1
    parts = [StoragePart(k, PART_LABELS[k], b, n) for k, (b, n) in totals.items()]
    return BucketMeasure(
        used_bytes=sum(p.bytes for p in parts),
        object_count=sum(p.objects or 0 for p in parts),
        parts=parts,
        measured_at=datetime.now(UTC),
    )


def bucket_measure() -> BucketMeasure:
    """The bucket's size, at most `BUCKET_CACHE_SECONDS` old. Raises if R2 cannot be read —
    the caller falls back to the database's figure."""
    global _cache, _cache_at
    with _lock:
        if _cache is None or time.monotonic() - _cache_at > BUCKET_CACHE_SECONDS:
            _cache = _measure_bucket()
            _cache_at = time.monotonic()
        return _cache


# --- The report ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountStorage:
    id: uuid.UUID
    name: str
    bytes: int


@dataclass(frozen=True)
class MonthStorage:
    month: str  # "2026-09"
    bytes: int


@dataclass(frozen=True)
class StorageReport:
    limit_bytes: int
    used_bytes: int
    # "bucket" when R2 itself was measured; "database" when it could not be, and the figure is
    # the sum of what the media table knows about instead (no thumbnails, builds or orphans).
    source: str
    object_count: int | None
    measured_at: datetime
    parts: list[StoragePart]
    # Bytes of media (with its copies) uploaded in the last 30 days and still here — the pace
    # the page uses to guess when the limit is reached.
    added_30d_bytes: int
    monthly: list[MonthStorage]
    top_accounts: list[AccountStorage]
    bucket_error: str | None = None


@dataclass(frozen=True)
class UserReport:
    total: int
    active: int
    main_users: int
    sub_accounts: int
    new_30d: int
    accounts: int
    client_accounts: int


@dataclass(frozen=True)
class ScreenReport:
    paired: int
    online: int
    android: int
    web: int
    new_30d: int


@dataclass(frozen=True)
class InfrastructureReport:
    storage: StorageReport
    users: UserReport
    screens: ScreenReport
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _media_bytes():
    """A ready media row's full footprint: the file, plus the copies made for playback."""
    return (
        Media.size_bytes
        + func.coalesce(Media.stream_size_bytes, 0)
        + func.coalesce(Media.playback_size_bytes, 0)
    )


def _month_starts(now: datetime) -> list[datetime]:
    year, month = now.year, now.month
    out = []
    for _ in range(TREND_MONTHS):
        out.append(datetime(year, month, 1, tzinfo=UTC))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return list(reversed(out))


def _storage(session: Session, now: datetime) -> StorageReport:
    settings = get_settings()
    ready = Media.status == MediaStatus.READY

    # What the database knows, split the way the bucket is: originals, and their copies.
    originals, copies = session.exec(
        select(
            func.coalesce(func.sum(Media.size_bytes), 0),
            func.coalesce(
                func.sum(
                    func.coalesce(Media.stream_size_bytes, 0)
                    + func.coalesce(Media.playback_size_bytes, 0)
                ),
                0,
            ),
        ).where(ready)
    ).one()

    added_30d = session.exec(
        select(func.coalesce(func.sum(_media_bytes()), 0)).where(
            ready, Media.created_at >= now - timedelta(days=30)
        )
    ).one()

    starts = _month_starts(now)
    rows = session.exec(
        select(Media.created_at, _media_bytes()).where(ready, Media.created_at >= starts[0])
    ).all()
    by_month = {s.strftime("%Y-%m"): 0 for s in starts}
    for created_at, size in rows:
        by_month[created_at.astimezone(UTC).strftime("%Y-%m")] += int(size)

    top = session.exec(
        select(Account.id, Account.name, func.sum(Media.size_bytes).label("used"))
        .join(Media, Media.account_id == Account.id)
        .where(ready)
        .group_by(Account.id, Account.name)
        .order_by(func.sum(Media.size_bytes).desc())
        .limit(5)
    ).all()

    base = dict(
        limit_bytes=int(settings.r2_storage_limit_gb * 1024**3),
        added_30d_bytes=int(added_30d),
        monthly=[MonthStorage(m, b) for m, b in by_month.items()],
        top_accounts=[AccountStorage(i, n, int(b)) for i, n, b in top],
    )
    try:
        bucket = bucket_measure()
    except Exception as exc:  # noqa: BLE001 — any failure to reach R2 falls back the same way
        logger.warning("could not measure the R2 bucket, showing the database's figure: %s", exc)
        parts = [
            StoragePart("media", PART_LABELS["media"], int(originals), None),
            StoragePart("copies", PART_LABELS["copies"], int(copies), None),
        ]
        return StorageReport(
            **base,
            used_bytes=int(originals) + int(copies),
            source="database",
            object_count=None,
            measured_at=now,
            parts=parts,
            bucket_error="Could not reach the R2 bucket, so this is the database's own count.",
        )
    return StorageReport(
        **base,
        used_bytes=bucket.used_bytes,
        source="bucket",
        object_count=bucket.object_count,
        measured_at=bucket.measured_at,
        parts=bucket.parts,
    )


def _users(session: Session, now: datetime) -> UserReport:
    def count(*where) -> int:
        return int(session.exec(select(func.count()).select_from(User).where(*where)).one())

    accounts = session.exec(select(Account.kind, func.count()).group_by(Account.kind)).all()
    kinds = {k: int(n) for k, n in accounts}
    return UserReport(
        total=count(),
        active=count(User.is_active),
        main_users=count(User.role == UserRole.OWNER),
        sub_accounts=count(User.role == UserRole.MANAGER),
        new_30d=count(User.created_at >= now - timedelta(days=30)),
        accounts=sum(kinds.values()),
        client_accounts=kinds.get("client", 0),
    )


def _screens(session: Session, now: datetime) -> ScreenReport:
    """Paired screens — the same ones that count against an account's screen limit
    (services/devices.py::count_claimed): in an account, and not told to disconnect."""
    paired = (Device.account_id.is_not(None), Device.disconnect_requested_at.is_(None))

    def count(*where) -> int:
        return int(session.exec(select(func.count()).select_from(Device).where(*paired, *where)).one())

    return ScreenReport(
        paired=count(),
        online=count(Device.last_seen_at >= now - ONLINE_WITHIN),
        android=count(Device.platform == DevicePlatform.ANDROID),
        web=count(Device.platform == DevicePlatform.WEB),
        new_30d=count(Device.paired_at >= now - timedelta(days=30)),
    )


def report(session: Session) -> InfrastructureReport:
    now = datetime.now(UTC)
    return InfrastructureReport(
        storage=_storage(session, now),
        users=_users(session, now),
        screens=_screens(session, now),
        generated_at=now,
    )

