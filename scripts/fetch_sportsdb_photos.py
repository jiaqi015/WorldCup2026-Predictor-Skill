#!/usr/bin/env python3
"""Fetch player photos from TheSportsDB API for remaining placeholders."""
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
    validate_image,
)

PHOTOS_DIR = Path(__file__).parent.parent / "data" / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# TheSportsDB free API key (public)
API_KEY = "3"  # Free tier
REQUEST_DELAY = 0.5
DOWNLOAD_DELAY = 1.0
DOWNLOAD_JITTER = 0.5


def query_sportsdb(name):
    """Query TheSportsDB API for player by name."""
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

    # Find best match by normalized name
    target_norm = normalize_name(name)
    for player in players:
        player_name = player.get("strPlayer", "")
        if normalize_name(player_name) == target_norm:
            thumb = player.get("strThumb")
            if thumb:
                return thumb

    # If no exact match, try first result
    first = players[0]
    thumb = first.get("strThumb")
    return thumb if thumb else None


def download_image(url, filepath, timeout=20):
    """Download image from URL, validate, and save."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 2)
                print(f"  [429] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  [Download] Failed: {e}")
            return False
        except Exception as e:
            print(f"  [Download] Failed: {e}")
            return False
    else:
        return False

    if len(data) < 2000:
        return False

    with open(filepath, "wb") as f:
        f.write(data)

    return validate_image(filepath)


def determine_ext(url):
    """Guess file extension from URL or default to .jpg."""
    lower = url.lower()
    if ".png" in lower:
        return ".png"
    if ".webp" in lower:
        return ".webp"
    return ".jpg"


def main():
    parser = argparse.ArgumentParser(description="Fetch player photos from TheSportsDB")
    parser.add_argument("--dry-run", action="store_true", help="Don't download, just show matches")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for progress reporting")
    args = parser.parse_args()

    mapping = load_mapping()
    placeholders = get_placeholders(mapping)
    print(f"[TheSportsDB] {len(placeholders)} placeholder players to process")

    found = 0
    misses = []
    names = list(placeholders.keys())

    for i in range(0, len(names), args.batch_size):
        batch = names[i : i + args.batch_size]
        print(f"  Batch {i // args.batch_size + 1}: {len(batch)} names...")

        for name in batch:
            pic_url = query_sportsdb(name)

            if pic_url:
                ext = determine_ext(pic_url)
                fname = f"sportsdb_{safe_name(name)}{ext}"
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
                    "source": "sportsdb",
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
