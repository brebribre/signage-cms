"""Devices: pairing, claiming, and the token a screen authenticates with.

The pairing flow exists because a signage device has no keyboard and no browser to log into.
So the **device asks for a code, and a human types that code into the CMS** — the credential
is minted by the server and handed to the device, and is never entered on it.
"""

import hashlib
import logging
import secrets
import time
import uuid
from datetime import timedelta

from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import mqtt, mqtt_admin
from app.models import (
    Device,
    DeviceAccess,
    DeviceOrientation,
    Playlist,
    User,
    UserRole,
)
from app.models.base import utcnow
from app.services import device_sync
from app.services.errors import DomainError

logger = logging.getLogger(__name__)

# No 0/O, 1/I/L: the code is read off a television from across a room, and every ambiguous
# glyph becomes a support call.
PAIRING_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PAIRING_CODE_LENGTH = 6

# Claiming is a guess against a small space, and a correct guess attaches someone else's
# screen to your account. Ten attempts a minute is far more than typing needs.
CLAIM_ATTEMPT_LIMIT = 10
CLAIM_WINDOW_SECONDS = 60


class PairingNotFound(DomainError):
    """Unknown code, expired code, or one that has already been claimed."""


class DeviceNotFound(DomainError):
    pass


class TooManyClaimAttempts(DomainError):
    pass


class InvalidPlaylist(DomainError):
    pass


class InvalidTimezone(DomainError):
    pass


def hash_token(token: str) -> str:
    """sha256 hex. The plaintext token is never stored — see `poll_pairing`."""
    return hashlib.sha256(token.encode()).hexdigest()


def _new_code(session: Session) -> str:
    """A code no other pending device is using."""
    for _ in range(20):
        code = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
        if session.exec(select(Device).where(Device.pairing_code == code)).first() is None:
            return code
    raise RuntimeError("could not allocate a unique pairing code")


def sweep_expired(session: Session) -> int:
    """Delete unclaimed devices whose code has expired.

    Called when a new pairing starts, so the table cannot accumulate rows from screens that
    were powered on once and never claimed. Only ever touches rows with no account.
    """
    result = session.exec(
        delete(Device).where(
            Device.account_id.is_(None),
            Device.pairing_expires_at.is_not(None),
            Device.pairing_expires_at < utcnow(),
        )
    )
    session.commit()
    return result.rowcount or 0


def start_pairing(session: Session) -> Device:
    """Called by the **device**, unauthenticated, on first boot.

    Creates a row belonging to nobody. That is the one place in the schema where a row
    legitimately has no account, and every listing filters unclaimed rows out.
    """
    sweep_expired(session)
    settings = get_settings()
    device = Device(
        pairing_code=_new_code(session),
        # The device polls with this, not with the human-readable code, so a code
        # shoulder-surfed off the screen cannot be exchanged for a token.
        poll_token=secrets.token_urlsafe(32),
        pairing_expires_at=utcnow() + timedelta(seconds=settings.pairing_code_ttl_seconds),
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def poll_pairing(session: Session, *, poll_token: str) -> tuple[Device, str | None, str | None]:
    """Called by the device every few seconds.

    Returns `(device, plaintext_token_or_None, mqtt_password_or_None)`.

    **The device token is generated here, not at claim time.** That is what lets us store
    only a hash: a token minted during `claim` would have to sit in plaintext somewhere until
    the device collected it, which defeats hashing entirely. Instead `claim` marks the row as
    owned, and the first poll afterwards mints the token, saves its hash, hands back the
    plaintext, and destroys the poll token so it can never be collected twice.

    The MQTT password gets the same one-time-mint treatment, for the same reason — it is
    never stored, only handed back once. Unlike the bearer token, provisioning it can fail
    (a broker hiccup) without failing the pairing itself: a device with no MQTT credentials
    just never receives a push and polls exactly as it always has, which is the whole point
    of push being a latency optimization and not a dependency.
    """
    device = session.exec(select(Device).where(Device.poll_token == poll_token)).first()
    if device is None:
        raise PairingNotFound(poll_token)

    if device.account_id is None:
        if device.pairing_expires_at and device.pairing_expires_at < utcnow():
            raise PairingNotFound(poll_token)
        return device, None, None  # still waiting for a human

    token = secrets.token_urlsafe(32)
    device.token_hash = hash_token(token)
    device.paired_at = utcnow()
    device.pairing_code = None   # a claimed code must never be reusable
    device.poll_token = None     # collected exactly once
    device.pairing_expires_at = None
    session.add(device)
    session.commit()
    session.refresh(device)

    mqtt_password = None
    try:
        mqtt_password = mqtt_admin.provision_device(device.id)
    except mqtt_admin.MqttAdminError:
        logger.warning("mqtt credential provisioning failed for device %s", device.id, exc_info=True)

    return device, token, mqtt_password


# user id -> timestamps of recent claim attempts. In-process and therefore per-worker: it
# survives neither a restart nor a second Railway replica. That is an accepted limit for a
# control whose job is to stop hand-typed guessing, not a distributed attacker; moving it to
# the database is a Phase 14 job if it ever matters.
_claim_attempts: dict[uuid.UUID, list[float]] = {}


def _record_claim_attempt(user_id: uuid.UUID) -> None:
    now = time.monotonic()
    recent = [t for t in _claim_attempts.get(user_id, []) if now - t < CLAIM_WINDOW_SECONDS]
    if len(recent) >= CLAIM_ATTEMPT_LIMIT:
        _claim_attempts[user_id] = recent
        raise TooManyClaimAttempts(str(user_id))
    recent.append(now)
    _claim_attempts[user_id] = recent


def claim(
    session: Session, *, user: User, pairing_code: str, name: str, location: str = ""
) -> Device:
    """Called by the **CMS**, authenticated: a human has typed the code off the screen."""
    _record_claim_attempt(user.id)

    code = pairing_code.strip().upper().replace(" ", "")
    device = session.exec(
        select(Device).where(Device.pairing_code == code, Device.account_id.is_(None))
    ).first()
    if device is None or (device.pairing_expires_at and device.pairing_expires_at < utcnow()):
        raise PairingNotFound(code)

    device.account_id = user.account_id
    device.created_by = user.id
    device.name = name.strip() or "Unnamed screen"
    device.location = location.strip()
    session.add(device)

    # A manager who claims a screen must be able to reach it afterwards; without this they
    # would pair a device and immediately lose sight of it.
    if user.role == UserRole.MANAGER:
        session.add(DeviceAccess(user_id=user.id, device_id=device.id))

    session.commit()
    session.refresh(device)
    return device


def update(
    session: Session,
    *,
    user: User,
    device: Device,
    name: str | None = None,
    location: str | None = None,
    orientation: DeviceOrientation | None = None,
    timezone: str | None = None,
    playlist_id: uuid.UUID | None = None,
    clear_playlist: bool = False,
) -> Device:
    if timezone is not None:
        # Rejected here rather than silently falling back at resolve time: a typo'd zone
        # would otherwise put every schedule on this screen an unknown number of hours out,
        # with nothing anywhere saying so.
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise InvalidTimezone(timezone) from None
        device.timezone = timezone
    if name is not None:
        device.name = name.strip() or device.name
    if location is not None:
        device.location = location.strip()
    if orientation is not None:
        device.orientation = orientation
    if clear_playlist:
        device.playlist_id = None
    elif playlist_id is not None:
        playlist = session.get(Playlist, playlist_id)
        # Same account only — otherwise assigning a playlist would leak whether one exists.
        if playlist is None or playlist.account_id != user.account_id:
            raise InvalidPlaylist(str(playlist_id))
        device.playlist_id = playlist_id
    session.add(device)
    session.commit()
    session.refresh(device)

    # Best-effort nudge so a screen picks this up now instead of on its next poll (up to
    # 30s away). Computed from the row that's now committed, so a screen that acts on it
    # sees exactly what a manifest fetch would give it — never a signal that races ahead of
    # the data behind it.
    mqtt.notify_manifest_changed(
        device_id=device.id,
        version=device_sync.compute_version(session, device),
    )
    return device


def unpair(session: Session, *, device: Device) -> Device:
    """Revoke the token and send the screen back to showing a pairing code.

    The fix for a stolen or re-sited device: the row, its name and its playlist assignment
    survive, so re-pairing the same hardware does not mean setting it up again.
    """
    settings = get_settings()
    device.token_hash = None
    device.paired_at = None
    device.pairing_code = _new_code(session)
    device.poll_token = secrets.token_urlsafe(32)
    device.pairing_expires_at = utcnow() + timedelta(seconds=settings.pairing_code_ttl_seconds)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def remove(session: Session, *, device: Device) -> None:
    session.exec(delete(DeviceAccess).where(DeviceAccess.device_id == device.id))
    session.exec(delete(Device).where(Device.id == device.id))
    session.commit()


def authenticate(session: Session, *, bearer: str) -> Device:
    """Resolve a device from its bearer token, or raise.

    Looked up by hash on an indexed unique column, so this is a single index probe and needs
    no constant-time compare — there is no per-character timing to leak.
    """
    device = session.exec(
        select(Device).where(Device.token_hash == hash_token(bearer))
    ).first()
    if device is None or device.account_id is None:
        raise DeviceNotFound("invalid device token")
    return device


def list_devices(session: Session, *, user: User) -> list[Device]:
    """Claimed devices in the account, scoped to what this user may reach.

    An owner sees every device in the account without a grant row; a manager sees exactly
    what they were granted. Unclaimed devices — the ones sitting on a pairing code with no
    `account_id` yet — belong to nobody and appear for no one.
    """
    statement = select(Device).where(
        Device.account_id == user.account_id, Device.account_id.is_not(None)
    )
    if user.role == UserRole.MANAGER:
        statement = statement.join(
            DeviceAccess,
            (DeviceAccess.device_id == Device.id) & (DeviceAccess.user_id == user.id),
        )
    return list(session.exec(statement.order_by(Device.name)).all())


def account_devices(session: Session, *, account_id: uuid.UUID) -> list[Device]:
    """Every claimed device in an account, unscoped. Owner-only callers."""
    return list(
        session.exec(
            select(Device).where(Device.account_id == account_id).order_by(Device.name)
        ).all()
    )
