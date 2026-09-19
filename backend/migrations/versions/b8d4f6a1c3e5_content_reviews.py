"""content reviews

Revision ID: b8d4f6a1c3e5
Revises: a7c3e5f9b2d4
Create Date: 2026-09-19 15:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'b8d4f6a1c3e5'
down_revision: str | None = 'a7c3e5f9b2d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    'playlist_items', 'playlist_shuffle', 'campaign_create', 'campaign_update',
    'campaign_delete', 'schedule_create', 'schedule_update', 'schedule_delete',
    'device_playlist',
)
STATUSES = ('pending', 'approved', 'rejected', 'withdrawn')


def upgrade() -> None:
    # A manager's change to what screens show, waiting for the owner — see models/review.py.
    op.create_table(
        'content_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('requested_by', sa.Uuid(), nullable=True),
        sa.Column('requested_by_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('kind', sa.Enum(*KINDS, name='reviewkind', native_enum=False), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=True),
        sa.Column('target_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('summary', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('screens', sa.JSON(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum(*STATUSES, name='reviewstatus', native_enum=False), nullable=False),
        sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_reviews_account_id', 'content_reviews', ['account_id'])
    op.create_index('ix_content_reviews_status', 'content_reviews', ['status'])
    op.create_index('ix_content_reviews_created_at', 'content_reviews', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_content_reviews_created_at', table_name='content_reviews')
    op.drop_index('ix_content_reviews_status', table_name='content_reviews')
    op.drop_index('ix_content_reviews_account_id', table_name='content_reviews')
    op.drop_table('content_reviews')
