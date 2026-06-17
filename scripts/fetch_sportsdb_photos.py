#!/usr/bin/env python3
"""Find or fetch player photos from TheSportsDB API for remaining placeholders.

The default mode is a read-only dry run. Use --write when you intentionally
want to update data/squads/photo_mapping.json and commit the downloaded assets.
"""
import argparse
import json
import os
import sys
import time
import random
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from photo_utils import (
    get_placeholders,
    load_mapping,
    normalize_name,
    safe_name,
    save_mapping,
    download_image,
    determine_ext,
)

PHOTOS_DIR = Path(__file__).parent.parent / "data" / "photos"

API_KEY = "3"  # TheSportsDB free tier
REQUEST_DELAY = 0.5
DOWNLOAD_DELAY = 1.0
DOWNLOAD_JITTER = 0.5


def query_sportsdb(name):
    """Query TheSportsDB API for player by name. Only returns exact match."""
    from photo_utils import USER_AGENT
    encoded = urllib.parse.quote(name)
    url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/searchplayers.php?p={encoded}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    players = data.get("player")
    if not players:
        return None

    # M2: Only return exact normalized match, no fallback to first result
    target_norm = normalize_name(name)
    for player in players:
        player_name = player.get("strPlayer", "")
        if normalize_name(player_name) == target_norm:
            thumb = player.get("strThumb")
            if thumb:
                return thumb

    return None


def main():
    PHOTOS_DIR.mkdir(exist_ok=True)
    parser = argparse.ArgumentParser(description="Fetch player photos from TheSportsDB")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Download images and update photo_mapping.json. Default is dry-run.",
    )
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for progress reporting")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N placeholder players. Useful for smoke tests.",
    )
    args = parser.parse_args()
    dry_run = not args.write

    mapping = load_mapping()
    placeholders = get_placeholders(mapping)
    print(f"[TheSportsDB] {len(placeholders)} placeholder players to process")
    if dry_run:
        print("[DRY] No files will be written. Re-run with --write to update assets.")

    found = 0
    misses = []
    names = list(placeholders.keys())
    if args.limit:
        names = names[: args.limit]
        print(f"[LIMIT] Processing first {len(names)} names")

    for i in range(0, len(names), args.batch_size):
        batch = names[i : i + args.batch_size]
        print(f"  Batch {i // args.batch_size + 1}: {len(batch)} names...", flush=True)

        for name in batch:
            pic_url = query_sportsdb(name)

            if pic_url:
                ext = determine_ext(pic_url)
                fname = f"sportsdb_{safe_name(name)}{ext}"
                fpath = PHOTOS_DIR / fname

                if fpath.exists() and fpath.stat().st_size > 2000:
                    found += 1
                elif dry_run:
                    found += 1
                    print(f"    [DRY] {name} -> {pic_url}")
                elif download_image(pic_url, str(fpath)):
                    found += 1
                    time.sleep(DOWNLOAD_DELAY + random.uniform(0, DOWNLOAD_JITTER))
                else:
                    misses.append(name)
                    continue

                mapping[name] = {
                    "source": "sportsdb",
                    "path": f"data/photos/{fname}",
                    "athlete_id": None,
                }
            else:
                misses.append(name)

            time.sleep(REQUEST_DELAY)

        if not dry_run:
            save_mapping(mapping)
        print(f"    Found {found} so far, {len(misses)} misses")

    print(f"\n=== Summary ===")
    print(f"  Total placeholders: {len(placeholders)}")
    print(f"  Found: {found}")
    print(f"  Not found: {len(misses)}")

    if not dry_run:
        save_mapping(mapping)

    return 0 if found > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
