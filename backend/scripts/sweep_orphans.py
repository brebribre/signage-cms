"""Find R2 objects with no media row behind them, and optionally delete them.

These come from the Phase 5 delete order: the database row is removed first and the object
second, deliberately, because a failed object delete leaves an orphan (costs storage) while a
failed row delete would leave a broken tile in the library (costs correctness). This is the
script that collects the resulting debris.

**Dry run by default.** It prints what it would remove and exits; deleting requires --delete.
A sweep that deletes on its first run is one typo away from erasing a media library.

    .venv/bin/python -m scripts.sweep_orphans
    .venv/bin/python -m scripts.sweep_orphans --delete
"""

import argparse
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.infra import storage
from app.infra.db import engine
from app.models import Media

# Objects younger than this are left alone whatever the database says: an upload in flight has
# a presigned URL and no `ready` row yet, and deleting it mid-PUT would look to the user like
# a random upload failure.
MIN_AGE_HOURS = 6


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="actually remove the objects")
    parser.add_argument("--min-age-hours", type=int, default=MIN_AGE_HOURS)
    args = parser.parse_args()

    settings = get_settings()
    client = storage._client()

    with Session(engine) as session:
        known: set[str] = set()
        for m in session.exec(select(Media)).all():
            known.add(m.storage_key)
            if m.thumbnail_key:
                known.add(m.thumbnail_key)

    cutoff = datetime.now(UTC) - timedelta(hours=args.min_age_hours)
    orphans: list[tuple[str, int]] = []
    total_objects = 0
    skipped_young = 0

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.r2_bucket, Prefix="media/"):
        for obj in page.get("Contents", []):
            total_objects += 1
            if obj["Key"] in known:
                continue
            if obj["LastModified"] > cutoff:
                skipped_young += 1
                continue
            orphans.append((obj["Key"], obj["Size"]))

    wasted = sum(size for _, size in orphans)
    print(f"\n  bucket        {settings.r2_bucket}")
    print(f"  objects       {total_objects}")
    print(f"  tracked       {len(known)} keys referenced by media rows")
    print(f"  too recent    {skipped_young} (younger than {args.min_age_hours}h, left alone)")
    print(f"  orphans       {len(orphans)} — {wasted / 1_048_576:.1f} MB\n")

    for key, size in orphans[:20]:
        print(f"    {key}  ({size / 1024:.0f} KB)")
    if len(orphans) > 20:
        print(f"    … and {len(orphans) - 20} more")

    if not orphans:
        print("  Nothing to do.\n")
        return

    if not args.delete:
        print("\n  Dry run. Re-run with --delete to remove them.\n")
        return

    for key, _ in orphans:
        storage.delete_object(key)
    print(f"\n  Deleted {len(orphans)} objects, reclaiming {wasted / 1_048_576:.1f} MB.\n")


if __name__ == "__main__":
    main()
