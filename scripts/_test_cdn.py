#!/usr/bin/env python3
"""
Test: For teams with 0 ESPN photos (Belgium, Brazil, France, Spain etc),
try downloading directly from ESPN CDN using athlete IDs.
"""
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PHOTOS_DIR = BASE_DIR / "data/photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

def curl_fetch(url):
    result = subprocess.run(["curl", "-s", "--max-time", "10", url], capture_output=True, text=True, timeout=15)
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)
    return None

def curl_download(url, filepath):
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "10", "-o", str(filepath), url],
        capture_output=True, timeout=15
    )
    if result.returncode == 0 and filepath.exists() and filepath.stat().st_size > 1000:
        return True
    if filepath.exists() and filepath.stat().st_size <= 1000:
        filepath.unlink()
    return False

# Load squads
with open(BASE_DIR / "data/squads/squads_partial.json") as f:
    squads = json.load(f)

# Test team: Belgium (team_id=174, 0 ESPN photos currently)
team = squads["Belgium"]
roster = curl_fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/174/roster")

if not roster:
    print("Failed to fetch Belgium roster")
    exit()

athletes = roster["athletes"]

print(f"Belgium: {len(athletes)} athletes")
print()

# Check headshot status
with_hs = [a for a in athletes if a.get("headshot", {}).get("href")]
no_hs = [a for a in athletes if not a.get("headshot", {}).get("href")]
print(f"With headshot URL in API: {len(with_hs)}")
print(f"Without headshot URL in API: {len(no_hs)}")
print()

# Try downloading from CDN for first 5 "no headshot" athletes
print("Trying CDN direct download for athletes WITHOUT headshot URL...")
success = 0
for a in no_hs[:5]:
    aid = a.get("id")
    name = a.get("displayName", "?")
    cdn_url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
    filepath = PHOTOS_DIR / f"_test_{aid}.png"
    
    if curl_download(cdn_url, filepath):
        size = filepath.stat().st_size
        print(f"  {name}: SUCCESS! ({size} bytes)")
        success += 1
    else:
        print(f"  {name}: FAILED")

print(f"\nCDN success: {success}/{len(no_hs[:5])}")

# Also try a few alternate ESPN image URL patterns
print("\nTrying alternate URL patterns...")
for a in no_hs[:3]:
    aid = a.get("id")
    name = a.get("displayName", "?")
    
    patterns = [
        f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png",
        f"https://a.espncdn.com/combiner/i?img=/i/headshots/soccer/players/full/{aid}.png&w=150&h=150",
        f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.jpg",
    ]
    
    for url in patterns:
        result = subprocess.run(
            ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code},%{size_download}",
             "--max-time", "10", url],
            capture_output=True, text=True, timeout=15
        )
        code = result.stdout.strip()
        print(f"  {name} ({aid}): {url.split('/')[-1]} -> {code}")
