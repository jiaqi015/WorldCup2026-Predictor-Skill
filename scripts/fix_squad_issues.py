#!/usr/bin/env python3
"""
Fix known squad data issues from ESPN API.
"""

import json
import sys
from pathlib import Path

# Paths
SQUADS_FILE = Path(__file__).parent.parent / "data" / "squads" / "squads_partial.json"

# Team name mapping
TEAM_CN_MAP = {
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
    "United States": "美国", "Uruguay": "乌拉圭", "Uzbekistan": "乌兹别克"
}

KNOWN_MISSING_PLAYERS = {
    "Argentina": {
        "name": "Leonardo Balerdi",
        "jersey": "2",
        "position": "D",
        "age": 27,
        "birth_date": "1999-01-26T08:00Z",
        "nationality": "Argentina",
    },
    "Austria": {
        "name": "Christoph Baumgartner",
        "jersey": "19",
        "position": "M",
        "age": 26,
        "birth_date": "1999-08-01T07:00Z",
        "nationality": "Austria",
    },
    "Egypt": {
        "name": "Mostafa Mohamed",
        "jersey": "26",
        "position": "F",
        "age": 28,
        "birth_date": "1997-11-28T08:00Z",
        "nationality": "Egypt",
    },
}


def fix_squads():
    """Fix all known issues."""
    print("=" * 60)
    print("Fixing Squad Data Issues")
    print("=" * 60)

    # Load data
    with open(SQUADS_FILE, 'r', encoding='utf-8') as f:
        squads = json.load(f)

    fixes_applied = 0

    # Fix 1: Egypt has 4 goalkeepers, remove the last one
    if "Egypt" in squads:
        players = squads["Egypt"]["players"]
        gks = [p for p in players if p.get("position") == "G"]
        others = [p for p in players if p.get("position") != "G"]

        if len(gks) > 3:
            print(f"\n[Fix 1] Egypt: Removing extra goalkeeper {gks[-1]['name']}")
            gks = gks[:3]
            squads["Egypt"]["players"] = gks + others
            fixes_applied += 1

    # Fix 2: Paraguay has duplicate jersey number 13
    if "Paraguay" in squads:
        players = squads["Paraguay"]["players"]
        seen_jerseys = {}
        for i, p in enumerate(players):
            jersey = p.get("jersey")
            if jersey in seen_jerseys:
                # Find next available number
                for new_jersey in range(1, 100):
                    if new_jersey not in seen_jerseys:
                        print(f"\n[Fix 2] Paraguay: {p['name']} jersey {jersey} -> {new_jersey}")
                        players[i]["jersey"] = new_jersey
                        fixes_applied += 1
                        break
            seen_jerseys[players[i].get("jersey")] = i

    # Fix 3: deterministically complete known 25-player API snapshots.
    for team_name, player in KNOWN_MISSING_PLAYERS.items():
        if team_name not in squads:
            continue
        players = squads[team_name]["players"]
        if len(players) >= 26 or any(p.get("name") == player["name"] for p in players):
            continue
        print(f"\n[Fix 3] {team_name}: Adding missing snapshot player {player['name']}")
        players.append(player.copy())
        fixes_applied += 1

    # Save fixed data
    if fixes_applied > 0:
        with open(SQUADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(squads, f, ensure_ascii=False, indent=2)
        print(f"\n{'=' * 60}")
        print(f"Applied {fixes_applied} fixes")
        print(f"Saved to {SQUADS_FILE}")
    else:
        print("\nNo fixes needed")

    return fixes_applied


if __name__ == "__main__":
    fixes = fix_squads()
    sys.exit(0 if fixes >= 0 else 1)
