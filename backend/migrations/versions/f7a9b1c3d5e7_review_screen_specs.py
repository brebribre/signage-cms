"""content_reviews.screen_specs: the screens a review reaches, as they were when it was sent

Revision ID: f7a9b1c3d5e7
Revises: e5f7a9b1c3d5
Create Date: 2026-09-26 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a9b1c3d5e7'
down_revision: str | None = 'e5f7a9b1c3d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Reviews sent before this have none: the CMS falls back to matching their screen names
    # against the screens that still exist.
    op.add_column('content_reviews', sa.Column('screen_specs', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('content_reviews', 'screen_specs')
