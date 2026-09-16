"""playlist element web url

Revision ID: c4e8a1d2f7b3
Revises: b3f1c9d27a64
Create Date: 2026-09-16 00:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e8a1d2f7b3'
down_revision: str | None = 'b3f1c9d27a64'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # An element is now a library file *or* a website: media_id becomes optional, and exactly
    # one of the two must be set.
    op.alter_column('playlist_item_elements', 'media_id', existing_type=sa.Uuid(), nullable=True)
    op.add_column('playlist_item_elements', sa.Column('web_url', sa.String(), nullable=True))
    op.create_check_constraint(
        'ck_element_media_or_web_url',
        'playlist_item_elements',
        '(media_id IS NULL) <> (web_url IS NULL)',
    )


def downgrade() -> None:
    # Website elements have nowhere to go in the old schema.
    op.execute('DELETE FROM playlist_item_elements WHERE media_id IS NULL')
    op.drop_constraint('ck_element_media_or_web_url', 'playlist_item_elements', type_='check')
    op.drop_column('playlist_item_elements', 'web_url')
    op.alter_column('playlist_item_elements', 'media_id', existing_type=sa.Uuid(), nullable=False)
