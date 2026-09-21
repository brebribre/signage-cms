"""live control: hold a screen on one scene

Revision ID: a7c9e1b3d5f7
Revises: f3b5d7e9a1c3
Create Date: 2026-09-21 16:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c9e1b3d5f7'
down_revision: str | None = 'f3b5d7e9a1c3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Both nullable, no default: every existing screen keeps running its programme.
    op.add_column('devices', sa.Column('live_slot_id', sa.Uuid(), nullable=True))
    op.add_column('devices', sa.Column('live_started_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'devices_live_slot_id_fkey', 'devices', 'playlist_items', ['live_slot_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('devices_live_slot_id_fkey', 'devices', type_='foreignkey')
    op.drop_column('devices', 'live_started_at')
    op.drop_column('devices', 'live_slot_id')
