"""Delete event rows past their retention window.

`play_events` is the table that grows without bound — a screen showing a 10-second image
generates roughly 8,600 rows a day, so a handful of screens fills a small Postgres volume in
months. Retention is a policy, not a suggestion; this is what enforces it.

Intended as a scheduled job (Railway cron, or anything that can run a command daily).

    .venv/bin/python -m scripts.prune_events
    .venv/bin/python -m scripts.prune_events --dry-run
"""

import argparse
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.infra.db import engine
from app.models import DeviceEvent, PlayEvent
from app.services import operations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = datetime.now(UTC)
    play_cutoff = now - timedelta(days=operations.PLAY_EVENT_RETENTION_DAYS)
    event_cutoff = now - timedelta(days=operations.DEVICE_EVENT_RETENTION_DAYS)

    with Session(engine) as session:
        plays_total = session.exec(select(func.count(PlayEvent.id))).one()
        events_total = session.exec(select(func.count(DeviceEvent.id))).one()
        plays_old = session.exec(
            select(func.count(PlayEvent.id)).where(PlayEvent.started_at < play_cutoff)
        ).one()
        events_old = session.exec(
            select(func.count(DeviceEvent.id)).where(DeviceEvent.created_at < event_cutoff)
        ).one()

        print(f"\n  play_events    {plays_total} rows, {plays_old} older than "
              f"{operations.PLAY_EVENT_RETENTION_DAYS}d")
        print(f"  device_events  {events_total} rows, {events_old} older than "
              f"{operations.DEVICE_EVENT_RETENTION_DAYS}d")

        if args.dry_run:
            print("\n  Dry run — nothing deleted.\n")
            return

        plays, events = operations.prune(session, now=now)
        print(f"\n  Deleted {plays} play events and {events} device events.\n")


if __name__ == "__main__":
    main()
