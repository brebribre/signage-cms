"""account kinds

Revision ID: b2c4d6e8f0a1
Revises: a7c9e1b3d5f7
Create Date: 2026-09-22 15:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c4d6e8f0a1'
down_revision: str | None = 'a7c9e1b3d5f7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = ('owner', 'admin', 'client')


def upgrade() -> None:
    # Every existing account is a client until said otherwise — see models/account.py::AccountKind.
    op.add_column(
        'accounts',
        sa.Column(
            'kind',
            sa.Enum(*KINDS, name='accountkind', native_enum=False),
            nullable=False,
            server_default='client',
        ),
    )
    # Whoever held the old per-user admin flag keeps their access: their account becomes an
    # Admin account. Which one of them is *the* Owner account is a decision, not a fact in the
    # data, so it is made by hand afterwards with scripts/set_account_kind.py.
    op.execute(
        "UPDATE accounts SET kind = 'admin' "
        "WHERE id IN (SELECT account_id FROM users WHERE is_platform_admin)"
    )
    op.drop_column('users', 'is_platform_admin')


def downgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # The flag goes back on the main user of every staff account — the same people who could
    # sign in to the monitoring app under the kinds.
    op.execute(
        "UPDATE users SET is_platform_admin = true "
        "WHERE role = 'owner' AND account_id IN (SELECT id FROM accounts WHERE kind IN ('owner', 'admin'))"
    )
    op.drop_column('accounts', 'kind')
