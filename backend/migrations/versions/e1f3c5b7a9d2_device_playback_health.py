"""device playback health

Revision ID: e1f3c5b7a9d2
Revises: d9e2b7a4c1f5
Create Date: 2026-09-17 18:21:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'e1f3c5b7a9d2'
down_revision: str | None = 'd9e2b7a4c1f5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Playback health from each heartbeat — see Device.playback_dropped_frames.
    op.add_column('devices', sa.Column('playback_dropped_frames', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('playback_decoder', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column('devices', sa.Column('download_bytes_per_second', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('playback_reported_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'playback_reported_at')
    op.drop_column('devices', 'download_bytes_per_second')
    op.drop_column('devices', 'playback_decoder')
    op.drop_column('devices', 'playback_dropped_frames')
