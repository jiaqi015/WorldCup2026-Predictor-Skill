#!/usr/bin/env python3
"""
Update index.html with official squad data from ESPN.
Generates new PL, POS, EN, STAR_PLAYER variables with jersey numbers, ages, and positions.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Paths
SQUADS_FILE = Path(__file__).parent.parent / "data" / "squads" / "squads_partial.json"
MAPPING_FILE = Path(__file__).parent.parent / "data" / "squads" / "player_mapping.json"
PHOTO_MAP_FILE = Path(__file__).parent.parent / "data" / "squads" / "photo_mapping.json"
INDEX_FILE = Path(__file__).parent.parent / "index.html"

# Team name mapping (ESPN English -> Chinese)
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

# Position mapping (ESPN -> Chinese)
POS_MAP = {
    "G": "门将",
    "D": "中卫",
    "M": "中前卫",
    "F": "边锋"
}

# Product-curated team icons for entertainment mode. Values use the same
# localized labels as PL and are accepted only while they remain in the 11.
STAR_PLAYER_OVERRIDES = {
    "佛得角": "加里-罗德里格斯",
    "刚果金": "卡库塔",
    "克罗地亚": "克拉马里奇",
    "德国": "沃尔特马德",
    "加纳": "塞梅尼奥",
    "伊拉克": "艾哈迈德",
    "科特迪瓦": "迪奥曼德",
    "日本": "前田",
    "约旦": "法库里",
    "摩洛哥": "苏菲安",
    "巴拿马": "迪亚斯",
    "苏格兰": "亚当斯",
    "西班牙": "托雷斯",
    "突尼斯": "伊斯梅尔",
    "土耳其": "耶尔德兹",
    "美国": "佩皮",
    "乌拉圭": "努涅斯",
    "乌兹别克": "乌鲁诺夫",
}


def load_data():
    """Load squad data and player mapping."""
    # Load squads
    with open(SQUADS_FILE, 'r', encoding='utf-8') as f:
        squads = json.load(f)

    # Load mapping if exists
    mapping = {}
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping = json.load(f)

    return squads, mapping


def get_player_cn_name(en_name, mapping, team_en=None):
    """Get Chinese name for player, fallback to English."""
    qualified = f"{en_name} ({team_en})" if team_en else None
    if qualified and qualified in mapping:
        return mapping[qualified].get('cn', en_name)
    if en_name in mapping:
        return mapping[en_name].get('cn', en_name)
    return en_name


def generate_new_variables(squads, mapping):
    """Generate new JavaScript variables."""
    lines = []

    # Generate PL (player list - 11 starters per team)
    lines.append("// Generated from official ESPN World Cup 2026 data")
    lines.append(f"// Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("var PL={")

    pl_entries = []
    pl_data = {}  # team_cn -> [cn_names], used to keep STAR_PLAYER in PL
    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        players = team_data.get('players', [])

        # Sort by jersey, take first 11 as starters
        def get_jersey(p):
            j = p.get('jersey', '')
            try:
                return int(j) if j else 99
            except (ValueError, TypeError):
                return 99

        sorted_players = sorted(players, key=get_jersey)
        starters = sorted_players[:11]

        player_names = [get_player_cn_name(p["name"], mapping, team_en) for p in starters]
        pl_data[team_cn] = player_names
        pl_entries.append(f'"{team_cn}":[{",".join(json.dumps(n, ensure_ascii=False) for n in player_names)}]')

    lines.append(','.join(pl_entries))
    lines.append('};')

    # Generate EN (Chinese -> English mapping)
    lines.append("\nvar EN={")
    en_entries = []
    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        for p in team_data.get('players', []):
            cn = get_player_cn_name(p['name'], mapping, team_en)
            if cn != p['name']:  # Only add if we have a translation
                en_entries.append(f'{json.dumps(cn, ensure_ascii=False)}:{json.dumps(p["name"], ensure_ascii=False)}')
    lines.append(','.join(en_entries))
    lines.append('};')

    # Generate POS (position mapping)
    lines.append("\nvar POS={")
    pos_entries = []
    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        player_pos = []
        for p in team_data.get('players', []):
            cn = get_player_cn_name(p['name'], mapping, team_en)
            pos = POS_MAP.get(p.get('position', ''), '中前卫')
            player_pos.append(f'{json.dumps(cn, ensure_ascii=False)}:{json.dumps(pos, ensure_ascii=False)}')
        pos_entries.append(f'"{team_cn}":{{{",".join(player_pos)}}}')
    lines.append(','.join(pos_entries))
    lines.append('};')

    # Generate STAR_PLAYER. Curated choices preserve product intent across
    # refreshes; every choice is still constrained to the generated PL 11.
    lines.append("\nvar STAR_PLAYER={")
    star_entries = []
    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        starters = pl_data.get(team_cn, [])
        curated = STAR_PLAYER_OVERRIDES.get(team_cn)
        full_players = team_data.get('players', [])
        forward_in_pl = []
        for p in full_players:
            if p.get('position') == 'F':
                cn = get_player_cn_name(p['name'], mapping, team_en)
                if cn in starters:
                    forward_in_pl.append(cn)
        if curated in starters:
            star_cn = curated
        else:
            star_cn = forward_in_pl[0] if forward_in_pl else (starters[0] if starters else None)
        if star_cn:
            star_entries.append(f'{json.dumps(team_cn, ensure_ascii=False)}:{json.dumps(star_cn, ensure_ascii=False)}')
    lines.append(','.join(star_entries))
    lines.append('};')

    # Generate PHOTO_MAP using the same display labels consumed by the UI.
    with open(PHOTO_MAP_FILE, 'r', encoding='utf-8') as f:
        source_photos = json.load(f)
    display_photos = {}
    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        for player in team_data.get('players', []):
            en_name = player['name']
            cn_name = get_player_cn_name(en_name, mapping, team_en)
            photo = source_photos.get(f"{en_name} ({team_en})") or source_photos.get(en_name)
            if not photo:
                continue
            path = photo["path"]
            # Always emit team-qualified key — front-end prefers it for cross-team collisions.
            display_photos[f"{team_cn}|{cn_name}"] = path
            # Also emit bare key as a fallback (last-write-wins on collisions; the
            # team-qualified key above guarantees per-team accuracy regardless).
            display_photos[cn_name] = path
    lines.append("\nvar PHOTO_MAP=" + json.dumps(display_photos, ensure_ascii=False, separators=(",", ":")) + ";")

    return '\n'.join(lines)


def update_index_file(new_vars):
    """Update index.html with new variables."""
    # Read original
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace PL variable
    content = re.sub(
        r'(?:(?:// Generated from official ESPN World Cup 2026 data\n'
        r'// Updated: [^\n]+\n)+)?var PL=\{[^;]+\};',
        new_vars.split('var EN=')[0].strip(),
        content,
        flags=re.DOTALL
    )

    # Replace EN variable
    en_match = re.search(r'var EN=\{[^;]+\};', new_vars)
    if en_match:
        content = re.sub(r'var EN=\{[^;]+\};', en_match.group(0), content, flags=re.DOTALL)

    # Replace POS variable
    pos_match = re.search(r'var POS=\{[^;]+\};', new_vars)
    if pos_match:
        content = re.sub(r'var POS=\{[^;]+\};', pos_match.group(0), content, flags=re.DOTALL)
        content = content.replace('};nction getPos(player,team){', '};function getPos(player,team){')

    # Replace STAR_PLAYER variable
    star_match = re.search(r'var STAR_PLAYER=\{[^;]+\};', new_vars)
    if star_match:
        content = re.sub(r'var STAR_PLAYER=\{[^;]+\};', star_match.group(0), content, flags=re.DOTALL)

    photo_match = re.search(r'var PHOTO_MAP=\{[^;]+\};', new_vars)
    if photo_match:
        content = re.sub(r'var PHOTO_MAP=\{[^;]+\};', photo_match.group(0), content, flags=re.DOTALL)

    # Write updated file
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated {INDEX_FILE}")


def main():
    """Main function."""
    print("=" * 60)
    print("Update index.html with Official Squad Data")
    print("=" * 60)

    # Load data
    squads, mapping = load_data()
    print(f"Loaded {len(squads)} teams, {len(mapping)} player mappings")

    # Generate new variables
    print("\nGenerating new variables...")
    new_vars = generate_new_variables(squads, mapping)

    # Update index.html
    print("\nUpdating index.html...")
    update_index_file(new_vars)

    print("\n" + "=" * 60)
    print("Update complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Sync the bundled Skill asset")
    print("2. Run scripts/release_check.py")
    print("3. Test the web application")

    return 0


if __name__ == "__main__":
    sys.exit(main())
