"""A streaming copy of every uploaded video, for web screens.

A smart TV's browser hands `<video>` to the TV's own media player, which can open an address but
not a file kept inside the browser — so a web screen that caches a video file and plays it gets a
black screen (seen on a Samsung Tizen 5.5 TV). What those browsers do support is Media Source
Extensions: the page feeds the video to the browser piece by piece, the way YouTube and Netflix
play on TVs. That needs the file laid out as *fragmented* MP4 — the moov header up front, then the
media in small independent chunks — which an ordinary MP4 isn't.

So after upload, each video gets a second copy in that layout: `ffmpeg -c copy` with
fragmenting flags. The streams are copied, never re-encoded, so it's fast (seconds for hundreds
of MB), costs no quality, and plays identically. The copy sits beside the original under the same
media id; the Android player keeps using the original, and web screens cache and play the copy.

Runs on one background thread in the API process, one video at a time — a dev-phase choice that
keeps this free of any queue infrastructure. On startup it picks up any ready video that has no
copy yet (older uploads, or ones interrupted by a deploy). Without ffmpeg on the machine it logs
once and does nothing; web screens then stream the original, as they did before this existed.
"""

import hashlib
import json
import logging
import queue
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.infra import storage
from app.models import Media, MediaKind, MediaStatus

logger = logging.getLogger(__name__)

CONVERT_TIMEOUT_SECONDS = 30 * 60

# AAC audio object types, by ffprobe's profile name — the number that goes in `mp4a.40.N`.
_AAC_OBJECT_TYPES = {"Main": 1, "LC": 2, "SSR": 3, "LTP": 4, "HE-AAC": 5, "HE-AACv2": 29}


class ConversionError(Exception):
    """A video that can't get a streaming copy. The message is stored on the row as-is."""


def stream_key(media: Media) -> str:
    return f"media/{media.account_id}/{media.id}/stream.mp4"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _run(args: list[str]) -> str:
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=CONVERT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise ConversionError(f"{args[0]} took longer than {CONVERT_TIMEOUT_SECONDS // 60} minutes") from None
    if done.returncode != 0:
        raise ConversionError(f"{args[0]} failed: {done.stderr.strip()[-300:]}")
    return done.stdout


def _video_codec(fragmented: Path) -> str:
    """`avc1.PPCCLL` from the copy's own avcC box — profile, constraint flags and level exactly as
    the decoder will read them. ffprobe reports profile and level but not the constraint byte, and
    a wrong codec string makes MediaSource refuse the whole file."""
    with fragmented.open("rb") as f:
        head = f.read(256 * 1024)  # empty_moov puts the whole header at the front
    at = head.find(b"avcC")
    if at < 0:
        if b"hvcC" in head or b"hev1" in head:
            raise ConversionError("video is H.265/HEVC; web screens need H.264 — streaming the original instead")
        raise ConversionError("video codec isn't H.264")
    body = head[at + 4 : at + 8]
    if len(body) < 4:
        raise ConversionError("unreadable H.264 header")
    return f"avc1.{body[1]:02x}{body[2]:02x}{body[3]:02x}"


def _audio_codec(source: Path) -> str | None:
    out = json.loads(_run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,profile", "-of", "json", str(source),
    ]))
    streams = out.get("streams") or []
    if not streams:
        return None
    codec, profile = streams[0].get("codec_name"), streams[0].get("profile")
    if codec != "aac":
        raise ConversionError(f"audio is {codec}; web screens need AAC — streaming the original instead")
    return f"mp4a.40.{_AAC_OBJECT_TYPES.get(profile, 2)}"


def make_stream_copy(source: Path, dest: Path) -> tuple[str, int, str]:
    """Writes the fragmented copy to `dest`. Returns (mime, size, checksum)."""
    audio = _audio_codec(source)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        # First video and (if any) first audio track only; subtitles and data tracks would
        # need codecs of their own in the MIME string.
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c", "copy",
        # A fragment at every keyframe, the header up front with no samples in it, and each
        # fragment addressed on its own — what MediaSource expects to be fed.
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4", str(dest),
    ])
    codecs = ",".join(c for c in (_video_codec(dest), audio) if c)
    digest = hashlib.sha256()
    with dest.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return f'video/mp4; codecs="{codecs}"', dest.stat().st_size, f"sha256:{digest.hexdigest()}"


def process(media_id: uuid.UUID) -> None:
    """Make, upload and record one video's streaming copy. Never raises."""
    from app.infra.db import engine

    with Session(engine) as session:
        media = session.get(Media, media_id)
        if (
            media is None or media.kind != MediaKind.VIDEO or media.status != MediaStatus.READY
            or media.stream_key or media.stream_error
        ):
            return
        try:
            with tempfile.TemporaryDirectory(prefix="fortu-stream-") as tmp:
                source, dest = Path(tmp) / "source.mp4", Path(tmp) / "stream.mp4"
                storage.download_file(media.storage_key, str(source))
                mime, size, checksum = make_stream_copy(source, dest)
                key = stream_key(media)
                storage.upload_file(str(dest), key, "video/mp4")
        except ConversionError as exc:
            logger.warning("no streaming copy for media %s: %s", media_id, exc)
            _record_error(session, media_id, str(exc))
            return
        except Exception as exc:  # storage or anything unexpected: record, never kill the worker
            logger.exception("streaming copy failed for media %s", media_id)
            _record_error(session, media_id, f"conversion failed: {exc}"[:500])
            return

        media = session.get(Media, media_id)
        if media is None:  # deleted while converting — don't leave the copy behind
            storage.delete_object(key)
            return
        media.stream_key, media.stream_size_bytes = key, size
        media.stream_checksum, media.stream_mime = checksum, mime
        session.add(media)
        session.commit()
        logger.info("streaming copy ready for media %s (%s, %d bytes)", media_id, mime, size)
        # Screens showing it pick the copy up on their next poll: stream_checksum is part of the
        # manifest version (services/device_sync.py::compute_version).


def _record_error(session: Session, media_id: uuid.UUID, message: str) -> None:
    session.rollback()
    media = session.get(Media, media_id)
    if media is not None:
        media.stream_error = message[:500]
        session.add(media)
        session.commit()


_queue: "queue.Queue[uuid.UUID]" = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


def _loop() -> None:
    while True:
        media_id = _queue.get()
        process(media_id)
        _queue.task_done()


def enqueue(media_id: uuid.UUID) -> None:
    """Queue one video. Returns at once; safe to call for anything (non-videos are skipped)."""
    global _worker
    if not ffmpeg_available():
        return
    with _worker_lock:
        if _worker is None:
            _worker = threading.Thread(target=_loop, name="video-streams", daemon=True)
            _worker.start()
    _queue.put(media_id)


def enqueue_missing() -> int:
    """Queue every ready video without a copy yet. Called at startup."""
    if not ffmpeg_available():
        logger.warning("ffmpeg not found — videos get no streaming copy; web screens stream the originals")
        return 0
    from app.infra.db import engine

    with Session(engine) as session:
        ids = list(session.exec(
            select(Media.id).where(
                Media.kind == MediaKind.VIDEO, Media.status == MediaStatus.READY,
                Media.stream_key.is_(None), Media.stream_error.is_(None),
            )
        ).all())
    for media_id in ids:
        enqueue(media_id)
    if ids:
        logger.info("queued %d video(s) for a streaming copy", len(ids))
    return len(ids)
