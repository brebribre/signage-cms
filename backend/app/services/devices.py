"""Devices.

Phase 8 adds the pairing handshake, claiming and unpairing. This module currently holds only
what Phase 9b needs: listing the screens a user may reach, so grants can be assigned against
something real.
"""

import uuid

from sqlmodel import Session, select

from app.models import Device, DeviceAccess, User, UserRole


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
