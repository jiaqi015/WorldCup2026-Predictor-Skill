#!/usr/bin/env python3
"""Test Wikipedia API success rate with a small sample."""
import json, subprocess, time, re, unicodedata, urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PHOTOS_DIR = BASE_DIR / "data/photos"

def curl_fetch_json(url):
    result = subprocess.run(
        ["curl", "-s", "--max-time", "10", url],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return None

def curl_download(url, filepath):
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "12", "-o", str(filepath), url],
        capture_output=True, timeout=18
    )
    if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 2000:
        return True
    if filepath.exists():
        filepath.unlink()
    return False

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def safe_filename(name):
    return re.sub(r"[^\w.-]+", "_", name).strip("_")

def search_wiki(player_name):
    query = f"{player_name} footballer"
    search_url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={urllib.parse.quote(query)}"
        f"&format=json&srlimit=2"
    )
    data = curl_fetch_json(search_url)
    if not data:
        return None
    
    pages = data.get("query", {}).get("search", [])
    if not pages:
        return None
    
    for r in pages[:1]:
        pid = r["pageid"]
        img_url = (
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&prop=pageimages&format=json&piprop=original&pageids={pid}"
        )
        img_data = curl_fetch_json(img_url)
        if not img_data:
            continue
        pi = img_data.get("query", {}).get("pages", {}).get(str(pid), {})
        orig = pi.get("original", {})
        src = orig.get("source", "")
        if src and src.lower().endswith(('.jpg', '.jpeg', '.png')):
            return src
        thumb = pi.get("thumbnail", {}).get("source", "")
        if thumb:
            return thumb
    return None

def main():
    with open(BASE_DIR / "data/squads/squads_partial.json") as f:
        squads = json.load(f)
    with open(BASE_DIR / "data/squads/photo_mapping.json") as f:
        pm = json.load(f)

    # Test players from teams with 0 ESPN photos
    test_players = []
    for team_name in ["France", "Brazil", "Spain", "Belgium", "Germany", "England", "Portugal", "Scotland"]:
        for p in squads[team_name]["players"][:3]:
            if pm.get(p["name"], {}).get("source") != "espn":
                test_players.append((p["name"], team_name))
        if len(test_players) >= 20:
            break

    print(f"Testing Wikipedia with {len(test_players)} players...\n")

    success = 0
    for pname, team in test_players:
        img_url = search_wiki(pname)
        if img_url:
            sf = safe_filename(pname)
            fp = PHOTOS_DIR / f"wiki_test_{sf}.jpg"
            if curl_download(img_url, fp):
                print(f"  OK: {pname} ({team}) -> {fp.stat().st_size} bytes")
                success += 1
            else:
                print(f"  DL_FAIL: {pname} ({team})")
        else:
            print(f"  NO_IMG: {pname} ({team})")
        time.sleep(1)

    print(f"\nSuccess: {success}/{len(test_players)} ({success/len(test_players)*100:.0f}%)")

if __name__ == "__main__":
    main()
