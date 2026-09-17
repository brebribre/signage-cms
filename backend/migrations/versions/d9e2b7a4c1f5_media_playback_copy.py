"""media playback copy

Revision ID: d9e2b7a4c1f5
Revises: c4a8f1d2e6b3
Create Date: 2026-09-17 18:20:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'd9e2b7a4c1f5'
down_revision: str | None = 'c4a8f1d2e6b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The normalised copy screens play — see Media.playback_key.
    op.add_column('media', sa.Column('playback_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('media', sa.Column('playback_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('media', sa.Column('playback_checksum', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('media', sa.Column('playback_reencoded', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('media', sa.Column('playback_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.drop_column('media', 'playback_error')
    op.drop_column('media', 'playback_reencoded')
    op.drop_column('media', 'playback_checksum')
    op.drop_column('media', 'playback_size_bytes')
    op.drop_column('media', 'playback_key')
