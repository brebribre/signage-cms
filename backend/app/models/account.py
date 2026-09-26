import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from app.models.base import enum_column, tz_column, utcnow


class AccountKind(StrEnum):
    """What sort of account this is — which decides who can use the monitoring app and what
    they may do there. See services/admin.py for the rules in one table.

    - OWNER: Marien itself. Exactly one. No limits, ever. Issues admin and client accounts.
    - ADMIN: a technician's own account. Signs in to the monitoring app too, but may only issue
      client accounts and change client limits.
    - CLIENT: a customer. The CMS only — never the monitoring app.

    An account's kind is about the *account*: its main user (UserRole.OWNER) is the one who
    inherits the monitoring access, and a sub account (UserRole.MANAGER) never does, whatever
    the account. So a technician's sub accounts are ordinary CMS users like anyone's.
    """

    OWNER = "owner"
    ADMIN = "admin"
    CLIENT = "client"


class Account(SQLModel, table=True):
    """The tenant. Media, playlists and devices belong to an account, never to a user.

    This is what makes subusers safe: a manager's upload has to stay visible to the owner
    and to their colleagues, so deleting the person must not take the content with them.
    """

    __tablename__ = "accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    # Client by default: an account only becomes owner or admin by being issued as one from the
    # monitoring app, or by scripts/set_account_kind.py. No customer-facing route can change it.
    kind: AccountKind = Field(
        default=AccountKind.CLIENT,
        sa_column=enum_column(AccountKind, nullable=False, server_default="client"),
    )
    # Bytes. None means unlimited, which is the default — a quota that appears without anyone
    # setting it would block uploads for reasons nobody chose.
    storage_quota_bytes: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    # How many screens may be paired. None means unlimited, same rule as the storage quota.
    # Set from the monitoring app (api/routes/admin.py) — never by the account itself.
    max_screens: int | None = Field(default=None)
    # IANA name every newly paired screen starts in (Settings → General). A default, not a
    # constraint: each screen's own timezone is still its own, and changing this moves no screen
    # already paired. UTC until an owner chooses — never a guess at their locale.
    default_timezone: str = Field(default="UTC", sa_column_kwargs={"server_default": "UTC"})
    # The moment the account stops working. None means it never does, which is the default —
    # like the limits above, an end that nobody chose would lock people out for no reason.
    # Set from the monitoring app, under the same rule as the limits (services/admin.py), so the
    # owner account never has one. What "stops working" means is `is_expired` below.
    expires_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))

    def is_expired(self, now: datetime | None = None) -> bool:
        """Past its end date. An expired account can still sign in and look, but the CMS
        refuses every change (api/deps.py::get_current_user) and its main user loses the
        monitoring app (services/admin.py::is_staff). Its screens keep playing what they have.
        See ACCOUNTS.md, "Accounts that expire"."""
        return self.expires_at is not None and self.expires_at <= (now or utcnow())
