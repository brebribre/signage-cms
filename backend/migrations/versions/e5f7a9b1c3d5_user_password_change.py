"""user must_change_password and session_version

Revision ID: e5f7a9b1c3d5
Revises: d4e6f8a0b2c4
Create Date: 2026-09-25 21:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f7a9b1c3d5'
down_revision: str | None = 'd4e6f8a0b2c4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nobody is made to change a password by this migration: existing users chose theirs, or
    # were handed one before this existed, and are left alone. Version 1 is what every cookie
    # issued before this carries, so nobody is signed out either.
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('session_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('users', 'session_version')
    op.drop_column('users', 'must_change_password')
