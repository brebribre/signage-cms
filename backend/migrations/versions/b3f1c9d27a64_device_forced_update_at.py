"""device forced update at

Revision ID: b3f1c9d27a64
Revises: 7c2e5d1a9b40
Create Date: 2026-09-15 00:55:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1c9d27a64'
down_revision: str | None = '7c2e5d1a9b40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('forced_update_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'forced_update_at')
