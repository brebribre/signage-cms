"""device disconnect handshake

Revision ID: c4a8f1d2e6b3
Revises: b7d1e4c2a9f0
Create Date: 2026-09-17 17:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c4a8f1d2e6b3'
down_revision: str | None = 'b7d1e4c2a9f0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Set when "Disconnect" is clicked; the row is deleted once the screen has been told.
    op.add_column('devices', sa.Column('disconnect_requested_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'disconnect_requested_at')
