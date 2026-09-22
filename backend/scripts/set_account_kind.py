"""Set what kind of account an account is — owner, admin or client — named by the username of
one of its people.

The monitoring app issues admin and client accounts itself, so day to day this script is not
needed. It exists for the two things no API does, on purpose: making *the* owner account, and
taking staff access away from an account that has it. Run it by hand, against the real
database (see DEPLOY.md for how that works on Railway).

    .venv/bin/python -m scripts.set_account_kind --username you --kind owner
    .venv/bin/python -m scripts.set_account_kind --username tech --kind admin
    .venv/bin/python -m scripts.set_account_kind --username tech --kind client   # access taken away

Only one account can be the owner account. To move it, make the current one admin or client
first. The owner account has no limits, so making an account the owner clears any it had.
"""

import argparse

from sqlmodel import Session, select

from app.infra.db import engine
from app.models import Account, AccountKind, User, UserRole
from app.services import auth as auth_service


def article(kind: AccountKind) -> str:
    """"an admin account", "a client account" — the message reads as a sentence either way."""
    return "an" if str(kind)[0] in "aeiou" else "a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True, help="anyone in the account")
    parser.add_argument("--kind", required=True, choices=[k.value for k in AccountKind])
    args = parser.parse_args()
    wanted = AccountKind(args.kind)

    with Session(engine) as session:
        user = auth_service.get_by_username(session, args.username)
        if user is None:
            raise SystemExit(f"\n  No user named {args.username!r}.\n")
        account = session.get(Account, user.account_id)

        if account.kind == wanted:
            print(f"\n  {account.name!r} is already {article(wanted)} {wanted} account. Nothing changed.\n")
            return

        if wanted == AccountKind.OWNER:
            other = session.exec(
                select(Account).where(Account.kind == AccountKind.OWNER, Account.id != account.id)
            ).first()
            if other is not None:
                raise SystemExit(
                    f"\n  {other.name!r} is already the owner account. There can be only one —"
                    f" make it admin or client first.\n"
                )
            # The owner account has no limits; whatever it had as an admin or client goes.
            account.max_screens = None
            account.storage_quota_bytes = None

        was = account.kind
        account.kind = wanted
        session.add(account)
        session.commit()
        print(f"\n  {account.name!r} is now {article(wanted)} {wanted} account (was {was}).")

        # Who that gives the monitoring app to — the account's main users, never sub accounts.
        mains = session.exec(
            select(User).where(User.account_id == account.id, User.role == UserRole.OWNER)
        ).all()
        names = ", ".join(u.username for u in mains) or "nobody (the account has no owner)"
        if wanted == AccountKind.CLIENT:
            print(f"  {names} can no longer sign in to the monitoring app.\n")
        else:
            print(f"  {names} can sign in to the monitoring app as {wanted}.\n")


if __name__ == "__main__":
    main()
