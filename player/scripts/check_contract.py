"""Verify the Android player's Kotlin models against the backend's live OpenAPI schema.

The player and the API are separate codebases that must agree exactly on JSON field names.
A typo in a `@SerialName` compiles fine and fails at runtime, on a screen, in a lobby — which
is the worst possible place to discover it. This closes that gap from the outside.

Run with:  python3 scripts/check_contract.py [base_url]
Defaults to the local backend on :8001; pass a URL to check against production.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
MODELS = Path(__file__).resolve().parent.parent / "app/src/main/java/com/fortu/player/api/Models.kt"

# (OpenAPI component name, Kotlin data class name)
PAIRS = [
    ("PairStartResponse", "PairStartResponse"),
    ("PairPollResponse", "PairPollResponse"),
    ("ManifestItem", "ManifestItem"),
    ("ManifestResponse", "Manifest"),
    ("ManifestDevice", "ManifestDevice"),
    ("ManifestPlaylist", "ManifestPlaylist"),
    ("HeartbeatRequest", "HeartbeatRequest"),
    ("HeartbeatResponse", "HeartbeatResponse"),
    ("HeartbeatScreen", "HeartbeatScreen"),
    ("UpdateInfo", "UpdateInfo"),
    ("PlayReport", "PlayReport"),
]


def kotlin_fields(source: str, cls: str) -> set[str] | None:
    """Field names a Kotlin data class deserializes, honouring @SerialName overrides.

    Handles both single-line and multi-line declarations by scanning forward from the class
    name and tracking parenthesis depth — a line-count-based regex silently mis-parses the
    single-line form and reports false mismatches.
    """
    start = source.find(f"data class {cls}(")
    if start == -1:
        return None
    i = source.index("(", start)
    depth, end = 0, None
    for j in range(i, len(source)):
        if source[j] == "(":
            depth += 1
        elif source[j] == ")":
            depth -= 1
            if depth == 0:
                end = j
                break
    if end is None:
        return None

    body = source[i + 1 : end]
    # Strip comments first. A KDoc line above a field would otherwise be glued to it by the
    # comma split and the whole part discarded as a comment, silently hiding a real field.
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    fields = set()
    # Split on commas that are not inside nested parens/generics.
    for part in re.split(r",(?![^<]*>)", body):
        part = part.strip()
        if not part or part.startswith(("//", "/*", "*")):
            continue
        sn = re.search(r'@SerialName\("([^"]+)"\)', part)
        if sn:
            fields.add(sn.group(1))
            continue
        v = re.search(r"\bval\s+(\w+)", part)
        if v:
            fields.add(v.group(1))
    return fields


def main() -> None:
    schema = json.load(urllib.request.urlopen(f"{BASE}/openapi.json"))
    comps = schema["components"]["schemas"]
    source = MODELS.read_text()

    failures = []
    print(f"\nchecking {MODELS.name} against {BASE}\n")
    for api_name, kt_name in PAIRS:
        if api_name not in comps:
            print(f"  ✗ {kt_name:20} — '{api_name}' missing from the OpenAPI schema")
            failures.append(kt_name)
            continue
        api = set(comps[api_name].get("properties", {}).keys())
        kt = kotlin_fields(source, kt_name)
        if kt is None:
            print(f"  ✗ {kt_name:20} — no such data class in Models.kt")
            failures.append(kt_name)
            continue
        missing = api - kt   # backend sends something the player cannot read
        extra = kt - api     # player expects something the backend never sends
        if missing or extra:
            failures.append(kt_name)
            detail = ""
            if missing:
                detail += f"  player is MISSING {sorted(missing)}"
            if extra:
                detail += f"  player expects unknown {sorted(extra)}"
            print(f"  ✗ {kt_name:20} api={len(api)} kotlin={len(kt)}{detail}")
        else:
            print(f"  ✓ {kt_name:20} {len(api)} fields")

    print()
    if failures:
        print(f"CONTRACT MISMATCH: {len(failures)} model(s) — " + ", ".join(failures))
        raise SystemExit(1)
    print("Contract matches: every backend field has a Kotlin counterpart, and vice versa.")


if __name__ == "__main__":
    main()
