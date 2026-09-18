"""orientation in degrees

Revision ID: f2a6d8c4b1e7
Revises: e1f3c5b7a9d2
Create Date: 2026-09-18 09:40:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = 'f2a6d8c4b1e7'
down_revision: str | None = 'e1f3c5b7a9d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The column is a plain VARCHAR (see models/base.py::enum_column), so only the values move:
    # landscape is the panel's own orientation (0), portrait the clockwise quarter turn (90).
    op.execute("UPDATE devices SET orientation = '0' WHERE orientation = 'landscape'")
    op.execute("UPDATE devices SET orientation = '90' WHERE orientation = 'portrait'")


def downgrade() -> None:
    op.execute("UPDATE devices SET orientation = 'landscape' WHERE orientation IN ('0', '180')")
    op.execute("UPDATE devices SET orientation = 'portrait' WHERE orientation IN ('90', '270')")
