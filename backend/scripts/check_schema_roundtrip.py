"""Phase 2 checkpoint: every table round-trips, and the FK rules hold.

The three delete behaviours below are the ones the whole subuser model rests on, so they
are proven here rather than assumed from the model definitions.

Run with:  .venv/bin/python -m scripts.check_schema_roundtrip
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app.infra.db import engine
from app.models import (
    Account,
    Device,
    DeviceAccess,
    Media,
    MediaKind,
    MediaStatus,
    Playlist,
    PlaylistItem,
    User,
    UserRole,
)

PREFIX = "check-schema"
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  ✗ {label} FAILED {detail}")


def cleanup(session: Session) -> None:
    # Unclaimed devices belong to no account, so the account sweep below cannot reach them.
    session.exec(delete(Device).where(Device.poll_token.startswith(PREFIX)))
    session.commit()
    accounts = session.exec(select(Account).where(Account.name.startswith(PREFIX))).all()
    ids = [a.id for a in accounts]
    if ids:
        # devices.account_id is ON DELETE CASCADE, but playlist_items -> media is RESTRICT,
        # so items must go before the account takes the media with it.
        pls = session.exec(select(Playlist).where(Playlist.account_id.in_(ids))).all()
        if pls:
            session.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id.in_([p.id for p in pls])))
        session.exec(delete(Account).where(Account.id.in_(ids)))
        session.commit()


def main() -> None:
    with Session(engine) as s:
        cleanup(s)

        print("\naccount + users")
        account = Account(name=f"{PREFIX} account")
        s.add(account)
        s.commit()

        owner = User(
            account_id=account.id,
            username=f"{PREFIX}-owner",
            email=f"{PREFIX}-owner@example.com",
            password_hash="x",
            display_name="Owner",
            role=UserRole.OWNER,
        )
        s.add(owner)
        s.commit()

        manager = User(
            account_id=account.id,
            username=f"{PREFIX}-manager",
            email=None,  # a subuser need not have one
            password_hash="x",
            display_name="Manager",
            role=UserRole.MANAGER,
            created_by=owner.id,
        )
        s.add(manager)
        s.commit()
        check("account and two users round-trip", manager.account_id == account.id)
        check("a manager may have no email", manager.email is None)

        # Postgres allows many NULLs under a unique index; a second emailless user must work.
        second = User(
            account_id=account.id,
            username=f"{PREFIX}-manager2",
            email=None,
            password_hash="x",
            display_name="Manager 2",
            role=UserRole.MANAGER,
        )
        s.add(second)
        s.commit()
        check("two users can both have NULL email", second.id is not None)

        s.add(User(
            account_id=account.id, username=f"{PREFIX}-owner", password_hash="x",
            display_name="Dupe", role=UserRole.MANAGER,
        ))
        try:
            s.commit()
            check("duplicate username rejected", False, "commit succeeded")
        except IntegrityError:
            s.rollback()
            check("duplicate username rejected", True)

        print("\nstorage form")
        stored_role = s.exec(
            text("select role from users where username = :u").bindparams(u=owner.username)
        ).one()[0]
        check(
            "enums are stored as their lowercase VALUE, not the member name",
            stored_role == "owner",
            f"database holds {stored_role!r}",
        )
        check("role reads back as the enum", owner.role is UserRole.OWNER)

        print("\ntimestamps")
        check(
            "created_at is timezone-aware",
            account.created_at.tzinfo is not None,
            str(account.created_at.tzinfo),
        )

        print("\nmedia + playlist ordering")
        media = []
        for i in range(3):
            m = Media(
                account_id=account.id, created_by=manager.id,
                filename=f"clip{i}.mp4", kind=MediaKind.VIDEO, mime_type="video/mp4",
                size_bytes=48_210_233, width=1920, height=1080, duration_seconds=30.0,
                storage_key=f"media/{account.id}/{uuid.uuid4()}/clip{i}.mp4",
                checksum=f"{PREFIX}-sha-{i}", status=MediaStatus.READY,
            )
            s.add(m)
            media.append(m)
        s.commit()

        playlist = Playlist(account_id=account.id, created_by=manager.id, name=f"{PREFIX} loop")
        s.add(playlist)
        s.commit()
        for pos, m in enumerate(media):
            s.add(PlaylistItem(playlist_id=playlist.id, media_id=m.id, position=pos, duration_seconds=30))
        s.commit()

        got = s.exec(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id).order_by(PlaylistItem.position)
        ).all()
        check("three items round-trip in order", [i.position for i in got] == [0, 1, 2])
        check("size_bytes survives as BIGINT", media[0].size_bytes == 48_210_233)

        s.add(PlaylistItem(playlist_id=playlist.id, media_id=media[0].id, position=0, duration_seconds=10))
        try:
            s.commit()
            check("duplicate (playlist, position) rejected", False, "commit succeeded")
        except IntegrityError:
            s.rollback()
            check("duplicate (playlist, position) rejected", True)

        print("\ndevices + access grants")
        device = Device(
            account_id=account.id, created_by=owner.id, name="Lobby", location="Front desk",
            playlist_id=playlist.id, pairing_code=None, poll_token=None,
            token_hash=f"{PREFIX}-tokenhash", paired_at=datetime.now(UTC),
        )
        unclaimed = Device(
            pairing_code=f"{PREFIX[:3]}X7K", poll_token=f"{PREFIX}-poll",
            pairing_expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        s.add(device)
        s.add(unclaimed)
        s.commit()
        check("an unclaimed device may have no account", unclaimed.account_id is None)

        s.add(DeviceAccess(user_id=manager.id, device_id=device.id))
        s.commit()
        grants = s.exec(select(DeviceAccess).where(DeviceAccess.user_id == manager.id)).all()
        check("grant round-trips", len(grants) == 1)

        print("\nFK behaviour — the rules the subuser model rests on")

        # RESTRICT: media that is on air cannot be deleted.
        # The DELETE is inside the try: session.exec() executes immediately, so the
        # violation raises there rather than at commit().
        try:
            s.exec(delete(Media).where(Media.id == media[0].id))
            s.commit()
            check("deleting on-air media is REFUSED (RESTRICT)", False, "delete succeeded")
        except IntegrityError:
            s.rollback()
            check("deleting on-air media is REFUSED (RESTRICT)", True)

        # SET NULL: deleting a playlist must not delete the hardware.
        s.exec(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id))
        s.exec(delete(Playlist).where(Playlist.id == playlist.id))
        s.commit()
        s.refresh(device)
        check(
            "deleting a playlist keeps the device, playlist_id NULL (SET NULL)",
            device.id is not None and device.playlist_id is None,
        )

        # SET NULL: deleting a subuser keeps their uploads, and cascades their grants.
        manager_id = manager.id
        s.exec(delete(User).where(User.id == manager_id))
        s.commit()
        survivors = s.exec(select(Media).where(Media.account_id == account.id)).all()
        check(
            "deleting a subuser KEEPS their media, created_by NULL (SET NULL)",
            len(survivors) == 3 and all(m.created_by is None for m in survivors),
            f"{len(survivors)} media rows survive",
        )
        left = s.exec(select(DeviceAccess).where(DeviceAccess.user_id == manager_id)).all()
        check("deleting a user removes their grants (CASCADE)", left == [])

        # CASCADE from the account: the tenant is the root of everything.
        s.exec(delete(Account).where(Account.id == account.id))
        s.commit()
        check(
            "deleting the account removes its users, media and devices (CASCADE)",
            s.exec(select(User).where(User.account_id == account.id)).all() == []
            and s.exec(select(Media).where(Media.account_id == account.id)).all() == []
            and s.exec(select(Device).where(Device.account_id == account.id)).all() == [],
        )

        cleanup(s)
        s.exec(delete(Device).where(Device.poll_token == f"{PREFIX}-poll"))
        s.commit()

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All schema checks passed.")


if __name__ == "__main__":
    main()
