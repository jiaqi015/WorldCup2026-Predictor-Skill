#!/usr/bin/env python3
"""
Fetch FIFA World Cup 2026 match schedule and odds from ESPN API.
Outputs: data/matches/match_schedule.json
"""

import json
import os
import re
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

R32_SLOTS = [
    ("R1", "2A", "2B"), ("R2", "1E", "3_ABCDF"),
    ("R3", "1F", "2C"), ("R4", "1C", "2F"),
    ("R5", "1I", "3_CDFGH"), ("R6", "2E", "2I"),
    ("R7", "1A", "3_CEFHI"), ("R8", "1L", "3_EHIJK"),
    ("R9", "1D", "3_BEFIJ"), ("R10", "1G", "3_AEHIJ"),
    ("R11", "2K", "2L"), ("R12", "1H", "2J"),
    ("R13", "1B", "3_EFGIJ"), ("R14", "1J", "2H"),
    ("R15", "1K", "3_DEIJL"), ("R16", "2D", "2G"),
]
R16_PAIRS = [
    ("R2", "R5"), ("R1", "R3"), ("R4", "R6"), ("R7", "R8"),
    ("R11", "R12"), ("R9", "R10"), ("R14", "R16"), ("R13", "R15"),
]
QF_PAIRS = [("L1", "L2"), ("L5", "L6"), ("L3", "L4"), ("L7", "L8")]
SF_PAIRS = [("Q1", "Q2"), ("Q3", "Q4")]

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


def _stats_for(teams, matches):
    stats = {team: {"p": 0, "gf": 0, "ga": 0, "gd": 0} for team in teams}
    for match in matches:
        home, away = match.get("home"), match.get("away")
        if home not in stats or away not in stats:
            continue
        home_score, away_score = match.get("homeScore"), match.get("awayScore")
        if home_score is None or away_score is None:
            continue
        stats[home]["gf"] += home_score
        stats[home]["ga"] += away_score
        stats[away]["gf"] += away_score
        stats[away]["ga"] += home_score
        if home_score > away_score:
            stats[home]["p"] += 3
        elif home_score < away_score:
            stats[away]["p"] += 3
        else:
            stats[home]["p"] += 1
            stats[away]["p"] += 1
    for row in stats.values():
        row["gd"] = row["gf"] - row["ga"]
    return stats


def _split_ranked(teams, value_for):
    ordered = sorted(teams, key=lambda team: value_for(team), reverse=True)
    buckets = []
    for team in ordered:
        value = value_for(team)
        if not buckets or buckets[-1][0] != value:
            buckets.append((value, [team]))
        else:
            buckets[-1][1].append(team)
    return [bucket for _, bucket in buckets]


def _rank_group(teams, matches):
    overall = _stats_for(teams, matches)
    final = []
    for points_bucket in _split_ranked(teams, lambda team: overall[team]["p"]):
        buckets = [points_bucket]
        for field in ("p", "gd", "gf"):
            refined = []
            for bucket in buckets:
                if len(bucket) <= 1:
                    refined.append(bucket)
                    continue
                head_to_head = _stats_for(bucket, matches)
                refined.extend(_split_ranked(bucket, lambda team, f=field: head_to_head[team][f]))
            buckets = refined
        for field in ("gd", "gf"):
            refined = []
            for bucket in buckets:
                if len(bucket) <= 1:
                    refined.append(bucket)
                else:
                    refined.extend(_split_ranked(bucket, lambda team, f=field: overall[team][f]))
            buckets = refined
        for bucket in buckets:
            final.extend(sorted(bucket, key=teams.index))
    return final


def _official_seed_map(schedule):
    seeds = {}
    for group, teams in GROUPS.items():
        matches = [
            match for match in schedule.values()
            if match.get("stage") == "group"
            and match.get("group") == group
            and match.get("completed")
            and match.get("homeScore") is not None
            and match.get("awayScore") is not None
        ]
        if len(matches) != 6:
            continue
        ranking = _rank_group(teams, matches)
        for position, team in enumerate(ranking[:3], start=1):
            seeds[team] = f"{position}{group}"
    return seeds


def _parse_seed_label(label):
    match = re.match(r"^Group ([A-L]) Winner$", label or "")
    if match:
        return f"1{match.group(1)}"
    match = re.match(r"^Group ([A-L]) 2nd Place$", label or "")
    if match:
        return f"2{match.group(1)}"
    match = re.match(r"^Third Place Group ([A-L](?:/[A-L])*)$", label or "")
    if match:
        return "3_" + match.group(1).replace("/", "")
    return ""


def _seed_matches(actual_seed, topology_seed):
    if not actual_seed or not topology_seed:
        return False
    if topology_seed.startswith("3_"):
        return actual_seed.startswith("3") and actual_seed[1:] in topology_seed[2:]
    return actual_seed == topology_seed


def _pair_key(first, second):
    return tuple(sorted((first, second)))


def _round_source(label, round_name, prefix, source_slots, by_slot):
    match = re.match(rf"^{re.escape(round_name)} (\d+) Winner$", label or "")
    if match:
        return f"{prefix}{match.group(1)}"
    for slot in source_slots:
        source = by_slot.get(slot)
        if source and source.get("winner") == label:
            return slot
    return ""


def assign_bracket_slots(schedule):
    """Attach one stable internal bracket slot to every knockout fixture."""
    for match in schedule.values():
        match.pop("bracketSlot", None)

    seeds = _official_seed_map(schedule)
    by_slot = {}
    for match in schedule.values():
        if match.get("stage") != "R":
            continue
        home_seed = seeds.get(match.get("home")) or _parse_seed_label(match.get("home"))
        away_seed = seeds.get(match.get("away")) or _parse_seed_label(match.get("away"))
        candidates = []
        for slot, first_seed, second_seed in R32_SLOTS:
            ordered = _seed_matches(home_seed, first_seed) and _seed_matches(away_seed, second_seed)
            reversed_pair = _seed_matches(home_seed, second_seed) and _seed_matches(away_seed, first_seed)
            if ordered or reversed_pair:
                candidates.append(slot)
        if len(candidates) == 1:
            match["bracketSlot"] = candidates[0]
            by_slot[candidates[0]] = match

    def assign_round(stage, round_name, prefix, source_slots, pairs, target_prefix):
        pair_index = {_pair_key(*pair): f"{target_prefix}{index + 1}" for index, pair in enumerate(pairs)}
        matches = sorted(
            (match for match in schedule.values() if match.get("stage") == stage),
            key=lambda match: (match.get("date") or "", match.get("id") or ""),
        )
        for match in matches:
            home_source = _round_source(match.get("home"), round_name, prefix, source_slots, by_slot)
            away_source = _round_source(match.get("away"), round_name, prefix, source_slots, by_slot)
            slot = pair_index.get(_pair_key(home_source, away_source))
            if slot:
                match["bracketSlot"] = slot
                by_slot[slot] = match

    assign_round("L", "Round of 32", "R", [f"R{i}" for i in range(1, 17)], R16_PAIRS, "L")
    assign_round("Q", "Round of 16", "L", [f"L{i}" for i in range(1, 9)], QF_PAIRS, "Q")
    assign_round("S", "Quarterfinal", "Q", [f"Q{i}" for i in range(1, 5)], SF_PAIRS, "S")

    for match in schedule.values():
        if match.get("stage") == "3RD":
            match["bracketSlot"] = "3RD"
            by_slot["3RD"] = match
        elif match.get("stage") == "FINAL":
            match["bracketSlot"] = "FINAL"
            by_slot["FINAL"] = match
    return len(by_slot)

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
        home_score = None
        away_score = None
        home_winner = None
        away_winner = None
        for c in competitors:
            team_name = c.get("team", {}).get("displayName", "")
            cn_name = TEAM_CN.get(team_name, team_name)
            raw_score = c.get("score")
            score = None
            try:
                score = int(raw_score) if raw_score is not None and raw_score != "" else None
            except (TypeError, ValueError):
                score = None
            if c.get("homeAway") == "home":
                home_cn = cn_name
                home_score = score
                home_winner = c.get("winner") is True
            else:
                away_cn = cn_name
                away_score = score
                away_winner = c.get("winner") is True

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

        match = {
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
        if completed and home_score is not None and away_score is not None:
            match["homeScore"] = home_score
            match["awayScore"] = away_score
            if home_winner:
                match["winner"] = home_cn
            elif away_winner:
                match["winner"] = away_cn
            elif home_score > away_score:
                match["winner"] = home_cn
            elif away_score > home_score:
                match["winner"] = away_cn
            else:
                match["winner"] = None
        schedule[match_id] = match

    knockout_count = sum(1 for match in schedule.values() if match["stage"] != "group")
    assigned_slots = assign_bracket_slots(schedule)
    if knockout_count == 32 and assigned_slots != 32:
        print(
            f"Failed to map knockout bracket slots: {assigned_slots}/32 assigned",
            file=sys.stderr,
        )
        sys.exit(1)

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
