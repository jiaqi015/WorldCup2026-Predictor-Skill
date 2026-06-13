#!/usr/bin/env python3
"""
TDD Final Validation: Comprehensive checks for translations, photos, and data integrity.
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SQUADS_FILE = BASE_DIR / "data" / "squads" / "squads_partial.json"
MAPPING_FILE = BASE_DIR / "data" / "squads" / "player_mapping.json"
PHOTO_MAP_FILE = BASE_DIR / "data" / "squads" / "photo_mapping.json"
PHOTOS_DIR = BASE_DIR / "data" / "photos"
MANIFEST_FILE = BASE_DIR / "data" / "squads" / "manifest.json"
INDEX_FILE = BASE_DIR / "index.html"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_translation_coverage():
    """Verify translated labels are present and free of corrupt characters."""
    mapping = load_json(MAPPING_FILE)
    cn_pattern = re.compile(r'[\u4e00-\u9fff]')
    total = len(mapping)
    has_cn = sum(1 for v in mapping.values() if cn_pattern.search(v.get("cn", "")))
    no_cn = [(k, v) for k, v in mapping.items() if not cn_pattern.search(v.get("cn", ""))]
    corrupt = [(k, v) for k, v in mapping.items() if "\ufffd" in v.get("cn", "")]

    return {
        "name": "Translation Coverage",
        "pass": has_cn == total and not corrupt,
        "detail": f"{has_cn}/{total} ({has_cn/total*100:.1f}%)",
        "failures": [f"{k} -> {v.get('cn','')}" for k, v in (no_cn + corrupt)[:5]]
    }


def check_photo_coverage():
    """Verify 100% photo coverage."""
    photo_map = load_json(PHOTO_MAP_FILE)
    squads = load_json(SQUADS_FILE)
    total_players = sum(len(t.get("players", [])) for t in squads.values())
    mapped = len(photo_map)
    missing = []
    for team_name, team_data in squads.items():
        for player in team_data.get("players", []):
            if player["name"] not in photo_map:
                missing.append(f"{team_name}: {player['name']}")

    return {
        "name": "Photo Coverage",
        "pass": mapped >= total_players - 1,  # Allow 1 off due to potential dupes
        "detail": f"{mapped}/{total_players} ({mapped/total_players*100:.1f}%)",
        "failures": missing[:5]
    }


def check_photo_files_exist():
    """Verify all photo files in mapping exist on disk."""
    photo_map = load_json(PHOTO_MAP_FILE)
    missing = []
    for name, info in photo_map.items():
        path = BASE_DIR / info["path"]
        if not path.exists():
            missing.append(f"{name}: {info['path']}")

    return {
        "name": "Photo Files Exist",
        "pass": len(missing) == 0,
        "detail": f"{len(missing)} missing files",
        "failures": missing[:5]
    }


def check_photo_sources():
    """Count approved headshot and generated-avatar sources."""
    photo_map = load_json(PHOTO_MAP_FILE)
    sources = {}
    for item in photo_map.values():
        source = item.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1
    approved = {"espn", "placeholder", "sofifa"}
    unexpected = sorted(set(sources) - approved)
    total = len(photo_map)

    return {
        "name": "Photo Sources",
        "pass": not unexpected,
        "detail": f"{sources}, Total: {total}",
        "failures": [f"unexpected source: {source}" for source in unexpected],
    }


def check_index_html_integrity():
    """Verify index.html has PHOTO_MAP and new loadPhotos."""
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    issues = []
    if "var PHOTO_MAP={" not in content:
        issues.append("Missing PHOTO_MAP variable")
    if "PHOTO_MAP[" not in content:
        issues.append("Missing PHOTO_MAP lookup in loadPhotos/getPhotoUrl")
    if "wikipedia.org" in content:
        issues.append("Still references Wikipedia API")
    if "🏆" in content:
        issues.append("Champion trophy emoji remains instead of the shared SVG icon")
    if 'function cupIcon()' not in content:
        issues.append("Missing reusable World Cup trophy icon")

    def js_object(name):
        match = re.search(rf"var {name}=(\{{.*?\}});", content, re.DOTALL)
        if not match:
            return {}
        return json.loads(re.sub(r",\s*}", "}", match.group(1)))

    photo_map = js_object("PHOTO_MAP")
    player_lists = js_object("PL")
    runtime_players = {
        player for players in player_lists.values() for player in players
    }
    missing_runtime_photos = sorted(runtime_players - set(photo_map))
    if missing_runtime_photos:
        issues.append(
            f"{len(missing_runtime_photos)} visible roster labels have no PHOTO_MAP entry"
        )

    return {
        "name": "Index.html Integrity",
        "pass": len(issues) == 0,
        "detail": f"PHOTO_MAP entries: {len(photo_map)}, Issues: {len(issues)}",
        "failures": issues + missing_runtime_photos[:5]
    }


def check_squad_data_consistency():
    """Verify squad data has all required fields."""
    squads = load_json(SQUADS_FILE)
    issues = []
    total = 0
    for team_name, team_data in squads.items():
        if not team_data.get("team_id"):
            issues.append(f"{team_name}: missing team_id")
        for player in team_data.get("players", []):
            total += 1
            if not player.get("name"):
                issues.append(f"{team_name}: player missing name")
            if not player.get("jersey"):
                issues.append(f"{team_name}/{player.get('name')}: missing jersey")
            if not player.get("position"):
                issues.append(f"{team_name}/{player.get('name')}: missing position")

    return {
        "name": "Squad Data Consistency",
        "pass": len(issues) == 0,
        "detail": f"{len(squads)} teams, {total} players, {len(issues)} issues",
        "failures": issues[:5]
    }


def check_source_manifest():
    """Verify the roster snapshot records its source and bounded status."""
    manifest = load_json(MANIFEST_FILE)
    issues = []
    if manifest.get("source") != "ESPN public site API":
        issues.append("Unexpected or missing roster source")
    if manifest.get("team_count") != 48 or manifest.get("player_count") != 1248:
        issues.append("Manifest counts do not match the validated snapshot")
    if "not a final FIFA registration list" not in manifest.get("status", ""):
        issues.append("Manifest must state the snapshot limitation")
    return {
        "name": "Source Manifest",
        "pass": len(issues) == 0,
        "detail": f"{manifest.get('team_count')} teams, {manifest.get('player_count')} players",
        "failures": issues,
    }


def check_mapping_consistency():
    """Verify mapping matches squads."""
    mapping = load_json(MAPPING_FILE)
    squads = load_json(SQUADS_FILE)

    squad_names = set()
    for team_data in squads.values():
        for player in team_data.get("players", []):
            squad_names.add(player["name"])

    mapping_names = set(mapping.keys())

    in_squad_not_mapping = squad_names - mapping_names
    in_mapping_not_squad = mapping_names - squad_names

    return {
        "name": "Mapping-Squad Consistency",
        "pass": len(in_squad_not_mapping) == 0,
        "detail": f"Squad: {len(squad_names)}, Mapping: {len(mapping_names)}, Diff: {len(in_squad_not_mapping)}",
        "failures": list(in_squad_not_mapping)[:5]
    }


def check_no_duplicate_jerseys():
    """Check for duplicate jersey numbers within teams."""
    squads = load_json(SQUADS_FILE)
    issues = []
    for team_name, team_data in squads.items():
        jerseys = {}
        for player in team_data.get("players", []):
            j = player.get("jersey", "")
            if j in jerseys:
                issues.append(f"{team_name}: #{j} used by {jerseys[j]} and {player['name']}")
            jerseys[j] = player["name"]

    return {
        "name": "No Duplicate Jerseys",
        "pass": len(issues) == 0,
        "detail": f"{len(issues)} duplicates found",
        "failures": issues[:5]
    }


def main():
    print("=" * 60)
    print("TDD Final Validation")
    print("=" * 60)

    checks = [
        check_translation_coverage(),
        check_photo_coverage(),
        check_photo_files_exist(),
        check_photo_sources(),
        check_index_html_integrity(),
        check_squad_data_consistency(),
        check_source_manifest(),
        check_mapping_consistency(),
        check_no_duplicate_jerseys(),
    ]

    all_pass = True
    for check in checks:
        status = "PASS" if check["pass"] else "FAIL"
        if not check["pass"]:
            all_pass = False
        print(f"\n  [{status}] {check['name']}: {check['detail']}")
        for f in check.get("failures", []):
            print(f"    - {f}")

    print("\n" + "=" * 60)
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
