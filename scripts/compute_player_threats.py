#!/usr/bin/env python3
"""
Compute player threat multipliers (goal + assist separately) for 140-200 key players.

Data sources:
- data/squads/squads_partial.json (1248 players, name/position/age)
- data/squads/player_mapping.json (English->Chinese name mapping)
- Embedded PL/POS/STAR_PLAYER variables from index.html (extracted at runtime)

Output: data/prediction/player_threats.json
"""

import json
import math
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
SQUADS_FILE = BASE / "data" / "squads" / "squads_partial.json"
MAPPING_FILE = BASE / "data" / "squads" / "player_mapping.json"
INDEX_FILE = BASE / "index.html"
OUTPUT_FILE = BASE / "data" / "prediction" / "player_threats.json"

TEAMS_48 = [
    "墨西哥","南非","韩国","捷克","加拿大","波黑","卡塔尔","瑞士",
    "巴西","摩洛哥","海地","苏格兰","美国","巴拉圭","澳大利亚","土耳其",
    "德国","库拉索","科特迪瓦","厄瓜多尔","荷兰","日本","瑞典","突尼斯",
    "比利时","埃及","伊朗","新西兰","西班牙","佛得角","沙特","乌拉圭",
    "法国","伊拉克","塞内加尔","挪威","阿根廷","阿尔及利亚","奥地利","约旦",
    "葡萄牙","刚果金","乌兹别克","哥伦比亚","英格兰","克罗地亚","加纳","巴拿马",
]

TEAM_EN = {
    "墨西哥":"Mexico","南非":"South Africa","韩国":"South Korea","捷克":"Czechia",
    "加拿大":"Canada","波黑":"Bosnia-Herzegovina","卡塔尔":"Qatar","瑞士":"Switzerland",
    "巴西":"Brazil","摩洛哥":"Morocco","海地":"Haiti","苏格兰":"Scotland",
    "美国":"United States","巴拉圭":"Paraguay","澳大利亚":"Australia","土耳其":"Türkiye",
    "德国":"Germany","库拉索":"Curaçao","科特迪瓦":"Ivory Coast","厄瓜多尔":"Ecuador",
    "荷兰":"Netherlands","日本":"Japan","瑞典":"Sweden","突尼斯":"Tunisia",
    "比利时":"Belgium","埃及":"Egypt","伊朗":"Iran","新西兰":"New Zealand",
    "西班牙":"Spain","佛得角":"Cape Verde","沙特":"Saudi Arabia","乌拉圭":"Uruguay",
    "法国":"France","伊拉克":"Iraq","塞内加尔":"Senegal","挪威":"Norway",
    "阿根廷":"Argentina","阿尔及利亚":"Algeria","奥地利":"Austria","约旦":"Jordan",
    "葡萄牙":"Portugal","刚果金":"DR Congo","乌兹别克":"Uzbekistan","哥伦比亚":"Colombia",
    "英格兰":"England","克罗地亚":"Croatia","加纳":"Ghana","巴拿马":"Panama",
}

# ESPN team name -> Chinese team name
ESPN_TO_CN = {
    "Algeria": "阿尔及利亚", "Argentina": "阿根廷", "Australia": "澳大利亚",
    "Austria": "奥地利", "Belgium": "比利时", "Bosnia-Herzegovina": "波黑",
    "Brazil": "巴西", "Canada": "加拿大", "Cape Verde": "佛得角",
    "Colombia": "哥伦比亚", "Congo DR": "刚果金", "Croatia": "克罗地亚",
    "Curaçao": "库拉索", "Czechia": "捷克", "Ecuador": "厄瓜多尔",
    "Egypt": "埃及", "England": "英格兰", "France": "法国",
    "Germany": "德国", "Ghana": "加纳", "Haiti": "海地",
    "Iran": "伊朗", "Iraq": "伊拉克", "Ivory Coast": "科特迪瓦",
    "Japan": "日本", "Jordan": "约旦", "Mexico": "墨西哥",
    "Morocco": "摩洛哥", "Netherlands": "荷兰", "New Zealand": "新西兰",
    "Norway": "挪威", "Panama": "巴拿马", "Paraguay": "巴拉圭",
    "Portugal": "葡萄牙", "Qatar": "卡塔尔", "Saudi Arabia": "沙特",
    "Scotland": "苏格兰", "Senegal": "塞内加尔", "South Africa": "南非",
    "South Korea": "韩国", "Spain": "西班牙", "Sweden": "瑞典",
    "Switzerland": "瑞士", "Tunisia": "突尼斯", "Türkiye": "土耳其",
    "United States": "美国", "Uruguay": "乌拉圭", "Uzbekistan": "乌兹别克",
}

# Position weights (from index.html)
GOAL_W = {"中锋": 9, "边锋": 7, "前腰": 7, "中前卫": 4, "后腰": 2, "边卫": 3, "中卫": 1, "门将": 0}
ASSIST_W = {"中锋": 3, "边锋": 5, "前腰": 7, "中前卫": 5, "后腰": 4, "边卫": 4, "中卫": 1, "门将": 0}

# Position mapping from ESPN position codes
POS_MAP = {"G": "门将", "D": "中卫", "M": "中前卫", "F": "中锋"}


def extract_js_var(html, var_name):
    """Extract a JS variable value from index.html using regex."""
    # Match: var VARNAME={...}; or var VARNAME=[...];
    pattern = rf'var\s+{re.escape(var_name)}\s*=\s*'
    match = re.search(pattern, html)
    if not match:
        return None

    start = match.end()
    # Find the matching closing brace/bracket
    if html[start] == '{':
        close_char, open_char = '}', '{'
    elif html[start] == '[':
        close_char, open_char = ']', '['
    else:
        return None

    depth = 0
    i = start
    in_string = False
    string_char = None
    while i < len(html):
        c = html[i]
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == string_char:
                in_string = False
        else:
            if c in ('"', "'"):
                in_string = True
                string_char = c
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    # Try to parse as JSON-like (JS uses unquoted keys sometimes)
                    raw = html[start:i + 1]
                    return raw
        i += 1
    return None


def parse_js_dict(raw):
    """Parse a JS object literal into a Python dict. Handles unquoted keys."""
    # Add quotes around unquoted keys: {key: val} -> {"key": val}
    # This is a simplified parser — works for flat dicts and simple nested structures
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to fix unquoted keys
    fixed = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r'"\1":', raw)
    # Fix single quotes
    fixed = fixed.replace("'", '"')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Use eval as last resort (safe: we control the input)
    try:
        return eval(raw)
    except:
        return None


def load_strength_tiers():
    """Load team strength tiers."""
    tiers_file = BASE / "data" / "rankings" / "team_strength_tiers.json"
    # Use the STRENGTH variable from index.html instead (it's the authoritative one)
    # tier 5: 5, tier 4: 4, tier 3: 3, tier 2: 2, tier 1: 1
    strength = {}
    try:
        with open(tiers_file) as f:
            tiers = json.load(f)
        for tier_name, teams in tiers.items():
            tier_num = int(tier_name.replace("tier", ""))
            for t in teams:
                strength[t] = tier_num
    except:
        pass
    # Fill defaults
    for t in TEAMS_48:
        if t not in strength:
            strength[t] = 3
    return strength


def load_squads():
    """Load squad data from ESPN."""
    with open(SQUADS_FILE) as f:
        squads = json.load(f)
    # Convert to {team_cn: [players]}
    result = {}
    for team_en, data in squads.items():
        team_cn = ESPN_TO_CN.get(team_en)
        if team_cn:
            result[team_cn] = data.get("players", [])
    return result


def load_player_mapping():
    """Load English->Chinese name mapping."""
    with open(MAPPING_FILE) as f:
        return json.load(f)


def load_embedded_data():
    """Extract PL, POS, STAR_PLAYER from index.html."""
    with open(INDEX_FILE, encoding="utf-8") as f:
        html = f.read()

    pl_raw = extract_js_var(html, "PL")
    pos_raw = extract_js_var(html, "POS")
    star_raw = extract_js_var(html, "STAR_PLAYER")

    pl = parse_js_dict(pl_raw) if pl_raw else {}
    pos = parse_js_dict(pos_raw) if pos_raw else {}
    star = parse_js_dict(star_raw) if star_raw else {}

    return pl, pos, star


def get_position(player_cn, team_cn, pos_data, squads_data, mapping_data):
    """
    Get a player's position. Priority:
    1. POS embedded data (8-tier Chinese position)
    2. ESPN squad data (G/D/M/F -> mapped to Chinese)
    3. Default: 中前卫
    """
    # Try POS data first
    if team_cn in pos_data and player_cn in pos_data[team_cn]:
        return pos_data[team_cn][player_cn]

    # Try ESPN squad data
    if team_cn in squads_data:
        for p in squads_data[team_cn]:
            en_name = p.get("name", "")
            cn_info = mapping_data.get(en_name, {})
            cn_name = cn_info.get("cn", "") if isinstance(cn_info, dict) else ""
            if cn_name == player_cn:
                espn_pos = p.get("position", "M")
                return POS_MAP.get(espn_pos, "中前卫")

    return "中前卫"


def get_age(player_cn, team_cn, squads_data, mapping_data):
    """Get a player's age from squad data."""
    if team_cn in squads_data:
        for p in squads_data[team_cn]:
            en_name = p.get("name", "")
            cn_info = mapping_data.get(en_name, {})
            cn_name = cn_info.get("cn", "") if isinstance(cn_info, dict) else ""
            if cn_name == player_cn:
                return p.get("age", 27)
    return 27  # Default age


def compute_age_factor(age):
    """Compute age-based performance factor."""
    if age < 23:
        return max(0.7, 0.7 + age * 0.013)
    elif age > 31:
        return max(0.7, 1.1 - (age - 31) * 0.05)
    return 1.0


def compute_goal_threat(position, team_tier, age, is_star):
    """Compute goal threat multiplier."""
    base = GOAL_W.get(position, 0) / 9.0
    age_factor = compute_age_factor(age)
    team_factor = team_tier / 5.0
    star_bonus = 1.3 if is_star else 1.0
    multiplier = base * age_factor * team_factor * star_bonus * 4.0
    return round(max(0.1, min(4.0, multiplier)), 1)


def compute_assist_threat(position, team_tier, age, is_star):
    """Compute assist threat multiplier."""
    base = ASSIST_W.get(position, 0) / 7.0
    age_factor = compute_age_factor(age)
    team_factor = team_tier / 5.0
    playmaker_bonus = 1.2 if (position in ("前腰", "中前卫") and is_star) else 1.0
    multiplier = base * age_factor * team_factor * playmaker_bonus * 4.0
    return round(max(0.1, min(4.0, multiplier)), 1)


def select_players(team_cn, pl_data, pos_data, squads_data, mapping_data, star_data, strength):
    """
    Select key players for a team and compute their threat multipliers.
    Returns list of player threat entries.
    """
    tier = strength.get(team_cn, 3)
    players = []
    seen_names = set()

    # Get the 11 embedded simulation players
    sim_players = pl_data.get(team_cn, [])
    star_name = star_data.get(team_cn, "")

    # Tier 1: All simulation players (they appear in matches)
    for p_cn in sim_players:
        if p_cn in seen_names or not p_cn:
            continue
        seen_names.add(p_cn)

        pos = get_position(p_cn, team_cn, pos_data, squads_data, mapping_data)
        age = get_age(p_cn, team_cn, squads_data, mapping_data)
        is_star = (p_cn == star_name)

        # Skip goalkeepers for threat calculation
        if pos == "门将":
            continue

        goal = compute_goal_threat(pos, tier, age, is_star)
        assist = compute_assist_threat(pos, tier, age, is_star)

        players.append({
            "team_cn": team_cn,
            "team_en": TEAM_EN.get(team_cn, ""),
            "player_name_source": p_cn,
            "player_name_app_alias": p_cn,
            "position": pos,
            "role_tags": get_role_tags(pos, is_star, p_cn == star_name),
            "goal_threat": {
                "multiplier": goal,
                "basis": get_basis(pos, is_star, "goal"),
                "confidence": "high" if tier >= 3 else "medium",
            },
            "assist_threat": {
                "multiplier": assist,
                "basis": get_basis(pos, is_star, "assist"),
                "confidence": "high" if tier >= 3 else "medium",
            },
            "star_tier": get_star_tier(pos, tier, is_star),
            "rationale": get_rationale(pos, is_star, goal, assist),
            "sources": [
                {
                    "name": "ESPN squads / embedded simulation roster",
                    "url": None,
                    "as_of": "2026-06-12",
                    "source_type": "observed",
                }
            ],
            "confidence": "high" if tier >= 4 else ("medium" if tier >= 2 else "low"),
        })

    # Ensure at least 2 players per team
    if len(players) < 2:
        # Add remaining squad players
        if team_cn in squads_data:
            for p in squads_data[team_cn]:
                if len(players) >= 2:
                    break
                en_name = p.get("name", "")
                cn_info = mapping_data.get(en_name, {})
                cn_name = cn_info.get("cn", en_name) if isinstance(cn_info, dict) else en_name
                if cn_name in seen_names or not cn_name:
                    continue
                espn_pos = p.get("position", "M")
                pos = POS_MAP.get(espn_pos, "中前卫")
                if pos == "门将":
                    continue
                seen_names.add(cn_name)
                age = p.get("age", 27)
                is_star = False

                goal = compute_goal_threat(pos, tier, age, is_star)
                assist = compute_assist_threat(pos, tier, age, is_star)

                players.append({
                    "team_cn": team_cn,
                    "team_en": TEAM_EN.get(team_cn, ""),
                    "player_name_source": en_name,
                    "player_name_app_alias": cn_name,
                    "position": pos,
                    "role_tags": get_role_tags(pos, False, False),
                    "goal_threat": {
                        "multiplier": goal,
                        "basis": get_basis(pos, False, "goal"),
                        "confidence": "medium",
                    },
                    "assist_threat": {
                        "multiplier": assist,
                        "basis": get_basis(pos, False, "assist"),
                        "confidence": "medium",
                    },
                    "star_tier": get_star_tier(pos, tier, False),
                    "rationale": get_rationale(pos, False, goal, assist),
                    "sources": [
                        {
                            "name": "ESPN squads",
                            "url": None,
                            "as_of": "2026-06-12",
                            "source_type": "observed",
                        }
                    ],
                    "confidence": "medium",
                })

    return players


def get_role_tags(position, is_star, is_primary_star):
    """Get role tags for a player."""
    tags = []
    pos_tags = {
        "中锋": ["primary_striker"],
        "边锋": ["winger"],
        "前腰": ["creator", "set_piece_taker"],
        "中前卫": ["box_to_box"],
        "后腰": ["defensive_midfielder"],
        "边卫": ["attacking_fullback"],
        "中卫": ["aerial_set_piece_threat"],
    }
    tags.extend(pos_tags.get(position, ["squad_regular"]))
    if is_primary_star:
        tags.append("veteran_star")
    return tags


def get_basis(position, is_star, threat_type):
    """Get basis for threat calculation."""
    if threat_type == "goal":
        basis = ["position_weight"]
        if position in ("中锋", "边锋"):
            basis.append("goal_scoring_position")
        if is_star:
            basis.append("star_player_status")
        return basis
    else:
        basis = ["position_weight"]
        if position in ("前腰", "中前卫", "边锋"):
            basis.append("creative_position")
        if is_star:
            basis.append("star_player_status")
        return basis


def get_star_tier(position, tier, is_star):
    """Determine star tier."""
    if is_star and tier >= 4:
        if position in ("中锋",):
            return "world_class_scorer"
        elif position in ("前腰", "边锋"):
            return "world_class_creator"
        return "elite_all_round_attacker"
    if is_star:
        return "national_team_core"
    if tier >= 4 and position in ("中锋", "边锋", "前腰"):
        return "secondary_attacker"
    return "squad_regular"


def get_rationale(position, is_star, goal, assist):
    """Generate rationale text."""
    parts = []
    if is_star:
        parts.append("Primary star player")
    if goal > assist + 0.5:
        parts.append(f"Primary goal threat (multiplier {goal}), lower creation value ({assist})")
    elif assist > goal + 0.5:
        parts.append(f"Primary creative threat (multiplier {assist}), moderate goal threat ({goal})")
    else:
        parts.append(f"Balanced attacking contributor (goal {goal}, assist {assist})")
    parts.append(f"Position: {position}")
    return "; ".join(parts)


def main():
    print("[threats] Loading data...")
    squads = load_squads()
    mapping = load_player_mapping()
    pl, pos, star = load_embedded_data()
    strength = load_strength_tiers()

    print(f"[threats] Squads: {len(squads)} teams")
    print(f"[threats] PL: {len(pl)} teams")
    print(f"[threats] POS: {len(pos)} teams")
    print(f"[threats] STAR_PLAYER: {len(star)} teams")

    all_players = []

    for team_cn in TEAMS_48:
        players = select_players(team_cn, pl, pos, squads, mapping, star, strength)
        all_players.extend(players)

    print(f"\n[threats] Total players: {len(all_players)}")

    # Per-team summary
    from collections import Counter
    team_counts = Counter(p["team_cn"] for p in all_players)
    for team in TEAMS_48:
        count = team_counts.get(team, 0)
        flag = " !!!" if count < 2 else ""
        print(f"  {team}: {count} players{flag}")

    # Validation
    errors = []
    for p in all_players:
        gt = p["goal_threat"]["multiplier"]
        at = p["assist_threat"]["multiplier"]
        if not (0.0 <= gt <= 4.0):
            errors.append(f"{p['player_name_app_alias']}: goal_threat {gt} out of range")
        if not (0.0 <= at <= 4.0):
            errors.append(f"{p['player_name_app_alias']}: assist_threat {at} out of range")
        if p["goal_threat"]["confidence"] not in ("high", "medium", "low"):
            errors.append(f"{p['player_name_app_alias']}: bad confidence")

    if errors:
        print(f"\n[threats] Validation errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")
    else:
        print("\n[threats] Validation passed")

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)
    print(f"  Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
