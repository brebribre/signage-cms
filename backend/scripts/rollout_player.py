"""Roll a published player build out to every screen — the command-line counterpart of the
Software updates tab the CMS used to have.

Usage (from backend/, against the local DB; in production via `railway ssh --service backend`):
    .venv/bin/python -m scripts.rollout_player 1.3.7                # now
    .venv/bin/python -m scripts.rollout_player 1.3.7 --at 2026-10-01T09:00:00+07:00
    .venv/bin/python -m scripts.rollout_player --list               # what is live and what is queued

Owner-only, exactly like the endpoint it calls: --user names the owner the rollout is
recorded against (default: brebribre).
"""

import argparse
from datetime import datetime

from sqlmodel import Session, select

from app.infra.db import engine
from app.models import User, UserRole
from app.services import player_rollouts
from app.services.player_rollouts import UnknownRelease


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", nargs="?", help="a version publish_player_apk.py uploaded, e.g. 1.3.7")
    parser.add_argument("--at", help="ISO-8601 moment to start; omitted means now")
    parser.add_argument("--user", default="brebribre", help="owner username to record the rollout under")
    parser.add_argument("--list", action="store_true", help="show rollouts instead of scheduling one")
    args = parser.parse_args()

    with Session(engine) as session:
        if args.list or not args.version:
            active = player_rollouts.active_rollout(session)
            for r in player_rollouts.list_rollouts(session):
                mark = "  ← live" if active and r.id == active.id else ""
                print(f"{r.version:>10}  scheduled {r.scheduled_at:%Y-%m-%d %H:%M %Z}{mark}")
            if not args.version:
                return

        user = session.exec(select(User).where(User.username == args.user)).first()
        if user is None or user.role != UserRole.OWNER:
            raise SystemExit(f"{args.user!r} is not an owner")
        scheduled_at = datetime.fromisoformat(args.at) if args.at else None
        try:
            rollout = player_rollouts.schedule(session, user=user, version=args.version, scheduled_at=scheduled_at)
        except UnknownRelease:
            raise SystemExit(f"no uploaded build called {args.version!r} — publish it first") from None
        when = "now" if scheduled_at is None else f"at {rollout.scheduled_at:%Y-%m-%d %H:%M %Z}"
        print(f"rolling out {rollout.version} {when}; screens are told right away (or on their next check-in)")


if __name__ == "__main__":
    main()
