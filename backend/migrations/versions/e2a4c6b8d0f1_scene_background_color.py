"""scene background colour

Revision ID: e2a4c6b8d0f1
Revises: d1f3b5c7e9a2
Create Date: 2026-09-19 19:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'e2a4c6b8d0f1'
down_revision: str | None = 'd1f3b5c7e9a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A solid scene background — see models/playlist.py PlaylistItem.background_color. The
    # `background` column is a plain VARCHAR (enum_column), so the new "color" value needs no
    # schema change of its own.
    op.add_column('playlist_items', sa.Column('background_color', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.execute("UPDATE playlist_items SET background = 'black' WHERE background = 'color'")
    op.drop_column('playlist_items', 'background_color')
