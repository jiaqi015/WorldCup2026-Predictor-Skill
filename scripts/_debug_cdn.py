#!/usr/bin/env python3
"""Debug ESPN CDN: Check if CDN has images for athletes without API headshot URLs."""
import json, subprocess

result = subprocess.run(
    ["curl", "-s", "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/174/roster"],
    capture_output=True, text=True, timeout=15
)
data = json.loads(result.stdout)
athletes = data.get("athletes", [])

with_hs = [a for a in athletes if a.get("headshot", {}).get("href")]
no_hs = [a for a in athletes if not a.get("headshot", {}).get("href")]

print(f"Belgium: {len(with_hs)} with headshot URL, {len(no_hs)} without")
print()

# Test CDN for first 5 "no headshot" athletes
print("=== Testing CDN for athletes WITHOUT headshot URL ===")
for a in no_hs[:5]:
    aid = a["id"]
    name = a["displayName"]
    url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
    r = subprocess.run(
        ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code},%{size_download}", "--max-time", "8", url],
        capture_output=True, text=True, timeout=12
    )
    print(f"  {name} (id={aid}): {r.stdout.strip()}")

# Test a "with headshot" athlete as control
print("\n=== Control: athlete WITH headshot URL ===")
if with_hs:
    a = with_hs[0]
    aid = a["id"]
    name = a["displayName"]
    url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{aid}.png"
    r = subprocess.run(
        ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code},%{size_download}", "--max-time", "8", url],
        capture_output=True, text=True, timeout=12
    )
    print(f"  {name} (id={aid}): {r.stdout.strip()}")

# Test alternate patterns
print("\n=== Alternate patterns ===")
test_aid = no_hs[0]["id"]
patterns = [
    f"https://a.espncdn.com/i/headshots/soccer/players/full/{test_aid}.png",
    f"https://a.espncdn.com/combiner/i?img=/i/headshots/soccer/players/full/{test_aid}.png&w=350&h=254",
    f"https://a.espncdn.com/i/headshots/soccer/players/full/{test_aid}.jpg",
]
for url in patterns:
    r = subprocess.run(
        ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code},%{size_download}", "--max-time", "8", url],
        capture_output=True, text=True, timeout=12
    )
    print(f"  {r.stdout.strip()}")
