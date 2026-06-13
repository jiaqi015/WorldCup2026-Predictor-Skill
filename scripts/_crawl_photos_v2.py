#!/usr/bin/env python3
"""
Enhanced photo crawler using curl subprocess to avoid Python SSL issues.
Features:
- Rate limiting with configurable delays
- Loads existing photo_mapping as base
- Saves progress after each team
- Better name matching with multiple strategies
- Retry logic for failed teams
"""

import json
import subprocess
import time
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SQUADS_FILE = DATA_DIR / "squads" / "squads_partial.json"
PHOTOS_DIR = DATA_DIR / "photos"
PHOTO_MAP_FILE = DATA_DIR / "squads" / "photo_mapping.json"

DELAY_BETWEEN_TEAMS = 2.0  # seconds between teams
DELAY_BETWEEN_DOWNLOADS = 0.3  # seconds between individual downloads
MAX_RETRIES = 3


def curl_fetch(url):
    """Fetch URL using curl subprocess."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "15", "--retry", "2", url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception:
        return None


def curl_download(url, filepath):
    """Download file using curl subprocess."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15", "-o", str(filepath), url],
            capture_output=True, timeout=20
        )
        if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 1000:
            return True
        return False
    except Exception:
        return False


def strip_accents(s):
    """Remove accents from a string."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.combining(c)
    )


def normalize_name(name):
    """Normalize name for comparison."""
    n = name.lower().strip()
    n = strip_accents(n)
    # Remove middle initials with dots
    n = re.sub(r'\s+\w\.\s+', ' ', n)
    # Remove special chars
    n = re.sub(r'[^\w\s-]', '', n)
    # Normalize whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def name_match_score(name1, name2):
    """Calculate how well two names match (0-1)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    if n1 == n2:
        return 1.0
    
    parts1 = n1.split()
    parts2 = n2.split()
    
    # Check if one contains the other
    if n1 in n2 or n2 in n1:
        # But avoid false positives (e.g., "John" matching "Johnson")
        if abs(len(n1) - len(n2)) < 5:
            return 0.9
        else:
            return 0.5
    
    # Check last name match
    if len(parts1) >= 1 and len(parts2) >= 1:
        if parts1[-1] == parts2[-1]:
            # Last name matches
            if len(parts1) >= 2 and len(parts2) >= 2:
                if parts1[0][0] == parts2[0][0]:
                    return 0.85  # Last name + first initial match
                return 0.7  # Just last name match
            return 0.7
    
    # Check first name match
    if len(parts1) >= 1 and len(parts2) >= 1:
        if parts1[0] == parts2[0]:
            return 0.6
    
    return 0.0


def crawl_all_photos():
    """Main enhanced crawling function."""
    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)
    
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing photo mapping as base
    photo_mapping = {}
    if PHOTO_MAP_FILE.exists():
        with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
            photo_mapping = json.load(f)
    
    initial_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    initial_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")
    
    stats = {
        "total_players": 0,
        "espn_found": 0,
        "new_downloads": 0,
        "already_had": 0,
        "no_headshot": 0,
        "no_match": 0,
        "teams_processed": 0,
        "api_errors": 0,
    }
    
    teams_list = list(squads.items())
    total_teams = len(teams_list)
    
    for idx, (team_name, team_data) in enumerate(teams_list):
        team_id = team_data.get("team_id")
        if not team_id:
            stats["api_errors"] += 1
            continue
        
        # Fetch roster from ESPN
        roster_data = curl_fetch(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
        )
        
        if not roster_data:
            print(f"[{idx+1}/{total_teams}] {team_name}: API ERROR")
            stats["api_errors"] += 1
            stats["teams_processed"] += 1
            time.sleep(DELAY_BETWEEN_TEAMS)
            continue
        
        athletes = roster_data.get("athletes", [])
        
        # Build ESPN athlete lookup
        espn_athletes = {}
        for a in athletes:
            aid = a.get("id")
            name = a.get("displayName", "")
            headshot = a.get("headshot", {})
            hs_url = headshot.get("href") if headshot else None
            if aid and name:
                espn_athletes[name] = (aid, hs_url, name)
        
        new_for_team = 0
        no_hs_team = 0
        no_match_team = 0
        
        for player in team_data.get("players", []):
            stats["total_players"] += 1
            pname = player["name"]
            
            # Skip if already has ESPN photo
            if photo_mapping.get(pname, {}).get("source") == "espn":
                stats["already_had"] += 1
                continue
            
            # Try to match with ESPN athletes
            best_match = None
            best_score = 0.7  # Minimum threshold
            
            for ename, (aid, hs_url, _) in espn_athletes.items():
                score = name_match_score(pname, ename)
                if score > best_score:
                    best_score = score
                    best_match = (aid, hs_url, ename)
            
            if not best_match:
                no_match_team += 1
                stats["no_match"] += 1
                continue
            
            athlete_id, hs_url, matched_name = best_match
            
            if not hs_url:
                no_hs_team += 1
                stats["no_headshot"] += 1
                continue
            
            stats["espn_found"] += 1
            photo_filename = f"{athlete_id}.png"
            photo_path = PHOTOS_DIR / photo_filename
            
            if photo_path.exists() and photo_path.stat().st_size > 1000:
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": athlete_id,
                }
                new_for_team += 1
                stats["new_downloads"] += 1
                continue
            
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
            if curl_download(hs_url, photo_path):
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": athlete_id,
                }
                new_for_team += 1
                stats["new_downloads"] += 1
        
        stats["teams_processed"] += 1
        
        status = f"[{idx+1}/{total_teams}] {team_name}: "
        if new_for_team > 0:
            status += f"+{new_for_team} new photos"
        else:
            status += "no new"
        status += f" (no_match={no_match_team}, no_hs={no_hs_team})"
        print(status)
        
        # Save progress after each team
        with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(photo_mapping, f, ensure_ascii=False, indent=2)
        
        time.sleep(DELAY_BETWEEN_TEAMS)
    
    # Final save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)
    
    # Final stats
    final_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    final_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")
    
    print("\n" + "=" * 60)
    print("Crawl Complete")
    print("=" * 60)
    print(f"Total players: {stats['total_players']}")
    print(f"Initial ESPN: {initial_espn}, New: {stats['new_downloads']}, Final ESPN: {final_espn}")
    print(f"Initial placeholder: {initial_placeholder}, Final placeholder: {final_placeholder}")
    print(f"No headshot on ESPN: {stats['no_headshot']}")
    print(f"No name match: {stats['no_match']}")
    print(f"API errors: {stats['api_errors']}")
    
    return photo_mapping


if __name__ == "__main__":
    crawl_all_photos()
