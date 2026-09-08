"""Shared helpers for table definitions."""

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum


def utcnow() -> datetime:
    return datetime.now(UTC)


def tz_column(**kwargs) -> Column:
    """A TIMESTAMPTZ column.

    SQLModel maps a plain `datetime` to TIMESTAMP WITHOUT TIME ZONE, which would
    silently drop the offset. Every datetime in the schema goes through here instead.
    """
    return Column(DateTime(timezone=True), **kwargs)


def enum_column(enum_cls: type[PyEnum], **kwargs) -> Column:
    """A VARCHAR column constrained to an enum's *values*.

    SQLModel's default maps a Python enum to a **native Postgres ENUM type storing member
    names**, which is wrong here twice over:

    - The database would hold 'OWNER' while the API speaks 'owner' — two vocabularies for
      one concept, and `psql` shows the one nobody writes.
    - Adding a value later needs `ALTER TYPE ... ADD VALUE`, which cannot run inside a
      transaction block, and Alembic runs migrations in one.

    `native_enum=False` gives VARCHAR plus a CHECK constraint instead, and
    `values_callable` stores the value rather than the name. Adding a role becomes a code
    change and a one-line constraint migration.
    """
    return Column(
        SAEnum(enum_cls, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        **kwargs,
    )
