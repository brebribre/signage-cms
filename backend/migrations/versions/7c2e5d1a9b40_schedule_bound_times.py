"""schedule bound times

Revision ID: 7c2e5d1a9b40
Revises: e1974030643c
Create Date: 2026-09-14 18:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '7c2e5d1a9b40'
down_revision: str | None = 'e1974030643c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('schedules', sa.Column('start_time', sa.Time(), nullable=True))
    op.add_column('schedules', sa.Column('end_time', sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column('schedules', 'end_time')
    op.drop_column('schedules', 'start_time')
