"""device detected_orientation

Revision ID: d4e6f8a0b2c4
Revises: c3d5e7f9a1b2
Create Date: 2026-09-25 18:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e6f8a0b2c4'
down_revision: str | None = 'c3d5e7f9a1b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable, no default: every existing screen simply "couldn't tell", which changes nothing —
    # it only matters while a screen is waiting to be paired.
    op.add_column(
        'devices',
        # The same plain VARCHAR `orientation` is (models/base.py::enum_column).
        sa.Column('detected_orientation', sa.String(length=9), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('devices', 'detected_orientation')
