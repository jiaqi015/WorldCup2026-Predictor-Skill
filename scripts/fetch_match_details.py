#!/usr/bin/env python3
"""
Fetch detailed match data for completed World Cup matches from ESPN summary API.
Reads: data/matches/match_schedule.json
Outputs: data/matches/match_details.json
"""

import json
import os
import sys
import urllib.request
import time
import unicodedata

# English to Chinese team name mapping
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

# Player name mapping (English to project player metadata).
PLAYER_DATA = {}
PLAYER_DATA_NORMALIZED = {}

PLAYER_DISPLAY_CN = {
    "Julián Quiñones": "胡利安·基尼奥内斯",
    "Érik Lira": "埃里克·利拉",
    "Raúl Jiménez": "劳尔·希门尼斯",
    "Roberto Alvarado": "罗伯托·阿尔瓦拉多",
    "Ladislav Krejcí": "拉迪斯拉夫·克雷伊奇",
    "Ladislav Krejčí": "拉迪斯拉夫·克雷伊奇",
    "Vladimír Coufal": "弗拉迪米尔·曹法尔",
    "Hwang In-Beom": "黄仁范",
    "Lee Kang-In": "李刚仁",
    "Oh Hyeon-Gyu": "吴贤揆",
}


def normalize_name(value):
    """Normalize accents and punctuation for conservative alias matching."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char.lower() for char in value if char.isalnum())

def load_player_mapping():
    """Load player name mapping from JSON file."""
    global PLAYER_DATA, PLAYER_DATA_NORMALIZED
    mapping_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "squads", "player_mapping.json")
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for eng_name, info in data.items():
                if isinstance(info, str):
                    info = {"cn": info}
                if not isinstance(info, dict):
                    continue
                PLAYER_DATA[eng_name] = info
                PLAYER_DATA_NORMALIZED.setdefault(normalize_name(eng_name), []).append((eng_name, info))


def resolve_player(source_name, expected_team):
    """Resolve an ESPN participant against the project mapping within one team."""
    display_cn = PLAYER_DISPLAY_CN.get(source_name)
    candidates = []
    if source_name in PLAYER_DATA:
        candidates.append((source_name, PLAYER_DATA[source_name]))
    candidates.extend(PLAYER_DATA_NORMALIZED.get(normalize_name(source_name), []))

    seen = set()
    for mapped_name, info in candidates:
        candidate_key = (mapped_name, info.get("team"))
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        if info.get("team") != expected_team:
            continue
        alias = info.get("cn") or source_name
        return {
            "source_name": source_name,
            "display_name_cn": display_cn or alias,
            "app_alias": alias,
            "team_cn": expected_team,
            "jersey": info.get("jersey"),
            "position": info.get("position"),
            "mapping_status": "matched_team_player",
            "mapping_key": mapped_name,
        }

    return {
        "source_name": source_name,
        "display_name_cn": display_cn or source_name,
        "app_alias": None,
        "team_cn": expected_team,
        "jersey": None,
        "position": None,
        "mapping_status": "source_only",
        "mapping_key": None,
    }


def add_player_fields(target, prefix, resolved):
    """Flatten player metadata into an event for simple static embedding."""
    target[f"{prefix}_source_name"] = resolved["source_name"]
    target[f"{prefix}_cn"] = resolved["display_name_cn"]
    target[f"{prefix}_app_alias"] = resolved["app_alias"]
    target[f"{prefix}_team_cn"] = resolved["team_cn"]
    target[f"{prefix}_jersey"] = resolved["jersey"]
    target[f"{prefix}_position"] = resolved["position"]
    target[f"{prefix}_mapping_status"] = resolved["mapping_status"]
    target[f"{prefix}_mapping_key"] = resolved["mapping_key"]

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

def parse_key_events(key_events, home_team_id, home_team_cn, away_team_cn):
    """Parse key events to extract goals, cards, etc."""
    events = []
    for event in key_events:
        event_type = event.get("type", {})
        type_id = event_type.get("id")
        type_text = event_type.get("text", "")

        # Goal events (type 70 = goal, 137 = header goal)
        if type_id in ["70", "137"]:
            participants = event.get("participants", [])
            scorer = participants[0].get("athlete", {}).get("displayName", "") if len(participants) > 0 else ""
            assister = participants[1].get("athlete", {}).get("displayName", "") if len(participants) > 1 else None

            team_id = event.get("team", {}).get("id", "")
            team_cn = "home" if team_id == home_team_id else "away"
            expected_team = home_team_cn if team_cn == "home" else away_team_cn

            clock = event.get("clock", {}).get("displayValue", "")

            goal_event = {
                "type": "goal",
                "minute": clock,
                "team": team_cn,
                "team_cn": expected_team,
                "source": "ESPN summary API",
            }
            add_player_fields(goal_event, "scorer", resolve_player(scorer, expected_team))
            if assister:
                add_player_fields(goal_event, "assist", resolve_player(assister, expected_team))

            events.append(goal_event)

        # Yellow card (type 94)
        elif type_id == "94":
            participants = event.get("participants", [])
            player = participants[0].get("athlete", {}).get("displayName", "") if participants else ""
            team_id = event.get("team", {}).get("id", "")
            team_cn = "home" if team_id == home_team_id else "away"
            expected_team = home_team_cn if team_cn == "home" else away_team_cn
            clock = event.get("clock", {}).get("displayValue", "")

            card_event = {
                "type": "yellowCard",
                "minute": clock,
                "team": team_cn,
                "team_cn": expected_team,
                "source": "ESPN summary API",
            }
            add_player_fields(card_event, "player", resolve_player(player, expected_team))
            events.append(card_event)

        # Red card (type 93)
        elif type_id == "93":
            participants = event.get("participants", [])
            player = participants[0].get("athlete", {}).get("displayName", "") if participants else ""
            team_id = event.get("team", {}).get("id", "")
            team_cn = "home" if team_id == home_team_id else "away"
            expected_team = home_team_cn if team_cn == "home" else away_team_cn
            clock = event.get("clock", {}).get("displayValue", "")

            card_event = {
                "type": "redCard",
                "minute": clock,
                "team": team_cn,
                "team_cn": expected_team,
                "source": "ESPN summary API",
            }
            add_player_fields(card_event, "player", resolve_player(player, expected_team))
            events.append(card_event)

    return events

def parse_team_stats(boxscore, home_team_id):
    """Parse team statistics from boxscore."""
    stats = {"home": {}, "away": {}}

    teams = boxscore.get("teams", [])
    for team_data in teams:
        team_info = team_data.get("team", {})
        team_id = team_info.get("id", "")
        side = "home" if team_id == home_team_id else "away"

        for stat in team_data.get("statistics", []):
            name = stat.get("name", "")
            value = stat.get("displayValue", "")

            # Map stat names to simpler keys
            stat_map = {
                "possessionPct": "possession",
                "totalShots": "shots",
                "shotsOnTarget": "shotsOnTarget",
                "wonCorners": "corners",
                "foulsCommitted": "fouls",
                "yellowCards": "yellowCards",
                "redCards": "redCards",
                "offsides": "offsides",
                "saves": "saves",
                "totalPasses": "passes",
                "passPct": "passAccuracy"
            }

            if name in stat_map:
                try:
                    stats[side][stat_map[name]] = float(value) if "." in value else int(value)
                except ValueError:
                    stats[side][stat_map[name]] = value

    return stats

def main():
    # Load player mapping
    load_player_mapping()
    print(f"Loaded {len(PLAYER_DATA)} player name mappings")

    # Load match schedule
    schedule_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "matches", "match_schedule.json")
    if not os.path.exists(schedule_path):
        print("match_schedule.json not found. Run fetch_match_data.py first.", file=sys.stderr)
        sys.exit(1)

    with open(schedule_path, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    # Find completed matches
    completed = [m for m in schedule.values() if m.get("completed")]
    print(f"Found {len(completed)} completed matches")

    if not completed:
        print("No completed matches to process")
        return

    details = {}
    for match in completed:
        match_id = match["id"]
        home_cn = match["home"]
        away_cn = match["away"]
        print(f"\nFetching details for {home_cn} vs {away_cn} (ID: {match_id})...")

        # Fetch summary
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={match_id}"
        summary = fetch_json(url)

        if not summary:
            print(f"  Failed to fetch summary for match {match_id}")
            continue

        # Get home team ID
        header = summary.get("header", {})
        competitors = header.get("competitions", [{}])[0].get("competitors", [])
        home_team_id = None
        home_score = 0
        away_score = 0

        for c in competitors:
            team_id = c.get("id", "")
            score = int(c.get("score", "0"))
            if c.get("homeAway") == "home":
                home_team_id = team_id
                home_score = score
            else:
                away_score = score

        # Get game info (referee, attendance)
        game_info = summary.get("gameInfo", {})
        attendance = game_info.get("attendance")
        referee = None
        officials = game_info.get("officials", [])
        for off in officials:
            if off.get("position", {}).get("name") == "Referee":
                referee = off.get("fullName")
                break

        # Parse key events
        key_events = summary.get("keyEvents", [])
        events = parse_key_events(key_events, home_team_id, home_cn, away_cn)

        # Parse team stats
        boxscore = summary.get("boxscore", {})
        stats = parse_team_stats(boxscore, home_team_id)

        details[match_id] = {
            "matchId": match_id,
            "homeTeamCn": home_cn,
            "awayTeamCn": away_cn,
            "homeScore": home_score,
            "awayScore": away_score,
            "attendance": attendance,
            "referee": referee,
            "events": events,
            "stats": stats
        }

        print(f"  Score: {home_score}-{away_score}")
        print(f"  Events: {len(events)} (goals: {sum(1 for e in events if e['type'] == 'goal')})")
        if referee:
            print(f"  Referee: {referee}")
        if attendance:
            print(f"  Attendance: {attendance}")

        # Rate limiting
        time.sleep(1)

    # Output
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "matches", "match_details.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(f"\nSaved details for {len(details)} matches to {out_path}")

if __name__ == "__main__":
    main()
