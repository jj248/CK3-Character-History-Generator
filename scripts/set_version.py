"""
scripts/set_version.py
~~~~~~~~~~~~~~~~~~~~~~
Synchronises the application version across all manifest files from a given
version string (typically a git tag like ``v1.2.3``).

Files patched
-------------
- ``ui/src-tauri/tauri.conf.json``  — ``"version"`` field
- ``ui/src-tauri/Cargo.toml``       — ``version`` field under ``[package]``

Usage
-----
    python scripts/set_version.py v1.2.3

The leading ``v`` is stripped automatically before writing, so the manifests
always contain bare semver (e.g. ``1.2.3``).

Exit codes
----------
0  — success
1  — bad arguments or version format
2  — file not found or write failure
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent

TAURI_CONF = REPO_ROOT / "ui" / "src-tauri" / "tauri.conf.json"
CARGO_TOML = REPO_ROOT / "ui" / "src-tauri" / "Cargo.toml"

# Matches the [package] version line in Cargo.toml.
# Only replaces the first occurrence so workspace dependency versions are safe.
_CARGO_VERSION_RE = re.compile(
    r'^(version\s*=\s*")[^"]+(")',
    re.MULTILINE,
)

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _strip_v_prefix(tag: str) -> str:
    """Return bare semver from a git tag, e.g. ``v1.2.3`` → ``1.2.3``."""
    return tag.lstrip("v")


def _validate_semver(version: str) -> None:
    """Raise ``SystemExit`` if *version* is not valid semver (MAJOR.MINOR.PATCH)."""
    if not _SEMVER_RE.match(version):
        print(f"error: '{version}' is not valid semver (expected MAJOR.MINOR.PATCH).", file=sys.stderr)
        raise SystemExit(1)


def _patch_tauri_conf(version: str) -> None:
    """Write *version* into the ``"version"`` field of tauri.conf.json."""
    if not TAURI_CONF.exists():
        print(f"error: {TAURI_CONF} not found.", file=sys.stderr)
        raise SystemExit(2)

    config = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    config["version"] = version
    TAURI_CONF.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  patched {TAURI_CONF.relative_to(REPO_ROOT)}")


def _patch_cargo_toml(version: str) -> None:
    """Write *version* into the ``[package]`` section of Cargo.toml."""
    if not CARGO_TOML.exists():
        print(f"error: {CARGO_TOML} not found.", file=sys.stderr)
        raise SystemExit(2)

    original = CARGO_TOML.read_text(encoding="utf-8")
    patched, count = _CARGO_VERSION_RE.subn(rf'\g<1>{version}\g<2>', original, count=1)

    if count == 0:
        print(f"error: could not find version field in {CARGO_TOML}.", file=sys.stderr)
        raise SystemExit(2)

    CARGO_TOML.write_text(patched, encoding="utf-8")
    print(f"  patched {CARGO_TOML.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if len(args) != 1:
        print("usage: python scripts/set_version.py <version>", file=sys.stderr)
        print("       e.g.  python scripts/set_version.py v1.2.3", file=sys.stderr)
        raise SystemExit(1)

    version = _strip_v_prefix(args[0])
    _validate_semver(version)

    print(f"Setting version → {version}")
    _patch_tauri_conf(version)
    _patch_cargo_toml(version)
    print("Done.")


if __name__ == "__main__":
    main()