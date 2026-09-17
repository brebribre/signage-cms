"""Every uploaded video, made playable on every screen — then laid out for streaming too.

Two copies come out of this, in order:

**The playback copy** is what screens download. Uploads arrive as whatever an editor exported:
60 fps, H.265, 10-bit, 40 Mbps — all legal "video/mp4", none of it something a signage box
decodes in hardware, and the difference between smooth and stuttering in a lobby is exactly
this. So every video is brought to one shape: H.264 High profile, yuv420p, no faster than
30 fps, AAC stereo, a keyframe every two seconds, header up front, at a bitrate the box's
decoder and the venue's wifi can both carry. Resolution is kept up to 4K (3840 on the long
side) — the panels this is built for are 4K, and a 4K source must reach them as 4K — with the
level and bitrate ceiling chosen for the size (4.1 and 8 Mbps up to 1080p, 5.1 and 20 Mbps
above). A file that already meets all that is only remuxed (faststart), so nothing gets
re-encoded — and softened — without cause; `Media.playback_reencoded` says which happened.
This is what Yodeck and the rest do on upload, and it is the single biggest lever on
playback quality, ahead of anything a player can do.

**The streaming copy** is the playback copy re-laid as fragmented MP4 — the moov header up
front, the media in small independent chunks — for web screens, whose smart-TV browsers can't
open a plain file from their own cache but can be fed one piece by piece through Media Source
Extensions (the way YouTube plays on them). A stream copy, never a second encode.

Runs on one background thread in the API process, one video at a time — a dev-phase choice
that keeps this free of any queue infrastructure. On startup it picks up any ready video that
has no playback copy yet (older uploads, or ones interrupted by a deploy). Without ffmpeg on
the machine it logs once and does nothing; screens then get the originals, as they did before
this existed.
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
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from sqlmodel import Session, select

from app.infra import storage
from app.models import Media, MediaKind, MediaStatus

logger = logging.getLogger(__name__)

CONVERT_TIMEOUT_SECONDS = 30 * 60

# --- The target every playback copy meets -------------------------------------------------
# Up to 4K, never scaled below the source. H.264 High@4.1 covers 1080p30; 2160p30 needs 5.1.
MAX_EDGE_PX = 3840
HD_EDGE_PX = 1920
MAX_FPS = 30.0
ACCEPTED_PROFILES = {"Baseline", "Constrained Baseline", "Main", "High"}
ACCEPTED_PIX_FMTS = {"yuv420p", "yuvj420p"}
CRF = "21"
KEYFRAME_SECONDS = 2


def _is_4k(width: int, height: int) -> bool:
    return max(width, height) > HD_EDGE_PX


def _level_for(width: int, height: int) -> str:
    return "5.1" if _is_4k(width, height) else "4.1"


def _max_level_for(width: int, height: int) -> int:
    return 51 if _is_4k(width, height) else 41


def _maxrate_for(width: int, height: int) -> tuple[str, str]:
    """(maxrate, bufsize): 8 Mbps up to 1080p, 20 Mbps above — what a box decodes without
    dropping frames and what venue wifi delivers in reasonable time."""
    return ("20M", "40M") if _is_4k(width, height) else ("8M", "16M")


def _accept_bitrate_for(width: int, height: int) -> int:
    """A little above the encode's own cap, so a file already at the target isn't re-encoded."""
    return 22_000_000 if _is_4k(width, height) else 9_000_000

# AAC audio object types, by ffprobe's profile name — the number that goes in `mp4a.40.N`.
_AAC_OBJECT_TYPES = {"Main": 1, "LC": 2, "SSR": 3, "LTP": 4, "HE-AAC": 5, "HE-AACv2": 29}


class ConversionError(Exception):
    """A video that can't be processed. The message is stored on the row as-is."""


def stream_key(media: Media) -> str:
    return f"media/{media.account_id}/{media.id}/stream.mp4"


def playback_key(media: Media) -> str:
    return f"media/{media.account_id}/{media.id}/playback.mp4"


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


# --- Probing ------------------------------------------------------------------------------


@dataclass
class VideoInfo:
    codec: str
    profile: str | None
    level: int | None
    pix_fmt: str | None
    width: int
    height: int
    fps: float
    bitrate: int | None
    duration: float | None
    audio_codec: str | None
    audio_profile: str | None

    def meets_target(self) -> bool:
        """Whether a screen can play this as-is — the test that decides remux versus re-encode."""
        return (
            self.codec == "h264"
            and (self.profile in ACCEPTED_PROFILES)
            and (self.level is None or self.level <= _max_level_for(self.width, self.height))
            and (self.pix_fmt in ACCEPTED_PIX_FMTS)
            and max(self.width, self.height) <= MAX_EDGE_PX
            and self.fps <= MAX_FPS + 0.5
            and (self.bitrate is None or self.bitrate <= _accept_bitrate_for(self.width, self.height))
            and self.audio_codec in (None, "aac")
        )

    def describe(self) -> str:
        parts = [self.codec, f"{self.width}x{self.height}", f"{self.fps:g} fps"]
        if self.profile:
            parts.append(self.profile)
        if self.bitrate:
            parts.append(f"{self.bitrate / 1_000_000:.1f} Mbps")
        return " ".join(parts)


def _fps(stream: dict) -> float:
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = stream.get(key)
        if raw and raw != "0/0":
            try:
                return float(Fraction(raw))
            except (ValueError, ZeroDivisionError):
                continue
    return 0.0


def probe(source: Path) -> VideoInfo:
    out = json.loads(_run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source),
    ]))
    video = next((s for s in out.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise ConversionError("no video track in the file")
    audio = next((s for s in out.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = out.get("format", {})

    def as_int(value) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def as_float(value) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return VideoInfo(
        codec=video.get("codec_name") or "unknown",
        profile=video.get("profile"),
        level=as_int(video.get("level")),
        pix_fmt=video.get("pix_fmt"),
        width=as_int(video.get("width")) or 0,
        height=as_int(video.get("height")) or 0,
        fps=_fps(video),
        bitrate=as_int(fmt.get("bit_rate")) or as_int(video.get("bit_rate")),
        duration=as_float(fmt.get("duration")),
        audio_codec=audio.get("codec_name") if audio else None,
        audio_profile=audio.get("profile") if audio else None,
    )


# --- The playback copy --------------------------------------------------------------------


def make_playback_copy(source: Path, dest: Path, info: VideoInfo) -> bool:
    """Writes the playback copy to `dest`. Returns whether the video was re-encoded (True) or
    only remuxed because it already met the target (False)."""
    if info.meets_target():
        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c", "copy",
            "-movflags", "+faststart",
            "-f", "mp4", str(dest),
        ])
        return False

    # Only ever scale down, and only past 4K — a 720p file stays 720p, a 4K file stays 4K, an
    # 8K one becomes 4K. Even dimensions, because H.264 4:2:0 needs them.
    filters = [
        f"scale=w='min({MAX_EDGE_PX},iw)':h='min({MAX_EDGE_PX},ih)'"
        ":force_original_aspect_ratio=decrease:force_divisible_by=2",
    ]
    # Only bring fast content down. 25 fps is left at 25: turning it into 30 would duplicate
    # every fifth frame, which judders worse than 25 on a 60 Hz panel does.
    fps = info.fps if info.fps <= MAX_FPS + 0.5 else MAX_FPS
    if fps != info.fps:
        filters.append(f"fps={MAX_FPS:g}")
    gop = max(1, round((fps or MAX_FPS) * KEYFRAME_SECONDS))
    scale = min(1.0, MAX_EDGE_PX / max(info.width, info.height, 1))
    out_w, out_h = round(info.width * scale), round(info.height * scale)
    maxrate, bufsize = _maxrate_for(out_w, out_h)

    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-profile:v", "high", "-level", _level_for(out_w, out_h), "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", CRF, "-maxrate", maxrate, "-bufsize", bufsize,
        # A keyframe every two seconds and nowhere else: a seek or a loop lands on one quickly,
        # and the fragmented copy (one fragment per keyframe) comes out in even pieces.
        "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
        "-movflags", "+faststart",
    ]
    if info.audio_codec is not None:
        args += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    args += ["-f", "mp4", str(dest)]
    _run(args)
    return True


# --- The streaming copy -------------------------------------------------------------------


def _video_codec(fragmented: Path) -> str:
    """`avc1.PPCCLL` from the copy's own avcC box — profile, constraint flags and level exactly as
    the decoder will read them. ffprobe reports profile and level but not the constraint byte, and
    a wrong codec string makes MediaSource refuse the whole file."""
    with fragmented.open("rb") as f:
        head = f.read(256 * 1024)  # empty_moov puts the whole header at the front
    at = head.find(b"avcC")
    if at < 0:
        if b"hvcC" in head or b"hev1" in head:
            raise ConversionError("video is H.265/HEVC; web screens need H.264")
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
        raise ConversionError(f"audio is {codec}; web screens need AAC")
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
    return f'video/mp4; codecs="{codecs}"', dest.stat().st_size, _sha256(dest)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


# --- The worker ---------------------------------------------------------------------------


def process(media_id: uuid.UUID) -> None:
    """Make, upload and record one video's playback copy, then its streaming copy. Never
    raises. A failure in the second step keeps the first: a screen that can't stream still
    gets the normalised file."""
    from app.infra.db import engine

    with Session(engine) as session:
        media = session.get(Media, media_id)
        if (
            media is None or media.kind != MediaKind.VIDEO or media.status != MediaStatus.READY
            or media.playback_key or media.playback_error
        ):
            return
        old_stream_key = media.stream_key
        play_key, strm_key = playback_key(media), stream_key(media)

        try:
            with tempfile.TemporaryDirectory(prefix="fortu-video-") as tmp:
                source = Path(tmp) / "source.mp4"
                playback = Path(tmp) / "playback.mp4"
                stream = Path(tmp) / "stream.mp4"
                storage.download_file(media.storage_key, str(source))

                info = probe(source)
                reencoded = make_playback_copy(source, playback, info)
                logger.info(
                    "media %s: %s → playback copy (%s)", media_id, info.describe(),
                    "re-encoded" if reencoded else "remuxed as-is",
                )
                after = probe(playback)
                play_size, play_checksum = playback.stat().st_size, _sha256(playback)
                storage.upload_file(str(playback), play_key, "video/mp4")

                stream_result: tuple[str, int, str] | None = None
                stream_error: str | None = None
                try:
                    stream_result = make_stream_copy(playback, stream)
                    storage.upload_file(str(stream), strm_key, "video/mp4")
                except ConversionError as exc:
                    stream_error = str(exc)
        except ConversionError as exc:
            logger.warning("no playback copy for media %s: %s", media_id, exc)
            _record_error(session, media_id, str(exc))
            return
        except Exception as exc:  # storage or anything unexpected: record, never kill the worker
            logger.exception("video processing failed for media %s", media_id)
            _record_error(session, media_id, f"processing failed: {exc}"[:500])
            return

        media = session.get(Media, media_id)
        if media is None:  # deleted while converting — don't leave the copies behind
            storage.delete_object(play_key)
            if stream_result:
                storage.delete_object(strm_key)
            return
        media.playback_key, media.playback_size_bytes = play_key, play_size
        media.playback_checksum, media.playback_reencoded = play_checksum, reencoded
        media.playback_error = None
        # The probe of the copy is the truth about what screens will show.
        media.width, media.height = after.width or media.width, after.height or media.height
        if after.duration:
            media.duration_seconds = after.duration
        if stream_result:
            media.stream_key, media.stream_size_bytes = strm_key, stream_result[1]
            media.stream_mime, media.stream_checksum = stream_result[0], stream_result[2]
            media.stream_error = None
        else:
            media.stream_key = media.stream_size_bytes = media.stream_mime = media.stream_checksum = None
            media.stream_error = stream_error
        session.add(media)
        session.commit()
        # An older stream copy made from the original (before playback copies existed) is
        # superseded; only after the row points elsewhere is it safe to remove.
        if old_stream_key and old_stream_key != strm_key:
            storage.delete_object(old_stream_key)
        logger.info(
            "media %s ready: playback %d bytes%s", media_id, play_size,
            f", stream {stream_result[1]} bytes" if stream_result else f", no stream copy ({stream_error})",
        )
        # Screens showing it pick the copies up on their next poll: both checksums are part of
        # the manifest version (services/device_sync.py::compute_version).


def _record_error(session: Session, media_id: uuid.UUID, message: str) -> None:
    session.rollback()
    media = session.get(Media, media_id)
    if media is not None:
        media.playback_error = message[:500]
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
            _worker = threading.Thread(target=_loop, name="video-processing", daemon=True)
            _worker.start()
    _queue.put(media_id)


def enqueue_missing() -> int:
    """Queue every ready video without a playback copy yet. Called at startup — this is also
    how every video uploaded before playback copies existed gets one."""
    if not ffmpeg_available():
        logger.warning("ffmpeg not found — videos get no playback or streaming copy; screens play the originals")
        return 0
    from app.infra.db import engine

    with Session(engine) as session:
        ids = list(session.exec(
            select(Media.id).where(
                Media.kind == MediaKind.VIDEO, Media.status == MediaStatus.READY,
                Media.playback_key.is_(None), Media.playback_error.is_(None),
            )
        ).all())
    for media_id in ids:
        enqueue(media_id)
    if ids:
        logger.info("queued %d video(s) for a playback copy", len(ids))
    return len(ids)
