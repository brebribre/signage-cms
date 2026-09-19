"""device owner flag

Revision ID: a7c3e5f9b2d4
Revises: f2a6d8c4b1e7
Create Date: 2026-09-19 14:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e5f9b2d4'
down_revision: str | None = 'f2a6d8c4b1e7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Whether the player runs as Android Device Owner — see Device.device_owner.
    op.add_column('devices', sa.Column('device_owner', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'device_owner')
