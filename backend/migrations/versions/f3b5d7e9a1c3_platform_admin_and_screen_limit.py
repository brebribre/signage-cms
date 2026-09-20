"""platform admin and screen limit

Revision ID: f3b5d7e9a1c3
Revises: e2a4c6b8d0f1
Create Date: 2026-09-20 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'f3b5d7e9a1c3'
down_revision: str | None = 'e2a4c6b8d0f1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no default: every existing account stays unlimited, exactly as it is today.
    # Nothing is enforced by this migration — see models/account.py.
    op.add_column('accounts', sa.Column('max_screens', sa.Integer(), nullable=True))

    # False for every existing user. The only way to set it is scripts/make_admin.py.
    op.add_column(
        'users',
        sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        'admin_actions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('admin_user_id', sa.Uuid(), nullable=True),
        sa.Column('account_id', sa.Uuid(), nullable=True),
        sa.Column('account_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('action', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('detail', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_admin_actions_account_id', 'admin_actions', ['account_id'])
    op.create_index('ix_admin_actions_admin_user_id', 'admin_actions', ['admin_user_id'])


def downgrade() -> None:
    op.drop_index('ix_admin_actions_admin_user_id', table_name='admin_actions')
    op.drop_index('ix_admin_actions_account_id', table_name='admin_actions')
    op.drop_table('admin_actions')
    op.drop_column('users', 'is_platform_admin')
    op.drop_column('accounts', 'max_screens')
