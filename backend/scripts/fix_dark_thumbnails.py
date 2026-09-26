"""Find videos whose library preview is black, and remake it from the video itself.

A browser draws the preview frame at upload; iPhone Safari (and sometimes others) draws before it
has decoded a frame, and a black JPEG goes up — which looks like a broken video in the library.
New uploads are caught when their playback copy is made (services/video_streams.py); this is for
the ones uploaded before that check existed.

**Dry run by default.** It lists the dark previews and exits; remaking them needs --fix.

    .venv/bin/python -m scripts.fix_dark_thumbnails
    .venv/bin/python -m scripts.fix_dark_thumbnails --fix
"""

import argparse

from sqlmodel import Session, select

from app.infra.db import engine
from app.models import Media, MediaKind, MediaStatus
from app.services import video_streams


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="remake the dark previews")
    args = parser.parse_args()

    if args.fix and not video_streams.ffmpeg_available():
        raise SystemExit("ffmpeg is not installed here, so no preview can be remade")

    with Session(engine) as session:
        videos = session.exec(
            select(Media).where(
                Media.kind == MediaKind.VIDEO, Media.status == MediaStatus.READY,
                Media.thumbnail_key.is_not(None), Media.playback_key.is_not(None),
            )
        ).all()
        dark = [m for m in videos if video_streams.thumbnail_is_dark(m.thumbnail_key)]
        print(f"{len(dark)} of {len(videos)} video previews are dark")
        for m in dark:
            print(f"  {m.id}  {m.filename}")
        if not args.fix:
            if dark:
                print("dry run — run again with --fix to remake them")
            return
        for m in dark:
            video_streams._video_thumbnail(session, m.id, replace=True)
        still = [m for m in dark if video_streams.thumbnail_is_dark(session.get(Media, m.id).thumbnail_key)]
        print(f"remade {len(dark) - len(still)}; {len(still)} still dark (the video itself may be)")


if __name__ == "__main__":
    main()
