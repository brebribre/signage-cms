"""Delete an account and everything in it, named by the username of one of its people.

There is no API for this, on purpose: it is not undoable, and it is not something an account
holder or a technician should be able to do to a customer. Run it by hand, against the real
database (see DEPLOY.md for how that works on Railway).

    .venv/bin/python -m scripts.delete_account --username someone           # dry run
    .venv/bin/python -m scripts.delete_account --username someone --yes     # actually delete

Without `--yes` it only prints what would go. Nothing is written.

**Order matters.** `playlist_item_elements.media_id` is ON DELETE RESTRICT, so a scene still
pointing at a file blocks that file's deletion. Deleting the account alone would let Postgres
cascade media and scenes in whatever order it likes and fail about half the time. So playlists
go first, which takes their items and scene elements with them, and only then does the account
go and cascade the rest.

**R2 is not touched here.** Deleting media rows leaves their objects in the bucket. Run
`scripts/sweep_orphans --delete` afterwards to reclaim them; this script says so when it
deleted any media.
"""

import argparse

from sqlmodel import Session, delete, func, select

from app.infra.db import engine
from app.models import (
    Account,
    AccountKind,
    Campaign,
    ContentReview,
    Device,
    Media,
    Playlist,
    Schedule,
    User,
)
from app.services import auth as auth_service

#: What the account holds — (singular, plural, table) — in the order it is counted and reported.
HOLDINGS = (
    ("screen", "screens", Device),
    ("media file", "media files", Media),
    ("playlist", "playlists", Playlist),
    ("campaign", "campaigns", Campaign),
    ("schedule", "schedules", Schedule),
    ("review", "reviews", ContentReview),
)


def count_text(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True, help="anyone in the account to delete")
    parser.add_argument("--yes", action="store_true", help="actually delete; without it, a dry run")
    args = parser.parse_args()

    with Session(engine) as session:
        user = auth_service.get_by_username(session, args.username)
        if user is None:
            raise SystemExit(f"\n  No user named {args.username!r}.\n")
        account = session.get(Account, user.account_id)

        if account.kind == AccountKind.OWNER:
            raise SystemExit(
                f"\n  {account.name!r} is the owner account. Deleting it would leave nobody who"
                f" can issue technicians. Make it an admin or client account first, if you really"
                f" mean to.\n"
            )

        users = session.exec(select(User).where(User.account_id == account.id)).all()
        counts = {
            (one, many): session.exec(
                select(func.count()).select_from(model).where(model.account_id == account.id)
            ).one()
            for one, many, model in HOLDINGS
        }

        print(f"\n  {account.name!r} — {account.kind} account, made {account.created_at:%d %b %Y}")
        print(f"  people   : {', '.join(f'{u.username} ({u.role})' for u in users) or 'nobody'}")
        held = [count_text(n, one, many) for (one, many), n in counts.items() if n]
        print("  holds    : " + (", ".join(held) or "nothing"))

        if not args.yes:
            print("\n  Dry run — nothing was deleted. Add --yes to go through with it.\n")
            return

        try:
            # Playlists first: their scene elements are what hold media back. This takes
            # playlist_items and playlist_item_elements with them, by cascade.
            session.exec(delete(Playlist).where(Playlist.account_id == account.id))
            session.flush()
            # Then the account. Users, screens, media, campaigns, schedules, reviews, events and
            # settings all cascade from it; the admin action log keeps its snapshot of the name
            # and simply loses the id, which is what makes the history outlive the account.
            session.exec(delete(Account).where(Account.id == account.id))
            session.commit()
        except Exception:
            session.rollback()
            print("\n  Something went wrong. Nothing was deleted.\n")
            raise

        print(f"\n  {account.name!r} is gone, with everything in it.")
        if counts[("media file", "media files")]:
            print("  Its files are still in R2 — run `python -m scripts.sweep_orphans --delete`"
                  " to reclaim them.")
        print()


if __name__ == "__main__":
    main()
