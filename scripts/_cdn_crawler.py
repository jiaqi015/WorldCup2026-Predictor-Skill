#!/usr/bin/env python3
"""
Phase 1: Use athlete IDs from ESPN to directly download from ESPN CDN.
The API has 1245 IDs - images may exist on CDN even when API doesn't list headshot URL.
Phase 2: Wikipedia fallback for truly missing images.
"""

import json
import subprocess
import time
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PHOTOS_DIR = BASE_DIR / "data/photos"
PHOTO_MAP_FILE = BASE_DIR / "data/squads" / "photo_mapping.json"
SQUADS_FILE = BASE_DIR / "data/squads" / "squads_partial.json"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def curl_fetch(url):
    """Fetch JSON via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "12", "--retry", "1", url],
            capture_output=True, text=True, timeout=18
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return None


def curl_download(url, filepath):
    """Download file via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "12", "-o", str(filepath), url],
            capture_output=True, timeout=18
        )
        if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 1000:
            return True
        if filepath.exists():
            filepath.unlink()
    except Exception:
        if filepath.exists():
            filepath.unlink()
    return False


def curl_head(url):
    """Quick check if URL exists."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code},%{size_download}",
             "--max-time", "8", url],
            capture_output=True, text=True, timeout=12
        )
        parts = result.stdout.strip().split(",")
        code = int(parts[0]) if parts and parts[0].isdigit() else 0
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return code == 200 and size > 1000
    except Exception:
        return False


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def norm(s):
    """Normalize name for comparison."""
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def main():
    print("=" * 60)
    print("ESPN CDN Direct Photo Crawler")
    print("=" * 60)

    # Load squads
    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)

    # Load existing photo mapping
    photo_mapping = {}
    if PHOTO_MAP_FILE.exists():
        with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
            photo_mapping = json.load(f)

    initial_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    print(f"Initial ESPN photos: {initial_espn}")

    # Step 1: Fetch all ESPN rosters and build a complete athlete ID lookup
    print("\nFetching ESPN rosters for all 48 teams...")
    name_to_aid = {}  # normalized name -> (original ESPN name, athlete_id)

    for idx, (team_name, team_data) in enumerate(squads.items()):
        team_id = team_data.get("team_id")
        if not team_id:
            continue

        roster = curl_fetch(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
        )

        if not roster or "code" in roster:
            # Retry once after delay
            time.sleep(2)
            roster = curl_fetch(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
            )

        if not roster or "code" in roster:
            print(f"  [{idx+1}/48] {team_name}: API FAILED")
            continue

        athletes = roster.get("athletes", [])
        for a in athletes:
            ename = a.get("displayName", "")
            aid = a.get("id")
            if ename and aid:
                n = norm(ename)
                name_to_aid[n] = (ename, aid)

        print(f"  [{idx+1}/48] {team_name}: {len(athletes)} athletes")
        time.sleep(1.5)  # Rate limiting delay

    print(f"\nTotal athlete IDs collected: {len(name_to_aid)}")

    # Step 2: Match our players to ESPN athlete IDs
    print("\nMatching players to athlete IDs and downloading from CDN...")
    new_downloads = 0
    already_exist = 0
    no_id_match = 0
    download_failed = 0

    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            pnorm = norm(pname)

            # Skip if already has ESPN photo
            existing = photo_mapping.get(pname, {})
            if existing.get("source") == "espn":
                already_exist += 1
                continue

            # Find athlete ID
            aid = None
            if pnorm in name_to_aid:
                _, aid = name_to_aid[pnorm]
            else:
                # Try matching by parts
                pparts = pnorm.split()
                if pparts:
                    last = pparts[-1]
                    first_init = pparts[0][0] if pparts[0] else ""
                    for n, (ename, eid) in name_to_aid.items():
                        nparts = n.split()
                        if nparts and nparts[-1] == last:
                            if len(nparts) >= 1 and nparts[0][0] == first_init:
                                aid = eid
                                break
                        elif n == last:  # single name
                            aid = eid
                            break

            if not aid:
                no_id_match += 1
                continue

            # Try ESPN CDN
            photo_filename = f"{aid}.png"
            photo_path = PHOTOS_DIR / photo_filename

            if photo_path.exists() and photo_path.stat().st_size > 1000:
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": aid,
                }
                new_downloads += 1
                continue

            cdn_url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
            if curl_download(cdn_url, photo_path):
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": aid,
                }
                new_downloads += 1
                if new_downloads % 50 == 0:
                    print(f"  ... {new_downloads} new photos downloaded so far")
            else:
                download_failed += 1

            time.sleep(0.05)  # Small delay between downloads

    # Save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)

    final_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    final_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")

    print("\n" + "=" * 60)
    print("CDN Download Results")
    print("=" * 60)
    print(f"Initial ESPN: {initial_espn}")
    print(f"Already existed (skipped): {already_exist}")
    print(f"New ESPN photos: {new_downloads}")
    print(f"Download failed (no CDN image): {download_failed}")
    print(f"No athlete ID match: {no_id_match}")
    print(f"Final ESPN total: {final_espn}")
    print(f"Final placeholder: {final_placeholder}")
    print(f"Coverage: {final_espn / (final_espn + final_placeholder) * 100:.1f}%")


if __name__ == "__main__":
    main()
