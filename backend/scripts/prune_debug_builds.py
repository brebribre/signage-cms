"""Delete the player builds in R2 that were signed with the debug key, keeping every build
signed with the real release key.

Why: Android only installs an update signed with the same key as the app already on the screen.
Since 1.3.7 (2026-09-22) every build is signed with Paskall's own key, so a debug-signed build
can never be installed over a current screen, and rolling one out by mistake — a rollback typed
one version too far — would fail on every screen at once. Kept around they are only a trap.

Each build is checked by its actual signing certificate, not by its version number: it is
downloaded to a temporary folder, read with the Android SDK's `apksigner`, and kept unless it is
signed with the debug key. A build whose signature cannot be read is kept, never guessed at.
Prints what would go and changes nothing until you add --yes. Deleting is permanent: the bucket
keeps no older copies.

    .venv/bin/python -m scripts.prune_debug_builds              # show what would go
    .venv/bin/python -m scripts.prune_debug_builds --yes        # delete it

Runs from a laptop with the R2 settings in backend/.env, like publish_player_apk.py. Needs
`apksigner` from the Android SDK build-tools, found under $ANDROID_HOME or
~/Library/Android/sdk; pass --apksigner to point at it directly.
"""

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

from app.infra import storage
from app.services import player_releases

#: The debug certificate Android Studio signs with on every machine: "C=US, O=Android, CN=Android Debug".
DEBUG_DN = "CN=Android Debug"
#: The release key's certificate (see player/README.md, "Signing").
RELEASE_SHA256 = "eea378340148599f8977df652e3c303666e90a30dcea6b0c1c2e96a30e67342b"


def find_apksigner(explicit: str | None) -> str:
    if explicit:
        return explicit
    for root in (os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"), str(pathlib.Path.home() / "Library/Android/sdk")):
        if not root:
            continue
        tools = sorted((pathlib.Path(root) / "build-tools").glob("*/apksigner"))
        if tools:
            return str(tools[-1])
    print("  ✗ apksigner not found. Install Android build-tools or pass --apksigner.", file=sys.stderr)
    raise SystemExit(1)


def signer(apksigner: str, apk: pathlib.Path) -> tuple[str | None, str | None]:
    """(certificate DN, SHA-256) of the first signer, or (None, None) if it can't be read."""
    out = subprocess.run([apksigner, "verify", "--print-certs", str(apk)], capture_output=True, text=True).stdout
    dn = sha = None
    for line in out.splitlines():
        if "certificate DN:" in line and dn is None:
            dn = line.split("DN:", 1)[1].strip()
        if "certificate SHA-256 digest:" in line and sha is None:
            sha = line.split("digest:", 1)[1].strip().lower()
    return dn, sha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="actually delete; without it nothing changes")
    parser.add_argument("--apksigner", help="path to apksigner")
    args = parser.parse_args()
    apksigner = find_apksigner(args.apksigner)

    releases = player_releases.list_releases(current_key=None)
    doomed: list[player_releases.PlayerRelease] = []
    print()
    with tempfile.TemporaryDirectory() as tmp:
        for r in releases:
            apk = pathlib.Path(tmp) / f"{r.version}.apk"
            storage.download_file(r.key, str(apk))
            dn, sha = signer(apksigner, apk)
            apk.unlink()
            if sha == RELEASE_SHA256:
                verdict = "keep    release key"
            elif dn and DEBUG_DN in dn:
                verdict = "delete  debug key"
                doomed.append(r)
            else:
                verdict = f"keep    unrecognised signer: {dn or 'unreadable'}"
            print(f"  {r.version:>8}  {verdict}")

    print(f"\n  {len(doomed)} debug-signed build(s) of {len(releases)}.")
    if not doomed:
        return
    if not args.yes:
        print("  Nothing deleted. Run again with --yes to delete them.\n")
        return
    for r in doomed:
        storage.delete_object(r.key)
        gone = storage.head_object(r.key) is None
        print(f"  {'✓' if gone else '✗'} {r.key}")
    print()


if __name__ == "__main__":
    main()
