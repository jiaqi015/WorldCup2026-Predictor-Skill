#!/usr/bin/env python3
"""Analyze current photo/avatar status across all players."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

with open(BASE_DIR / "data/squads/photo_mapping.json", "r") as f:
    pm = json.load(f)

with open(BASE_DIR / "data/squads/squads_partial.json", "r") as f:
    squads = json.load(f)

espn = {k: v for k, v in pm.items() if v.get("source") == "espn"}
placeholder = {k: v for k, v in pm.items() if v.get("source") == "placeholder"}
other = {k: v for k, v in pm.items() if v.get("source") not in ("espn", "placeholder")}

all_players = set()
for team_name, team_data in squads.items():
    for player in team_data.get("players", []):
        all_players.add(player["name"])

not_in_mapping = all_players - set(pm.keys())

print("=" * 60)
print("头像状态总览")
print("=" * 60)
print(f"总球员数: {len(all_players)}")
print(f"Photo mapping条目数: {len(pm)}")
print(f"ESPN真实头像: {len(espn)}")
print(f"SVG占位头像: {len(placeholder)}")
print(f"其他来源: {len(other)}")
print(f"未在mapping中的球员: {len(not_in_mapping)}")
print()

# By team breakdown
print("=" * 60)
print("按球队统计")
print("=" * 60)
for team_name, team_data in squads.items():
    players = team_data.get("players", [])
    espn_count = sum(1 for p in players if pm.get(p["name"], {}).get("source") == "espn")
    placeholder_count = sum(1 for p in players if pm.get(p["name"], {}).get("source") == "placeholder")
    missing_count = sum(1 for p in players if p["name"] not in pm)
    bar = "#" * espn_count + "-" * placeholder_count + "?" * missing_count
    print(f"  {team_name:25s} ESPN={espn_count:3d}  Placeholder={placeholder_count:3d}  Missing={missing_count:3d}  [{bar[:20]}]")

print()

# List all placeholder players grouped by team
print("=" * 60)
print(f"待补全球员清单 (共{len(placeholder)}人)")
print("=" * 60)
for team_name, team_data in squads.items():
    placeholder_in_team = [
        p["name"] for p in team_data.get("players", [])
        if pm.get(p["name"], {}).get("source") == "placeholder"
    ]
    if placeholder_in_team:
        print(f"\n--- {team_name} ({len(placeholder_in_team)}人) ---")
        for name in placeholder_in_team:
            print(f"    {name}")

# Save the placeholder list to a JSON file
placeholder_list = list(placeholder.keys())
with open(BASE_DIR / "data/squads/placeholder_players.json", "w") as f:
    json.dump(placeholder_list, f, ensure_ascii=False, indent=2)
print(f"\n待补全清单已保存至: data/squads/placeholder_players.json")

# Check photo files on disk
photos_dir = BASE_DIR / "data/photos"
png_files = list(photos_dir.glob("*.png"))
svg_files = list(photos_dir.glob("avatar_*.svg"))
print(f"\npng照片文件: {len(png_files)}")
print(f"svg占位头像文件: {len(svg_files)}")
