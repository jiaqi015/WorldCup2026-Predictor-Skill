#!/usr/bin/env python3
"""
Multi-source photo crawler:
1. Try constructing ESPN CDN URLs directly from athlete IDs (even if API doesn't list headshot)
2. Try Wikipedia API for player photos
3. Try alternative image sources
"""

import json
import subprocess
import time
import re
import unicodedata
from pathlib import Path
import urllib.parse

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SQUADS_FILE = DATA_DIR / "squads" / "squads_partial.json"
PHOTOS_DIR = DATA_DIR / "photos"
PHOTO_MAP_FILE = DATA_DIR / "squads" / "photo_mapping.json"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def curl_fetch(url):
    """Fetch URL using curl subprocess."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "15", url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return result.stdout
        return None
    except Exception:
        return None


def curl_check_url(url):
    """Check if URL exists and has content."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code},%{size_download}",
             "--max-time", "10", url],
            capture_output=True, text=True, timeout=15
        )
        parts = result.stdout.strip().split(",")
        code = int(parts[0]) if parts[0].isdigit() else 0
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return code == 200 and size > 1000
    except Exception:
        return False


def curl_download(url, filepath):
    """Download file using curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15", "-o", str(filepath), url],
            capture_output=True, timeout=20
        )
        if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 1000:
            return True
        # Clean up small/bad files
        if filepath.exists() and filepath.stat().st_size <= 1000:
            filepath.unlink()
        return False
    except Exception:
        if filepath.exists():
            filepath.unlink()
        return False


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def normalize_name(name):
    n = name.lower().strip()
    n = strip_accents(n)
    n = re.sub(r'\s+\w\.\s+', ' ', n)
    n = re.sub(r'[^\w\s-]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def search_wikipedia(player_name):
    """Search Wikipedia for a player and get image URL."""
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(player_name)}+footballer&format=json&srlimit=3"
    
    data = curl_fetch(search_url)
    if not data or isinstance(data, str):
        return None
    
    pages = data.get("query", {}).get("search", [])
    if not pages:
        return None
    
    # Get the first result's page ID
    page_id = pages[0]["pageid"]
    
    # Get the image from the page
    image_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&pageids={page_id}"
    img_data = curl_fetch(image_url)
    if not img_data or isinstance(img_data, str):
        return None
    
    pages_info = img_data.get("query", {}).get("pages", {})
    page_info = pages_info.get(str(page_id), {})
    original = page_info.get("original", {})
    source = original.get("source", "")
    
    if source:
        return source
    
    # Fallback: get thumbnail
    thumbnail = page_info.get("thumbnail", {})
    thumb_source = thumbnail.get("source", "")
    return thumb_source if thumb_source else None


def try_espn_cdn(athlete_id):
    """Try standard ESPN CDN URL."""
    url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{athlete_id}.png"
    return curl_check_url(url)


def try_sofascore_api(player_name):
    """Try SofaScore search for player image."""
    # SofaScore uses an internal API
    search_url = f"https://www.sofascore.com/api/v1/search/player?q={urllib.parse.quote(player_name)}"
    return None  # SofaScore API requires special headers/auth


def main():
    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)
    
    # Load existing photo mapping
    photo_mapping = {}
    if PHOTO_MAP_FILE.exists():
        with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
            photo_mapping = json.load(f)
    
    initial_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    
    # Step 1: Try ESPN CDN URLs for all athletes that have IDs but no headshot
    print("=" * 60)
    print("Phase 1: Trying ESPN CDN direct URLs for athletes with IDs")
    print("=" * 60)
    
    espn_new = 0
    
    # First, gather all athlete IDs from ESPN API
    athlete_ids_by_name = {}
    teams_list = list(squads.items())
    
    for idx, (team_name, team_data) in enumerate(teams_list):
        team_id = team_data.get("team_id")
        if not team_id:
            continue
        
        roster_data = curl_fetch(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
        )
        if not roster_data:
            continue
        
        for a in roster_data.get("athletes", []):
            name = a.get("displayName", "")
            aid = a.get("id")
            if name and aid:
                athlete_ids_by_name[name] = aid
        
        time.sleep(1)
    
    print(f"Fetched {len(athlete_ids_by_name)} athlete IDs from ESPN")
    
    # Now try direct CDN URLs
    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            existing = photo_mapping.get(pname, {})
            if existing.get("source") == "espn":
                continue
            
            # Try to find athlete ID from ESPN roster
            aid = athlete_ids_by_name.get(pname)
            if not aid:
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
                espn_new += 1
                continue
            
            # Download
            cdn_url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
            if curl_download(cdn_url, photo_path):
                photo_mapping[pname] = {
                    "source": "espn",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": aid,
                }
                espn_new += 1
                if espn_new % 10 == 0:
                    print(f"  Downloaded {espn_new} new photos via ESPN CDN...")
            time.sleep(0.1)
    
    print(f"ESPN CDN direct: {espn_new} new photos")
    
    # Save progress
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)
    
    # Step 2: Try Wikipedia for remaining players
    print("\n" + "=" * 60)
    print("Phase 2: Trying Wikipedia API for remaining players")
    print("=" * 60)
    
    wiki_new = 0
    remaining = sum(1 for v in photo_mapping.values() if v.get("source") != "espn")
    print(f"Remaining players without ESPN photo: {remaining}")
    
    # Only try Wikipedia for a sample first to gauge success rate
    sample_count = 0
    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            existing = photo_mapping.get(pname, {})
            if existing.get("source") == "espn":
                continue
            if existing.get("source") == "wiki":
                continue
            
            if sample_count >= 10:  # Test with 10 first
                break
            
            print(f"  Searching Wikipedia for: {pname}...")
            img_url = search_wikipedia(pname)
            if img_url:
                print(f"    Found: {img_url[:80]}...")
                # Download
                safe_name = re.sub(r"[^\w.-]+", "_", pname).strip("_")
                photo_filename = f"{safe_name}.jpg"
                photo_path = PHOTOS_DIR / photo_filename
                if curl_download(img_url, photo_path):
                    photo_mapping[pname] = {
                        "source": "wiki",
                        "path": f"data/photos/{photo_filename}",
                        "athlete_id": None,
                    }
                    wiki_new += 1
                    print(f"    Downloaded!")
                else:
                    print(f"    Download failed")
            else:
                print(f"    No image found")
            
            sample_count += 1
            time.sleep(1)
        if sample_count >= 10:
            break
    
    print(f"\nWikipedia sample: {wiki_new}/10 found")
    
    # Final save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)
    
    final_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    final_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")
    final_wiki = sum(1 for v in photo_mapping.values() if v.get("source") == "wiki")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Initial ESPN: {initial_espn}")
    print(f"New ESPN (CDN direct): {espn_new}")
    print(f"New Wikipedia: {wiki_new}")
    print(f"Final ESPN: {final_espn}")
    print(f"Final placeholder: {final_placeholder}")
    print(f"Final Wikipedia: {final_wiki}")


if __name__ == "__main__":
    main()
