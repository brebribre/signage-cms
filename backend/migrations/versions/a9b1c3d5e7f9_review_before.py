"""content_reviews.before: what the change replaces, as it was when the review was sent

Revision ID: a9b1c3d5e7f9
Revises: f7a9b1c3d5e7
Create Date: 2026-09-26 11:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a9b1c3d5e7f9'
down_revision: str | None = 'f7a9b1c3d5e7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Null on reviews sent before this: the CMS then compares against what is saved now.
    op.add_column('content_reviews', sa.Column('before', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('content_reviews', 'before')
