"""Checkpoint: the streaming copy web screens play (services/video_streams.py).

Makes small test videos with ffmpeg itself, so it needs ffmpeg but no network or R2.

Run with:  .venv/bin/python -m scripts.check_video_streams
"""

import subprocess
import tempfile
from pathlib import Path

from app.services import video_streams
from app.services.video_streams import ConversionError, make_stream_copy

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  ✗ {label} FAILED {detail}")


def make_video(path: Path, *, audio: str | None, vcodec: str = "libx264") -> None:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=4"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:a", audio]
    args += ["-c:v", vcodec, "-pix_fmt", "yuv420p", "-g", "25", "-shortest", str(path)]
    subprocess.run(args, check=True, capture_output=True)


def top_level_boxes(path: Path) -> list[str]:
    data = path.read_bytes()
    boxes, offset = [], 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        boxes.append(data[offset + 4:offset + 8].decode("latin-1"))
        if size < 8:
            break
        offset += size
    return boxes


def main() -> None:
    if not video_streams.ffmpeg_available():
        print("ffmpeg not installed — nothing to check here (web screens stream originals without it)")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        print("\nH.264 + AAC")
        src, out = tmp / "a.mp4", tmp / "a-stream.mp4"
        make_video(src, audio="aac")
        mime, size, checksum = make_stream_copy(src, out)
        boxes = top_level_boxes(out)
        check("the MIME type names both codecs", mime.startswith('video/mp4; codecs="avc1.') and "mp4a.40.2" in mime, mime)
        check("the header comes first, then fragments", boxes[:2] == ["ftyp", "moov"] and "moof" in boxes, str(boxes[:6]))
        check("a fragment per keyframe (one a second here)", boxes.count("moof") >= 3, f"{boxes.count('moof')} fragments")
        check("size and checksum describe the copy", size == out.stat().st_size and checksum.startswith("sha256:"))

        print("\nH.264, no audio")
        src, out = tmp / "b.mp4", tmp / "b-stream.mp4"
        make_video(src, audio=None)
        mime, _, _ = make_stream_copy(src, out)
        check("the MIME type has only the video codec", "mp4a" not in mime and "avc1." in mime, mime)

        print("\nnot convertible")
        src, out = tmp / "c.mp4", tmp / "c-stream.mp4"
        make_video(src, audio="libopus")
        try:
            make_stream_copy(src, out)
            check("non-AAC audio is refused with a reason", False, "no error")
        except ConversionError as exc:
            check("non-AAC audio is refused with a reason", "AAC" in str(exc), str(exc))

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("All video stream checks passed.")


if __name__ == "__main__":
    main()
