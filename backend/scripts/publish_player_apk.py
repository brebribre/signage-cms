"""Upload a player APK to R2 and print the settings that publish it to every screen.

Deliberately does NOT flip the switch itself. It uploads the file and tells you the two
variables to set — because setting them is what pushes an install to every screen you own at
once, and that should be an explicit act, not a side effect of running an upload script.

Usage:
    .venv/bin/python -m scripts.publish_player_apk ../player/app/build/outputs/apk/release/app-release.apk
    .venv/bin/python -m scripts.publish_player_apk <apk> --version 1.2.0   # override detected version
"""

import argparse
import pathlib
import re
import subprocess
import sys
import zipfile

from app.config import get_settings
from app.infra import storage


def detect_version(apk: pathlib.Path) -> str | None:
    """Read versionName straight out of the APK, so the published version can never disagree
    with what the binary actually reports on heartbeat — which would cause an endless
    install loop, every screen reinstalling forever."""
    # aapt2 if it is around; it is the reliable path.
    for tool in ("aapt2", "aapt"):
        try:
            out = subprocess.run(
                [tool, "dump", "badging", str(apk)],
                capture_output=True, text=True, timeout=30,
            ).stdout
            m = re.search(r"versionName='([^']+)'", out)
            if m:
                return m.group(1)
        except (FileNotFoundError, subprocess.SubprocessError):
            continue

    # Fallback: at least confirm it is a real APK so a typo'd path fails loudly here rather
    # than uploading a 0-byte object.
    try:
        with zipfile.ZipFile(apk) as z:
            if "AndroidManifest.xml" not in z.namelist():
                print(f"  ✗ {apk} does not look like an APK", file=sys.stderr)
                raise SystemExit(1)
    except zipfile.BadZipFile:
        print(f"  ✗ {apk} is not a valid APK", file=sys.stderr)
        raise SystemExit(1)
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=pathlib.Path)
    parser.add_argument("--version", help="override the version detected from the APK")
    args = parser.parse_args()

    apk: pathlib.Path = args.apk
    if not apk.is_file():
        print(f"  ✗ no such file: {apk}", file=sys.stderr)
        raise SystemExit(1)

    version = args.version or detect_version(apk)
    if not version:
        print(
            "  ✗ could not read versionName from the APK. Install build-tools (for aapt2) "
            "or pass --version explicitly.\n"
            "    It must match the APK's real versionName exactly, or every screen will "
            "reinstall on every heartbeat forever.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    settings = get_settings()
    key = f"apks/fortu-player-{version}.apk"
    size_mb = apk.stat().st_size / 1_048_576

    print(f"\n  uploading {apk.name} ({size_mb:.1f} MB) as version {version}")
    print(f"  → s3://{settings.r2_bucket}/{key}")

    storage._client().upload_file(
        Filename=str(apk),
        Bucket=settings.r2_bucket,
        Key=key,
        ExtraArgs={"ContentType": "application/vnd.android.package-archive"},
    )

    head = storage.head_object(key)
    if head is None or head["ContentLength"] != apk.stat().st_size:
        print("  ✗ upload could not be verified in R2", file=sys.stderr)
        raise SystemExit(1)
    print(f"  ✓ uploaded and verified ({head['ContentLength']} bytes)\n")

    print(f"  Uploaded, but nothing is published yet — version {version} is now sitting in R2")
    print("  alongside every earlier build.\n")
    print("  To roll it out, open the CMS as an owner: Settings > Player updates, pick this")
    print("  version, and choose \"now\" or a future date/time. Screens pick it up on their")
    print("  next heartbeat after that moment (within ~30s) and install silently.\n")
    print("  To roll back, schedule an earlier version the same way — the most recently")
    print("  *scheduled* rollout whose time has passed is always what's live, so an older")
    print("  build scheduled for now simply takes over.\n")


if __name__ == "__main__":
    main()
