#!/usr/bin/env python3
"""
TDD Phase 3b: Crawl player headshots from ESPN API and persist locally.

Strategy:
1. ESPN API roster endpoint provides headshot URLs for many players
2. Download to data/photos/{athlete_id}.png
3. Build photo mapping: player name -> local path
4. Skip Wikipedia (SSL timeout) - use ESPN only
5. Generate validation report
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SQUADS_FILE = DATA_DIR / "squads" / "squads_partial.json"
PHOTOS_DIR = DATA_DIR / "photos"
PHOTO_MAP_FILE = DATA_DIR / "squads" / "photo_mapping.json"

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"

REQUEST_DELAY = 0.1  # seconds between downloads (ESPN is fast)
MAX_RETRIES = 2


def load_squads():
    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_json(url, retries=MAX_RETRIES, timeout=10):
    """Fetch JSON with retries."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt < retries:
                time.sleep(0.5)
            else:
                return None
    return None


def download_file(url, filepath, retries=MAX_RETRIES, timeout=10):
    """Download a file with retries."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = resp.read()
            if len(data) < 1000:  # Too small, likely error page
                return False
            with open(filepath, "wb") as f:
                f.write(data)
            return True
        except Exception:
            if attempt < retries:
                time.sleep(0.5)
            else:
                return False
    return False


def crawl_all_photos():
    """Main crawling function - ESPN headshots only."""
    squads = load_squads()
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    photo_mapping = {}
    stats = {
        "total_players": 0,
        "espn_found": 0,
        "espn_downloaded": 0,
        "no_headshot": 0,
        "no_match": 0,
        "teams_processed": 0,
        "errors": []
    }

    for team_name, team_data in squads.items():
        team_id = team_data.get("team_id")
        if not team_id:
            stats["errors"].append(f"No team_id for {team_name}")
            continue

        sys.stdout.write(f"\n[{stats['teams_processed']+1}/{len(squads)}] {team_name} ")
        sys.stdout.flush()

        roster_data = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster")
        if not roster_data:
            stats["errors"].append(f"Failed roster: {team_name}")
            stats["no_match"] += len(team_data.get("players", []))
            stats["total_players"] += len(team_data.get("players", []))
            stats["teams_processed"] += 1
            continue

        athletes = roster_data.get("athletes", [])
        # Build lookup: name -> (athlete_id, headshot_url)
        espn_athletes = {}
        for a in athletes:
            aid = a.get("id")
            name = a.get("displayName", "")
            headshot = a.get("headshot", {})
            hs_url = headshot.get("href") if headshot else None
            espn_athletes[name] = (aid, hs_url)

        for player in team_data.get("players", []):
            stats["total_players"] += 1
            pname = player["name"]

            # Find match
            matched = None
            # Exact match
            if pname in espn_athletes:
                matched = espn_athletes[pname]
            else:
                # Fuzzy match
                for ename, info in espn_athletes.items():
                    if pname.lower().strip() == ename.lower().strip():
                        matched = info
                        break
                if not matched:
                    for ename, info in espn_athletes.items():
                        if pname.lower() in ename.lower() or ename.lower() in pname.lower():
                            matched = info
                            break

            if not matched:
                stats["no_match"] += 1
                sys.stdout.write("m")
                sys.stdout.flush()
                continue

            athlete_id, hs_url = matched

            if not hs_url:
                stats["no_headshot"] += 1
                sys.stdout.write("n")
                sys.stdout.flush()
                continue

            stats["espn_found"] += 1
            photo_filename = f"{athlete_id}.png"
            photo_path = PHOTOS_DIR / photo_filename

            if photo_path.exists() and photo_path.stat().st_size > 1000:
                photo_mapping[pname] = {"source": "espn", "path": f"data/photos/{photo_filename}", "athlete_id": athlete_id}
                stats["espn_downloaded"] += 1
                sys.stdout.write(".")
                sys.stdout.flush()
                continue

            time.sleep(REQUEST_DELAY)
            if download_file(hs_url, photo_path):
                photo_mapping[pname] = {"source": "espn", "path": f"data/photos/{photo_filename}", "athlete_id": athlete_id}
                stats["espn_downloaded"] += 1
                sys.stdout.write("+")
                sys.stdout.flush()
            else:
                stats["no_headshot"] += 1
                sys.stdout.write("x")
                sys.stdout.flush()

        stats["teams_processed"] += 1

    # Save mapping
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)

    return stats, photo_mapping


def validate_photos(stats, photo_mapping):
    """TDD validation for photo crawling."""
    squads = load_squads()

    checks = []

    # Check 1: Total players covered
    total = stats["total_players"]
    mapped = len(photo_mapping)
    coverage = mapped / total * 100 if total > 0 else 0
    checks.append({
        "name": "Photo Coverage",
        "pass": coverage >= 50,
        "detail": f"{mapped}/{total} ({coverage:.1f}%)"
    })

    # Check 2: Photos directory has correct number of files
    photo_files = list(PHOTOS_DIR.glob("*.png")) + list(PHOTOS_DIR.glob("*.jpg"))
    checks.append({
        "name": "Photo Files Exist",
        "pass": len(photo_files) == mapped,
        "detail": f"{len(photo_files)} files, {mapped} in mapping"
    })

    # Check 3: All mapping paths point to existing files
    missing_files = 0
    for pname, info in photo_mapping.items():
        full_path = BASE_DIR / info["path"]
        if not full_path.exists():
            missing_files += 1
    checks.append({
        "name": "All Mapped Files Exist",
        "pass": missing_files == 0,
        "detail": f"{missing_files} missing files"
    })

    # Check 4: No duplicate athlete IDs
    athlete_ids = [v["athlete_id"] for v in photo_mapping.values() if v.get("athlete_id")]
    unique_ids = set(athlete_ids)
    checks.append({
        "name": "No Duplicate Athlete IDs",
        "pass": len(athlete_ids) == len(unique_ids),
        "detail": f"{len(athlete_ids)} IDs, {len(unique_ids)} unique"
    })

    # Check 5: File sizes reasonable (>5KB)
    small_files = 0
    for pname, info in photo_mapping.items():
        full_path = BASE_DIR / info["path"]
        if full_path.exists() and full_path.stat().st_size < 5000:
            small_files += 1
    checks.append({
        "name": "File Sizes Reasonable (>5KB)",
        "pass": small_files == 0,
        "detail": f"{small_files} suspiciously small files"
    })

    # Check 6: Teams processed
    checks.append({
        "name": "All Teams Processed",
        "pass": stats["teams_processed"] == len(squads),
        "detail": f"{stats['teams_processed']}/{len(squads)} teams"
    })

    return checks


def print_report(stats, checks, photo_mapping):
    """Print final report."""
    print("\n" + "=" * 60)
    print("Photo Crawling Report")
    print("=" * 60)
    print(f"Total players: {stats['total_players']}")
    print(f"ESPN headshots found: {stats['espn_found']}")
    print(f"Downloaded: {stats['espn_downloaded']}")
    print(f"No headshot on ESPN: {stats['no_headshot']}")
    print(f"No name match: {stats['no_match']}")
    print(f"Teams processed: {stats['teams_processed']}")

    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"]:
            print(f"  - {err}")

    print(f"\nMapping entries: {len(photo_mapping)}")

    # Source breakdown
    sources = {}
    for v in photo_mapping.values():
        src = v.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    print("Sources:", ", ".join(f"{k}: {v}" for k, v in sources.items()))

    print("\n--- TDD Validation ---")
    all_pass = True
    for check in checks:
        status = "PASS" if check["pass"] else "FAIL"
        if not check["pass"]:
            all_pass = False
        print(f"  [{status}] {check['name']}: {check['detail']}")

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    return all_pass


if __name__ == "__main__":
    stats, photo_mapping = crawl_all_photos()
    checks = validate_photos(stats, photo_mapping)
    all_pass = print_report(stats, checks, photo_mapping)
    sys.exit(0 if all_pass else 1)
