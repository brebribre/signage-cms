"""text elements

Revision ID: c9e1a3b5d7f2
Revises: b8d4f6a1c3e5
Create Date: 2026-09-19 17:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'c9e1a3b5d7f2'
down_revision: str | None = 'b8d4f6a1c3e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ONE_SOURCE = (
    "(CASE WHEN media_id IS NULL THEN 0 ELSE 1 END)"
    " + (CASE WHEN web_url IS NULL THEN 0 ELSE 1 END)"
    " + (CASE WHEN text IS NULL THEN 0 ELSE 1 END) = 1"
)


def upgrade() -> None:
    # A text element: typed in the scene editor, drawn by the players — see
    # models/playlist.py PlaylistItemElement.text.
    op.add_column('playlist_item_elements', sa.Column('text', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('playlist_item_elements', sa.Column('text_style', sa.JSON(), nullable=True))
    op.drop_constraint('ck_element_media_or_web_url', 'playlist_item_elements', type_='check')
    op.create_check_constraint('ck_element_one_source', 'playlist_item_elements', ONE_SOURCE)


def downgrade() -> None:
    op.execute("DELETE FROM playlist_item_elements WHERE text IS NOT NULL")
    op.drop_constraint('ck_element_one_source', 'playlist_item_elements', type_='check')
    op.create_check_constraint(
        'ck_element_media_or_web_url', 'playlist_item_elements', "(media_id IS NULL) <> (web_url IS NULL)"
    )
    op.drop_column('playlist_item_elements', 'text_style')
    op.drop_column('playlist_item_elements', 'text')
