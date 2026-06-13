#!/usr/bin/env python3
"""
Multi-source crawler: Try Wikipedia, Transfermarkt, and other sources.
Strategy: For each player without ESPN photo, try Wikipedia first.
"""

import json
import subprocess
import time
import re
import unicodedata
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PHOTOS_DIR = BASE_DIR / "data/photos"
PHOTO_MAP_FILE = BASE_DIR / "data/squads" / "photo_mapping.json"
SQUADS_FILE = BASE_DIR / "data/squads" / "squads_partial.json"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def curl_fetch_json(url):
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "12", "--retry", "1", url],
            capture_output=True, text=True, timeout=18
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def curl_download(url, filepath):
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15", "-o", str(filepath), url],
            capture_output=True, timeout=20
        )
        if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 2000:
            return True
        if filepath.exists():
            filepath.unlink()
    except Exception:
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


def search_wikipedia_image(player_name, team_en=""):
    """
    Search Wikipedia for a player's page and extract the main image.
    Returns image URL or None.
    """
    # Search for the player
    query = f"{player_name} footballer"
    if team_en:
        query += f" {team_en}"
    
    search_url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={urllib.parse.quote(query)}"
        f"&format=json&srlimit=3"
    )
    
    data = curl_fetch_json(search_url)
    if not data:
        return None
    
    pages = data.get("query", {}).get("search", [])
    if not pages:
        return None
    
    # Try each search result until we find one with an image
    for result in pages[:2]:
        page_id = result["pageid"]
        
        # Get page image
        image_url = (
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&prop=pageimages&format=json&piprop=original&pageids={page_id}"
        )
        
        img_data = curl_fetch_json(image_url)
        if not img_data:
            continue
        
        page_info = img_data.get("query", {}).get("pages", {}).get(str(page_id), {})
        original = page_info.get("original", {})
        source = original.get("source", "")
        
        if source and source.lower().endswith(('.jpg', '.jpeg', '.png')):
            return source
        
        # Fallback to thumbnail
        thumbnail = page_info.get("thumbnail", {})
        thumb = thumbnail.get("source", "")
        if thumb:
            return thumb
    
    return None


def main():
    print("=" * 60)
    print("Wikipedia Photo Crawler")
    print("=" * 60)

    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)

    with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
        photo_mapping = json.load(f)

    initial_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    initial_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")
    print(f"Current: ESPN={initial_espn}, Placeholder={initial_placeholder}")

    # Collect players needing photos
    todo = []
    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            pname = player["name"]
            existing = photo_mapping.get(pname, {})
            if existing.get("source") != "espn":
                todo.append((pname, team_name))

    print(f"Players to process: {len(todo)}")

    wiki_success = 0
    wiki_fail = 0

    # Process in small batches with progress
    for i, (pname, team_name) in enumerate(todo):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(todo)} (wiki: {wiki_success} found, {wiki_fail} failed)")
        
        img_url = search_wikipedia_image(pname, team_name)
        
        if img_url:
            safe_name = safe_filename(pname)
            photo_filename = f"wiki_{safe_name}.jpg"
            photo_path = PHOTOS_DIR / photo_filename
            
            if curl_download(img_url, photo_path):
                photo_mapping[pname] = {
                    "source": "wiki",
                    "path": f"data/photos/{photo_filename}",
                    "athlete_id": None,
                }
                wiki_success += 1
            else:
                wiki_fail += 1
        else:
            wiki_fail += 1
        
        # Save every 20
        if i % 20 == 0:
            with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
                json.dump(photo_mapping, f, ensure_ascii=False, indent=2)
        
        time.sleep(1.0)  # Wikipedia rate limit

    # Final save
    with open(PHOTO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(photo_mapping, f, ensure_ascii=False, indent=2)

    final_espn = sum(1 for v in photo_mapping.values() if v.get("source") == "espn")
    final_wiki = sum(1 for v in photo_mapping.values() if v.get("source") == "wiki")
    final_placeholder = sum(1 for v in photo_mapping.values() if v.get("source") == "placeholder")

    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)
    print(f"ESPN photos: {final_espn}")
    print(f"Wikipedia photos: {final_wiki}")
    print(f"Placeholder SVGs: {final_placeholder}")
    print(f"Total coverage: {(final_espn + final_wiki) / (final_espn + final_wiki + final_placeholder) * 100:.1f}%")


if __name__ == "__main__":
    main()
