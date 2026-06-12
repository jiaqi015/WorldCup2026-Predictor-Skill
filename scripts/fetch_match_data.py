#!/usr/bin/env python3
"""
Fetch FIFA World Cup 2026 match schedule and odds from ESPN API.
Outputs: data/matches/match_schedule.json
"""

import json
import os
import sys
import urllib.request
import time
from datetime import datetime, timezone

# ESPN API endpoint for all World Cup matches
ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=200"

# English to Chinese team name mapping (from index.html FC variable)
TEAM_CN = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国", "Czech Republic": "捷克",
    "Czechia": "捷克", "Canada": "加拿大", "Bosnia and Herzegovina": "波黑", "Bosnia-Herzegovina": "波黑",
    "Qatar": "卡塔尔", "Switzerland": "瑞士", "Brazil": "巴西", "Morocco": "摩洛哥",
    "Haiti": "海地", "Scotland": "苏格兰", "United States": "美国", "USA": "美国",
    "Paraguay": "巴拉圭", "Australia": "澳大利亚", "Türkiye": "土耳其", "Turkey": "土耳其",
    "Germany": "德国", "Curaçao": "库拉索", "Curacao": "库拉索", "Ivory Coast": "科特迪瓦",
    "Côte d'Ivoire": "科特迪瓦", "Ecuador": "厄瓜多尔", "Netherlands": "荷兰", "Japan": "日本",
    "Sweden": "瑞典", "Tunisia": "突尼斯", "Belgium": "比利时", "Egypt": "埃及", "Iran": "伊朗",
    "New Zealand": "新西兰", "Spain": "西班牙", "Cape Verde": "佛得角", "Saudi Arabia": "沙特",
    "Uruguay": "乌拉圭", "France": "法国", "Iraq": "伊拉克", "Senegal": "塞内加尔", "Norway": "挪威",
    "Argentina": "阿根廷", "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦",
    "Portugal": "葡萄牙", "DR Congo": "刚果金", "Congo DR": "刚果金", "Uzbekistan": "乌兹别克",
    "Colombia": "哥伦比亚", "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳",
    "Panama": "巴拿马"
}

# Stage type mapping from ESPN
ESPN_STAGE = {
    13802: "group",
    13801: "R",   # Round of 32
    13800: "L",   # Round of 16
    13799: "Q",   # Quarterfinals
    13798: "S",   # Semifinals
    13797: "3RD", # Third place
    13803: "FINAL"
}

# Group assignments (from index.html GD variable)
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

VENUE_CN = {
    "Estadio Banorte": "巴诺特体育场",
    "Estadio Akron": "阿克伦体育场",
    "BMO Field": "BMO球场",
    "Levi's Stadium": "李维斯体育场",
    "MetLife Stadium": "大都会人寿体育场",
    "Gillette Stadium": "吉列体育场",
    "SoFi Stadium": "SoFi体育场",
    "BC Place": "卑诗体育馆",
    "NRG Stadium": "NRG体育场",
    "AT&T Stadium": "AT&T体育场",
    "Lincoln Financial Field": "林肯金融球场",
    "Estadio BBVA": "BBVA体育场",
    "Mercedes-Benz Stadium": "梅赛德斯-奔驰体育场",
    "Lumen Field": "流明球场",
    "Hard Rock Stadium": "硬石体育场",
    "GEHA Field at Arrowhead Stadium": "箭头体育场GEHA球场",
}

CITY_CN = {
    "Mexico City": "墨西哥城",
    "Guadalajara": "瓜达拉哈拉",
    "Toronto": "多伦多",
    "Santa Clara, California": "加利福尼亚州圣克拉拉",
    "East Rutherford, New Jersey": "新泽西州东卢瑟福",
    "Foxborough, Massachusetts": "马萨诸塞州福克斯伯勒",
    "Inglewood, California": "加利福尼亚州英格尔伍德",
    "Vancouver": "温哥华",
    "Houston, Texas": "得克萨斯州休斯敦",
    "Arlington, Texas": "得克萨斯州阿灵顿",
    "Philadelphia, Pennsylvania": "宾夕法尼亚州费城",
    "Guadalupe": "瓜达卢佩",
    "Atlanta, Georgia": "佐治亚州亚特兰大",
    "Seattle, Washington": "华盛顿州西雅图",
    "Miami Gardens, Florida": "佛罗里达州迈阿密花园",
    "Kansas City, Missouri": "密苏里州堪萨斯城",
}

COUNTRY_CN = {
    "Mexico": "墨西哥",
    "Canada": "加拿大",
    "USA": "美国",
    "United States": "美国",
}

def find_group(home_cn, away_cn):
    """Find which group a match belongs to based on team names."""
    for group, teams in GROUPS.items():
        if home_cn in teams and away_cn in teams:
            return group
    return None

def fetch_json(url):
    """Fetch JSON from URL with retry logic."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
                return None

def main():
    print(f"Fetching match schedule from ESPN API...")
    data = fetch_json(ESPN_API)
    if not data:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)

    events = data.get("events", [])
    print(f"Found {len(events)} matches")

    schedule = {}
    for ev in events:
        match_id = ev.get("id")
        date = ev.get("date")
        comp = ev.get("competitions", [{}])[0]

        # Get venue
        venue_data = comp.get("venue", {})
        venue = None
        if venue_data:
            venue_name = venue_data.get("fullName", "")
            venue_city = venue_data.get("address", {}).get("city", "")
            venue_country = venue_data.get("address", {}).get("country", "")
            venue = {
                "name": venue_name,
                "name_cn": VENUE_CN.get(venue_name, venue_name),
                "city": venue_city,
                "city_cn": CITY_CN.get(venue_city, venue_city),
                "country": venue_country,
                "country_cn": COUNTRY_CN.get(venue_country, venue_country),
            }

        # Get teams
        competitors = comp.get("competitors", [])
        home_cn = None
        away_cn = None
        for c in competitors:
            team_name = c.get("team", {}).get("displayName", "")
            cn_name = TEAM_CN.get(team_name, team_name)
            if c.get("homeAway") == "home":
                home_cn = cn_name
            else:
                away_cn = cn_name

        # Get stage
        stage_type = ev.get("season", {}).get("type", 0)
        stage = ESPN_STAGE.get(stage_type, "unknown")

        # Get group for group stage matches
        group = None
        if stage == "group":
            group = find_group(home_cn, away_cn)

        # Get odds
        odds_data = None
        odds_list = comp.get("odds", [])
        if odds_list and odds_list[0] is not None:
            od = odds_list[0]
            home_odds = od.get("homeTeamOdds", {})
            away_odds = od.get("awayTeamOdds", {})
            draw_odds = od.get("drawOdds", {})
            odds_data = {
                "provider": od.get("provider", {}).get("name", "DraftKings"),
                "homeML": home_odds.get("moneyLine"),
                "awayML": away_odds.get("moneyLine"),
                "drawML": draw_odds.get("moneyLine"),
                "spread": od.get("spread"),
                "overUnder": od.get("overUnder"),
                "details": od.get("details", "")
            }

        # Get status
        status = comp.get("status", {}).get("type", {}).get("name", "")
        completed = comp.get("status", {}).get("type", {}).get("completed", False)

        schedule[match_id] = {
            "id": match_id,
            "date": date,
            "stage": stage,
            "group": group,
            "home": home_cn,
            "away": away_cn,
            "venue": venue,
            "odds": odds_data,
            "status": status,
            "completed": completed
        }

    # Output
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "matches")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "match_schedule.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    manifest = {
        "schema_version": 1,
        "source": "ESPN public scoreboard API",
        "source_url": ESPN_API,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "tournament": "FIFA World Cup 2026",
        "match_count": len(schedule),
        "completed_count": sum(1 for match in schedule.values() if match["completed"]),
        "status": (
            "Live external snapshot. ESPN fields, status values, and odds "
            "availability may change without notice."
        ),
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(schedule)} matches to {out_path}")
    print(f"Saved source manifest to {manifest_path}")

    # Summary
    completed = sum(1 for m in schedule.values() if m["completed"])
    with_odds = sum(1 for m in schedule.values() if m["odds"])
    with_venue = sum(1 for m in schedule.values() if m["venue"])
    print(f"  Completed: {completed}")
    print(f"  With odds: {with_odds}")
    print(f"  With venue: {with_venue}")

if __name__ == "__main__":
    main()
