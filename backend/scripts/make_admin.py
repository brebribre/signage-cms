"""Make an existing user a platform admin — or take it away again.

This is the only way the flag gets set. No API can, on purpose: an account owner must never
be able to promote themselves to seeing every customer's data. Run it once, by hand, against
the real database.

    .venv/bin/python -m scripts.make_admin --username you
    .venv/bin/python -m scripts.make_admin --username you --revoke
"""

import argparse

from sqlmodel import Session

from app.infra.db import engine
from app.services import auth as auth_service


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--revoke", action="store_true", help="remove admin instead of granting it")
    args = parser.parse_args()

    with Session(engine) as session:
        user = auth_service.get_by_username(session, args.username)
        if user is None:
            raise SystemExit(f"\n  No user named {args.username!r}.\n")

        wanted = not args.revoke
        if user.is_platform_admin == wanted:
            state = "already a platform admin" if wanted else "already not a platform admin"
            print(f"\n  {user.username} is {state}. Nothing changed.\n")
            return

        user.is_platform_admin = wanted
        session.add(user)
        session.commit()
        verb = "is now" if wanted else "is no longer"
        print(f"\n  {user.username} {verb} a platform admin.\n")


if __name__ == "__main__":
    main()
