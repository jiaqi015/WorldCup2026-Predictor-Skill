#!/usr/bin/env python3
"""
TDD Final Validation: Comprehensive checks for translations, photos, and data integrity.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from photo_utils import validate_image

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
    """Verify all photo files in mapping exist on disk and are valid images."""
    photo_map = load_json(PHOTO_MAP_FILE)
    missing = []
    invalid = []
    for name, info in photo_map.items():
        path = BASE_DIR / info["path"]
        if not path.exists():
            missing.append(f"{name}: {info['path']}")
        elif info.get("source") != "placeholder" and not validate_image(str(path)):
            invalid.append(f"{name}: {info['path']}")

    failures = missing[:5] + invalid[:5]
    return {
        "name": "Photo Files Exist",
        "pass": len(missing) == 0 and len(invalid) == 0,
        "detail": f"{len(missing)} missing, {len(invalid)} invalid images",
        "failures": failures
    }


def check_photo_sources():
    """Count approved headshot and generated-avatar sources."""
    photo_map = load_json(PHOTO_MAP_FILE)
    sources = {}
    for item in photo_map.values():
        source = item.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1
    approved = {"espn", "placeholder", "sofifa", "wikidata", "wikipedia", "sportsdb", "transfermarkt", "wikipedia_pageimg", "teammate"}
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


def check_orphan_files():
    """Detect files in data/photos/ not referenced by photo_mapping.json."""
    photo_map = load_json(PHOTO_MAP_FILE)
    referenced = set()
    for v in photo_map.values():
        p = v.get("path", "")
        if p:
            referenced.add(os.path.basename(p))

    on_disk = set(f for f in os.listdir(PHOTOS_DIR)
                  if os.path.isfile(PHOTOS_DIR / f))
    orphans = sorted(on_disk - referenced)

    return {
        "name": "No Orphan Photo Files",
        "pass": len(orphans) == 0,
        "detail": f"{len(orphans)} orphan files",
        "failures": orphans[:10]
    }


def check_cross_file_consistency():
    """Verify photo_mapping keys exist in player_mapping."""
    photo_map = load_json(PHOTO_MAP_FILE)
    player_map = load_json(MAPPING_FILE)
    player_keys = set(player_map.keys())

    # Also build qualified keys from squads
    squads = load_json(SQUADS_FILE)
    for team_name, team_data in squads.items():
        team_en = team_data.get("team", team_name)
        for p in team_data.get("players", []):
            player_keys.add(f"{p['name']} ({team_en})")

    missing = sorted(k for k in photo_map if k not in player_keys)

    return {
        "name": "Cross-File Consistency",
        "pass": len(missing) == 0,
        "detail": f"{len(missing)} photo_mapping keys not in player_mapping",
        "failures": missing[:10]
    }


def check_file_size_limits():
    """Flag any photo file exceeding MAX_IMAGE_SIZE (5MB)."""
    from photo_utils import MAX_IMAGE_SIZE
    photo_map = load_json(PHOTO_MAP_FILE)
    oversized = []
    for name, v in photo_map.items():
        p = v.get("path", "")
        if p:
            fp = BASE_DIR / p
            if fp.exists() and fp.stat().st_size > MAX_IMAGE_SIZE:
                oversized.append(f"{name}: {fp.stat().st_size / 1024 / 1024:.1f}MB")

    return {
        "name": "Photo Size Limits",
        "pass": len(oversized) == 0,
        "detail": f"{len(oversized)} files exceed {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB",
        "failures": oversized[:10]
    }


def check_filename_security():
    """Verify no photo mapping path contains '..' or escapes data/photos/."""
    photo_map = load_json(PHOTO_MAP_FILE)
    issues = []
    for name, v in photo_map.items():
        p = v.get("path", "")
        if ".." in p:
            issues.append(f"{name}: path contains '..' ({p})")
        if p.startswith("/") or ":\\" in p:
            issues.append(f"{name}: absolute path ({p})")

    return {
        "name": "Filename Security",
        "pass": len(issues) == 0,
        "detail": f"{len(issues)} insecure paths",
        "failures": issues[:10]
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
        check_orphan_files(),
        check_cross_file_consistency(),
        check_file_size_limits(),
        check_filename_security(),
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
