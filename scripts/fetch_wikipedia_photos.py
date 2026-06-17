#!/usr/bin/env python3
"""Fetch player photos from Wikipedia API for remaining placeholders."""
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
    USER_AGENT,
)

PHOTOS_DIR = Path(__file__).parent.parent / "data" / "photos"

REQUEST_DELAY = 1.0
DOWNLOAD_DELAY = 2.0
DOWNLOAD_JITTER = 1.0


def query_wikipedia(name):
    """Query Wikipedia API for page image."""
    # Try English Wikipedia first
    encoded = urllib.parse.quote(name.replace(" ", "_"))
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={encoded}&prop=pageimages&piprop=original&format=json"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "original" in page:
            return page["original"].get("source")
    return None


def main():
    PHOTOS_DIR.mkdir(exist_ok=True)
    parser = argparse.ArgumentParser(description="Fetch player photos from Wikipedia")
    parser.add_argument("--dry-run", action="store_true", help="Don't download, just show matches")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for progress reporting")
    args = parser.parse_args()

    mapping = load_mapping()
    placeholders = get_placeholders(mapping)
    print(f"[Wikipedia] {len(placeholders)} placeholder players to process")

    found = 0
    misses = []
    names = list(placeholders.keys())

    for i in range(0, len(names), args.batch_size):
        batch = names[i : i + args.batch_size]
        print(f"  Batch {i // args.batch_size + 1}: {len(batch)} names...")

        for name in batch:
            pic_url = query_wikipedia(name)

            if pic_url:
                ext = determine_ext(pic_url)
                fname = f"wikipedia_{safe_name(name)}{ext}"
                fpath = PHOTOS_DIR / fname

                if fpath.exists() and fpath.stat().st_size > 2000:
                    found += 1
                elif args.dry_run:
                    found += 1
                    print(f"    [DRY] {name} -> {pic_url}")
                elif download_image(pic_url, str(fpath)):
                    found += 1
                    time.sleep(DOWNLOAD_DELAY + random.uniform(0, DOWNLOAD_JITTER))
                else:
                    misses.append(name)
                    continue

                mapping[name] = {
                    "source": "wikipedia",
                    "path": f"data/photos/{fname}",
                    "athlete_id": None,
                }
            else:
                misses.append(name)

            time.sleep(REQUEST_DELAY)

        if not args.dry_run:
            save_mapping(mapping)
        print(f"    Found {found} so far, {len(misses)} misses")

    print(f"\n=== Summary ===")
    print(f"  Total placeholders: {len(placeholders)}")
    print(f"  Found: {found}")
    print(f"  Not found: {len(misses)}")

    if not args.dry_run:
        save_mapping(mapping)

    return 0 if found > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
