#!/usr/bin/env python3
"""Sync the repository's canonical index.html into the installable skill asset."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TARGET = SKILL_ROOT / "assets" / "predictor" / "index.html"


def find_source() -> Path | None:
    for candidate in SKILL_ROOT.parents:
        source = candidate / "index.html"
        if (candidate / ".git").exists() and source.is_file():
            return source
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the bundled app differs instead of updating it",
    )
    args = parser.parse_args()

    source = find_source()
    if source is None:
        parser.error("repository root index.html not found")

    source_bytes = source.read_bytes()
    target_bytes = TARGET.read_bytes() if TARGET.exists() else None
    if source_bytes == target_bytes:
        print("Bundled predictor is already in sync.")
        return 0

    if args.check:
        print(f"Bundled predictor is stale: {TARGET}")
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, TARGET)
    print(f"Synced {source} -> {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
