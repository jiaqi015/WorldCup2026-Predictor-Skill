#!/usr/bin/env python3
"""
Generate SVG avatar placeholders for players without ESPN headshots.
Creates professional-looking circular avatars with team colors and initials.
"""

import json
import argparse
import re
import sys
import unicodedata
import xml.sax.saxutils
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from photo_utils import safe_name

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SQUADS_FILE = DATA_DIR / "squads" / "squads_partial.json"
MAPPING_FILE = DATA_DIR / "squads" / "player_mapping.json"
PHOTO_MAP_FILE = DATA_DIR / "squads" / "photo_mapping.json"
PHOTOS_DIR = DATA_DIR / "photos"

# Country/Team colors (primary, secondary)
TEAM_COLORS = {
    "Algeria": ("#006233", "#FFFFFF"),
    "Argentina": ("#75AADB", "#FFFFFF"),
    "Australia": ("#FFCD00", "#006847"),
    "Austria": ("#ED2939", "#FFFFFF"),
    "Belgium": ("#000000", "#FAE042"),
    "Bosnia-Herzegovina": ("#002366", "#FFD700"),
    "Brazil": ("#009739", "#FEDD00"),
    "Canada": ("#FF0000", "#FFFFFF"),
    "Cape Verde": ("#003DA5", "#FFFFFF"),
    "Colombia": ("#FCD116", "#003893"),
    "Congo DR": ("#007FFF", "#FFD700"),
    "Croatia": ("#FF0000", "#FFFFFF"),
    "Curaçao": ("#003DA5", "#FEDD00"),
    "Czechia": ("#11457E", "#FFFFFF"),
    "Ecuador": ("#FFD100", "#003DA5"),
    "Egypt": ("#CE1126", "#FFFFFF"),
    "England": ("#FFFFFF", "#CF081F"),
    "France": ("#002395", "#FFFFFF"),
    "Germany": ("#000000", "#DD0000"),
    "Ghana": ("#006B3F", "#FFD700"),
    "Haiti": ("#00209F", "#D21034"),
    "Iran": ("#239F40", "#FFFFFF"),
    "Iraq": ("#007A3D", "#FFFFFF"),
    "Ivory Coast": ("#F77F00", "#009E60"),
    "Japan": ("#003DA5", "#FFFFFF"),
    "Jordan": ("#000000", "#007A33"),
    "Mexico": ("#006847", "#FFFFFF"),
    "Morocco": ("#C1272D", "#006233"),
    "Netherlands": ("#FF6600", "#FFFFFF"),
    "New Zealand": ("#000000", "#FFFFFF"),
    "Norway": ("#BA0C2F", "#00205B"),
    "Panama": ("#003DA5", "#D21034"),
    "Paraguay": ("#D52B1E", "#FFFFFF"),
    "Portugal": ("#006600", "#FF0000"),
    "Qatar": ("#8A1538", "#FFFFFF"),
    "Saudi Arabia": ("#006C35", "#FFFFFF"),
    "Scotland": ("#003078", "#FFFFFF"),
    "Senegal": ("#00853F", "#FDEF42"),
    "South Africa": ("#007749", "#FFB81C"),
    "South Korea": ("#003478", "#FFFFFF"),
    "Spain": ("#AA151B", "#F1BF00"),
    "Sweden": ("#006AA7", "#FECC02"),
    "Switzerland": ("#FF0000", "#FFFFFF"),
    "Tunisia": ("#E70013", "#FFFFFF"),
    "Türkiye": ("#E30A17", "#FFFFFF"),
    "United States": ("#002868", "#FFFFFF"),
    "Uruguay": ("#0038A8", "#FFFFFF"),
    "Uzbekistan": ("#0099B5", "#FFFFFF"),
}

CN_TO_EN = {
    "阿尔及利亚": "Algeria", "阿根廷": "Argentina", "澳大利亚": "Australia",
    "奥地利": "Austria", "比利时": "Belgium", "波黑": "Bosnia-Herzegovina",
    "巴西": "Brazil", "加拿大": "Canada", "佛得角": "Cape Verde",
    "哥伦比亚": "Colombia", "刚果金": "Congo DR", "克罗地亚": "Croatia",
    "库拉索": "Curaçao", "捷克": "Czechia", "厄瓜多尔": "Ecuador",
    "埃及": "Egypt", "英格兰": "England", "法国": "France",
    "德国": "Germany", "加纳": "Ghana", "海地": "Haiti",
    "伊朗": "Iran", "伊拉克": "Iraq", "科特迪瓦": "Ivory Coast",
    "日本": "Japan", "约旦": "Jordan", "墨西哥": "Mexico",
    "摩洛哥": "Morocco", "荷兰": "Netherlands", "新西兰": "New Zealand",
    "挪威": "Norway", "巴拿马": "Panama", "巴拉圭": "Paraguay",
    "葡萄牙": "Portugal", "卡塔尔": "Qatar", "沙特": "Saudi Arabia",
    "苏格兰": "Scotland", "塞内加尔": "Senegal", "南非": "South Africa",
    "韩国": "South Korea", "西班牙": "Spain", "瑞典": "Sweden",
    "瑞士": "Switzerland", "突尼斯": "Tunisia", "土耳其": "Türkiye",
    "美国": "United States", "乌拉圭": "Uruguay", "乌兹别克": "Uzbekistan",
}


def get_initials(en_name):
    """Get 2-letter initials from English name."""
    parts = en_name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) >= 2:
        return parts[0][:2].upper()
    return "XX"


def get_position_label(pos):
    """Get position label."""
    labels = {"G": "GK", "D": "DF", "M": "MF", "F": "FW"}
    return labels.get(pos, "")


def generate_svg_avatar(en_name, team_en, jersey, position, size=200):
    """Generate SVG avatar with team colors and player initials."""
    initials = xml.sax.saxutils.escape(get_initials(en_name))
    primary, secondary = TEAM_COLORS.get(team_en, ("#4A90D9", "#FFFFFF"))
    pos_label = xml.sax.saxutils.escape(get_position_label(position))
    jersey_str = xml.sax.saxutils.escape(str(jersey))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{primary};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{primary};stop-opacity:0.8"/>
    </linearGradient>
    <clipPath id="circle">
      <circle cx="{size//2}" cy="{size//2}" r="{size//2}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#circle)">
    <rect width="{size}" height="{size}" fill="url(#bg)"/>
    <text x="{size//2}" y="{size*0.42}" text-anchor="middle" fill="{secondary}" font-family="Arial,sans-serif" font-size="{size*0.35}" font-weight="bold" opacity="0.9">{initials}</text>
    <text x="{size//2}" y="{size*0.62}" text-anchor="middle" fill="{secondary}" font-family="Arial,sans-serif" font-size="{size*0.13}" opacity="0.7">#{jersey_str}</text>
    <text x="{size//2}" y="{size*0.78}" text-anchor="middle" fill="{secondary}" font-family="Arial,sans-serif" font-size="{size*0.10}" opacity="0.5">{pos_label}</text>
  </g>
</svg>'''
    return svg


def avatar_key(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch.lower() for ch in normalized if ch.isalnum())


def existing_avatar_paths():
    return {
        avatar_key(path.stem.removeprefix("avatar_")): path
        for path in PHOTOS_DIR.glob("avatar_*.svg")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset-non-espn",
        action="store_true",
        help="replace external or bitmap fallbacks with generated local SVG avatars",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Generate Placeholder Avatars")
    print("=" * 60)

    # Load data
    with open(SQUADS_FILE, "r", encoding="utf-8") as f:
        squads = json.load(f)
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Load existing photo mapping
    photo_mapping = {}
    if PHOTO_MAP_FILE.exists():
        with open(PHOTO_MAP_FILE, "r", encoding="utf-8") as f:
            photo_mapping = json.load(f)

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    avatar_paths = existing_avatar_paths()

    generated = 0
    skipped = 0
    total = 0

    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            total += 1
            pname = player["name"]

            current = photo_mapping.get(pname)
            if current and (
                not args.reset_non_espn or current.get("source") == "espn"
            ):
                skipped += 1
                continue

            # Get team English name for colors
            team_en = team_name  # Already English in squads_partial.json

            svg_path = avatar_paths.get(avatar_key(pname))
            if svg_path is None:
                svg = generate_svg_avatar(
                    pname,
                    team_en,
                    player.get("jersey", "0"),
                    player.get("position", "M"),
                )
                safe_fn = safe_name(pname)
                svg_path = PHOTOS_DIR / f"avatar_{safe_fn}.svg"
                svg_path.write_text(svg, encoding="utf-8")
                avatar_paths[avatar_key(pname)] = svg_path

            photo_mapping[pname] = {
                "source": "placeholder",
                "path": f"data/photos/{svg_path.name}",
                "athlete_id": None,
            }
            generated += 1

    # Save updated photo mapping
    sys.path.insert(0, str(Path(__file__).parent))
    from photo_utils import save_mapping
    save_mapping(photo_mapping)

    # Stats
    espn_count = sum(1 for v in photo_mapping.values() if v["source"] == "espn")
    placeholder_count = sum(1 for v in photo_mapping.values() if v["source"] == "placeholder")

    print(f"Total players: {total}")
    print(f"ESPN headshots: {espn_count}")
    print(f"Placeholders generated: {generated}")
    print(f"Already had photos: {skipped}")
    print(f"Total photo mapping: {len(photo_mapping)}")
    print(f"Coverage: {len(photo_mapping)/total*100:.1f}%")

    # Validation
    print("\n--- TDD Validation ---")
    checks = []
    unique_players = {
        player["name"]
        for team_data in squads.values()
        for player in team_data.get("players", [])
    }
    checks.append((
        "Full Coverage",
        set(photo_mapping) == unique_players,
        f"{len(photo_mapping)}/{len(unique_players)} unique players",
    ))
    checks.append(("ESPN Photos", espn_count > 0, f"{espn_count}"))
    checks.append(("All Files Exist", all(
        (BASE_DIR / v["path"]).exists() for v in photo_mapping.values()
    ), "OK"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}: {detail}")

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    return all_pass


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
