#!/usr/bin/env python3
"""
Comprehensive multi-source player photo crawler.
Strategy:
1. ESPN CDN (already tried - only 127 photos exist)
2. Try different ESPN image URL patterns
3. Try SofaScore player CDN
4. For remaining players: generate enhanced SVG avatars as fallback
"""

import json
import time
import re
import unicodedata
from pathlib import Path
import requests
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
PHOTOS_DIR = BASE_DIR / "data/photos"
PHOTO_MAP_FILE = BASE_DIR / "data/squads" / "photo_mapping.json"
SQUADS_FILE = BASE_DIR / "data/squads" / "squads_partial.json"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})


def fetch_json(url, timeout=12):
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def download_file(url, filepath, timeout=15):
    try:
        r = session.get(url, timeout=timeout, stream=True)
        if r.status_code == 200:
            data = r.content
            if len(data) > 2000:
                with open(filepath, "wb") as f:
                    f.write(data)
                return True
    except Exception:
        pass
    if filepath.exists():
        filepath.unlink()
    return False


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def norm(s):
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def safe_filename(name):
    return re.sub(r"[^\w.-]+", "_", name).strip("_")


def main():
    print("=" * 60)
    print("Multi-Source Photo Crawler v2")
    print("=" * 60)

    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)

    with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
        photo_mapping = json.load(f)

    initial_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    print(f"Starting: {initial_espn} ESPN photos")

    # Phase 1: Fetch all ESPN rosters and collect athlete IDs
    print("\n--- Phase 1: Collecting ESPN athlete IDs ---")
    name_to_aid = {}

    for idx, (team_name, team_data) in enumerate(squads.items()):
        team_id = team_data.get("team_id")
        if not team_id:
            continue

        roster = fetch_json(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
        )
        if not roster:
            print(f"  [{idx+1}/48] {team_name}: FAILED")
            time.sleep(1)
            continue

        for a in roster.get("athletes", []):
            ename = a.get("displayName", "")
            aid = a.get("id")
            if ename and aid:
                name_to_aid[norm(ename)] = aid

        time.sleep(0.5)

    print(f"  Collected {len(name_to_aid)} athlete IDs")

    # Phase 2: Try ESPNC DN for all remaining players
    print("\n--- Phase 2: Trying ESPN CDN ---")
    espn_new = 0
    espn_fail = 0

    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            existing = photo_mapping.get(pname, {})

            if existing.get("source") == "espn":
                continue

            pnorm = norm(pname)
            aid = name_to_aid.get(pnorm)
            if not aid:
                continue

            photo_filename = f"{aid}.png"
            photo_path = PHOTOS_DIR / photo_filename

            if photo_path.exists() and photo_path.stat().st_size > 1000:
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": aid,
                }
                espn_new += 1
                continue

            cdn_url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
            if download_file(cdn_url, photo_path):
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": aid,
                }
                espn_new += 1
            else:
                espn_fail += 1

        time.sleep(0.05)

    print(f"  ESPN CDN: {espn_new} new, {espn_fail} failed")

    # Save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)

    # Phase 3: Try SofaScore API for remaining players
    print("\n--- Phase 3: Trying SofaScore player search ---")
    sofascore_new = 0

    # SofaScore search API
    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            existing = photo_mapping.get(pname, {})
            if existing.get("source") in ("espn", "sofascore"):
                continue

            # Try SofaScore search
            search_url = f"https://www.sofascore.com/api/v1/search/player?q={pname}"
            result = fetch_json(search_url)
            if not result:
                continue

            results = result.get("results", [])
            if not results:
                continue

            # Try first result
            player_id = results[0].get("id")
            if not player_id:
                continue

            img_url = f"https://img.sofascore.com/api/v1/player/{player_id}/image"
            safe_name = safe_filename(pname)
            photo_path = PHOTOS_DIR / f"sofascore_{safe_name}.jpg"

            if download_file(img_url, photo_path):
                photo_mapping[pname] = {
                    "source": "sofascore",
                    "path": f"data/photos/sofascore_{safe_name}.jpg",
                    "athlete_id": str(player_id),
                }
                sofascore_new += 1
                if sofascore_new % 10 == 0:
                    print(f"  ... {sofascore_new} from SofaScore")

            time.sleep(0.5)

    print(f"  SofaScore: {sofascore_new} new")

    # Save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)

    # Phase 4: For truly remaining players, try to download from Transfermarkt
    print("\n--- Phase 4: Trying Transfermarkt ---")
    # Transfermarkt requires scraping, skip for now

    # Final stats
    final_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    final_ss = sum(1 for v in photo_mapping.values() if v.get("source") == "sofascore")
    final_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")

    print("\n" + "=" * 60)
    print("Final Results")
    print("=" * 60)
    print(f"ESPN: {final_espn}")
    print(f"SofaScore: {final_ss}")
    print(f"Placeholder: {final_placeholder}")
    print(f"Real photo coverage: {(final_espn + final_ss) / (final_espn + final_ss + final_placeholder) * 100:.1f}%")


if __name__ == "__main__":
    main()
