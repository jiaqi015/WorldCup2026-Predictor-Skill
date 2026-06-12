#!/usr/bin/env python3
"""Fetch a dated ESPN public roster snapshot for the 48-team predictor."""

import json
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

# Output path
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "squads"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Team groups for 2026 World Cup
GROUPS = {
    "A": ["墨西哥", "南非", "韩国", "捷克"],
    "B": ["加拿大", "波黑", "卡塔尔", "瑞士"],
    "C": ["巴西", "摩洛哥", "海地", "苏格兰"],
    "D": ["美国", "巴拉圭", "澳大利亚", "土耳其"],
    "E": ["德国", "库拉索", "科特迪瓦", "厄瓜多尔"],
    "F": ["荷兰", "日本", "瑞典", "突尼斯"],
    "G": ["比利时", "埃及", "伊朗", "新西兰"],
    "H": ["西班牙", "佛得角", "沙特", "乌拉圭"],
    "I": ["法国", "伊拉克", "塞内加尔", "挪威"],
    "J": ["阿根廷", "阿尔及利亚", "奥地利", "约旦"],
    "K": ["葡萄牙", "刚果金", "乌兹别克", "哥伦比亚"],
    "L": ["英格兰", "克罗地亚", "加纳", "巴拿马"]
}

# English team names for API queries
TEAM_EN_NAMES = {
    "墨西哥": "Mexico", "南非": "South Africa", "韩国": "South Korea", "捷克": "Czechia",
    "加拿大": "Canada", "波黑": "Bosnia and Herzegovina", "卡塔尔": "Qatar", "瑞士": "Switzerland",
    "巴西": "Brazil", "摩洛哥": "Morocco", "海地": "Haiti", "苏格兰": "Scotland",
    "美国": "United States", "巴拉圭": "Paraguay", "澳大利亚": "Australia", "土耳其": "Turkey",
    "德国": "Germany", "库拉索": "Curacao", "科特迪瓦": "Ivory Coast", "厄瓜多尔": "Ecuador",
    "荷兰": "Netherlands", "日本": "Japan", "瑞典": "Sweden", "突尼斯": "Tunisia",
    "比利时": "Belgium", "埃及": "Egypt", "伊朗": "Iran", "新西兰": "New Zealand",
    "西班牙": "Spain", "佛得角": "Cape Verde", "沙特": "Saudi Arabia", "乌拉圭": "Uruguay",
    "法国": "France", "伊拉克": "Iraq", "塞内加尔": "Senegal", "挪威": "Norway",
    "阿根廷": "Argentina", "阿尔及利亚": "Algeria", "奥地利": "Austria", "约旦": "Jordan",
    "葡萄牙": "Portugal", "刚果金": "DR Congo", "乌兹别克": "Uzbekistan", "哥伦比亚": "Colombia",
    "英格兰": "England", "克罗地亚": "Croatia", "加纳": "Ghana", "巴拿马": "Panama"
}

# Position mapping (English to Chinese)
POSITION_MAP = {
    "Goalkeeper": "门将",
    "Defender": "后卫",
    "Midfielder": "中场",
    "Forward": "前锋",
    "Left Winger": "边锋",
    "Right Winger": "边锋",
    "Centre-Forward": "中锋",
    "Attacking Midfield": "前腰",
    "Defensive Midfield": "后腰",
    "Central Midfield": "中前卫",
    "Left-Back": "边卫",
    "Right-Back": "边卫",
    "Centre-Back": "中卫"
}


def fetch_with_retry(url, headers=None, max_retries=3, timeout=15):
    """Fetch URL with retry logic."""
    if headers is None:
        headers = {"User-Agent": "WorldCup2026Predictor/1.0"}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}/{max_retries}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


def calculate_age(birth_date_str):
    """Calculate age from birth date string."""
    if not birth_date_str:
        return None
    try:
        # Try different date formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                birth_date = datetime.strptime(birth_date_str[:10], fmt)
                today = datetime(2026, 6, 12)  # World Cup start date
                age = today.year - birth_date.year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                return age
            except ValueError:
                continue
        return None
    except:
        return None


def fetch_from_espn_api():
    """Fetch squad data from ESPN API."""
    print("Fetching from ESPN API...")
    squads = {}

    # Get all teams first
    teams_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams"
    try:
        teams_data = fetch_with_retry(teams_url)
        teams = teams_data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', [])

        for team_info in teams:
            team = team_info.get('team', {})
            team_id = team.get('id')
            team_name = team.get('displayName')

            # Try to get roster
            roster_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
            try:
                roster_data = fetch_with_retry(roster_url, max_retries=2)
                athletes = roster_data.get('athletes', [])

                if athletes:
                    squads[team_name] = {
                        "team_id": team_id,
                        "players": []
                    }
                    for athlete in athletes:
                        player = {
                            "id": athlete.get('id'),
                            "name": athlete.get('displayName', ''),
                            "jersey": athlete.get('jersey', ''),
                            "position": athlete.get('position', {}).get('abbreviation', ''),
                            "age": athlete.get('age'),
                            "birth_date": athlete.get('dateOfBirth', ''),
                            "nationality": athlete.get('citizenship', '')
                        }
                        squads[team_name]["players"].append(player)

                    print(f"  ✓ {team_name}: {len(athletes)} players")
            except Exception as e:
                print(f"  ✗ {team_name}: {e}")
                continue

            time.sleep(0.5)  # Rate limiting

    except Exception as e:
        print(f"ESPN API failed: {e}")

    return squads


def save_squads(squads, filename="squads_partial.json"):
    """Save squads to JSON file."""
    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(squads, f, ensure_ascii=False, indent=2)
    manifest = {
        "schema_version": 1,
        "source": "ESPN public site API",
        "teams_endpoint": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams",
        "roster_endpoint_template": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "team_count": len(squads),
        "player_count": sum(len(team.get("players", [])) for team in squads.values()),
        "status": "source snapshot; not a final FIFA registration list"
    }
    with open(OUTPUT_DIR / "manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {output_path}")
    return output_path


def main():
    """Main function to fetch squad data."""
    print("=" * 60)
    print("2026 World Cup Squad Fetcher")
    print("=" * 60)

    # Check for existing partial data
    existing_file = OUTPUT_DIR / "squads_partial.json"
    existing_squads = {}
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_squads = json.load(f)
        print(f"Loaded {len(existing_squads)} existing teams")

    # Fetch from ESPN API
    espn_squads = fetch_from_espn_api()

    # Merge with existing data
    all_squads = {**existing_squads, **espn_squads}

    # Save partial results
    if all_squads:
        save_squads(all_squads)

    print(f"\nTotal teams collected: {len(all_squads)}")
    print(f"Teams needed: {48}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
