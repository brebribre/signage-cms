"""review playlists

Revision ID: d1f3b5c7e9a2
Revises: c9e1a3b5d7f2
Create Date: 2026-09-19 18:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd1f3b5c7e9a2'
down_revision: str | None = 'c9e1a3b5d7f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Playlist names a review touches — see models/review.py ContentReview.playlists.
    op.add_column('content_reviews', sa.Column('playlists', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('content_reviews', 'playlists')
