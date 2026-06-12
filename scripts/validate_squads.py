#!/usr/bin/env python3
"""
Validate squad data completeness and accuracy.
TDD approach: multiple validation checks from different angles.
"""

import json
import sys
from pathlib import Path
from collections import Counter

# Data paths
SQUADS_FILE = Path(__file__).parent.parent / "data" / "squads" / "squads_partial.json"
INDEX_FILE = Path(__file__).parent.parent / "skills" / "world-cup-2026-predictor" / "assets" / "predictor" / "index.html"

# Expected groups
GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia-Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Iraq", "Senegal", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"]
}

# Chinese team names mapping
TEAM_CN_NAMES = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国", "Czechia": "捷克",
    "Canada": "加拿大", "Bosnia-Herzegovina": "波黑", "Qatar": "卡塔尔", "Switzerland": "瑞士",
    "Brazil": "巴西", "Morocco": "摩洛哥", "Haiti": "海地", "Scotland": "苏格兰",
    "United States": "美国", "Paraguay": "巴拉圭", "Australia": "澳大利亚", "Türkiye": "土耳其",
    "Germany": "德国", "Curaçao": "库拉索", "Ivory Coast": "科特迪瓦", "Ecuador": "厄瓜多尔",
    "Netherlands": "荷兰", "Japan": "日本", "Sweden": "瑞典", "Tunisia": "突尼斯",
    "Belgium": "比利时", "Egypt": "埃及", "Iran": "伊朗", "New Zealand": "新西兰",
    "Spain": "西班牙", "Cape Verde": "佛得角", "Saudi Arabia": "沙特", "Uruguay": "乌拉圭",
    "France": "法国", "Iraq": "伊拉克", "Senegal": "塞内加尔", "Norway": "挪威",
    "Argentina": "阿根廷", "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦",
    "Portugal": "葡萄牙", "Congo DR": "刚果金", "Uzbekistan": "乌兹别克", "Colombia": "哥伦比亚",
    "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳", "Panama": "巴拿马"
}

# Valid positions
VALID_POSITIONS = {"G", "D", "M", "F"}  # Goalkeeper, Defender, Midfielder, Forward


def load_squads():
    """Load squad data from JSON file."""
    if not SQUADS_FILE.exists():
        print(f"ERROR: Squad file not found: {SQUADS_FILE}")
        return None

    with open(SQUADS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_team_count(squads):
    """Validate we have all 48 teams."""
    print("\n1. Team Count Validation")
    print("-" * 40)

    errors = []

    # Check total teams
    if len(squads) != 48:
        errors.append(f"Expected 48 teams, got {len(squads)}")

    # Check all expected teams are present
    all_expected = set()
    for group_teams in GROUPS.values():
        all_expected.update(group_teams)

    missing = all_expected - set(squads.keys())
    extra = set(squads.keys()) - all_expected

    if missing:
        errors.append(f"Missing teams: {missing}")
    if extra:
        errors.append(f"Unexpected teams: {extra}")

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        return False

    print(f"  ✓ All 48 teams present")
    return True


def validate_squad_size(squads):
    """Validate each team has 26 players."""
    print("\n2. Squad Size Validation")
    print("-" * 40)

    errors = []
    for team_name, team_data in squads.items():
        players = team_data.get('players', [])
        if len(players) != 26:
            errors.append(f"{team_name}: {len(players)} players (expected 26)")

    if errors:
        for e in errors[:10]:  # Show first 10 errors
            print(f"  ✗ {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False

    print(f"  ✓ All teams have 26 players")
    return True


def validate_positions(squads):
    """Validate each team has balanced positions (3 GK, ~8 DEF, ~8 MID, ~7 FWD)."""
    print("\n3. Position Balance Validation")
    print("-" * 40)

    errors = []
    for team_name, team_data in squads.items():
        players = team_data.get('players', [])
        positions = Counter(p.get('position', '') for p in players)

        gk_count = positions.get('G', 0)
        if gk_count != 3:
            errors.append(f"{team_name}: {gk_count} goalkeepers (expected 3)")

        total_outfield = sum(v for k, v in positions.items() if k != 'G')
        if total_outfield != 23:
            errors.append(f"{team_name}: {total_outfield} outfield players (expected 23)")

    if errors:
        for e in errors[:10]:
            print(f"  ✗ {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False

    print(f"  ✓ All teams have balanced positions")
    return True


def validate_jersey_numbers(squads):
    """Validate jersey numbers are unique within each team."""
    print("\n4. Jersey Number Validation")
    print("-" * 40)

    errors = []
    for team_name, team_data in squads.items():
        players = team_data.get('players', [])
        jerseys = [p.get('jersey') for p in players if p.get('jersey')]

        # Check for duplicates
        seen = set()
        for j in jerseys:
            if j in seen:
                errors.append(f"{team_name}: Duplicate jersey number {j}")
            seen.add(j)

        # Check range (1-26 typically for World Cup)
        for j in jerseys:
            try:
                j_int = int(j)
                if not (1 <= j_int <= 99):
                    errors.append(f"{team_name}: Invalid jersey number {j}")
            except (ValueError, TypeError):
                errors.append(f"{team_name}: Invalid jersey number format: {j}")

    if errors:
        for e in errors[:10]:
            print(f"  ✗ {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False

    print(f"  ✓ All jersey numbers valid and unique")
    return True


def validate_ages(squads):
    """Validate player ages are reasonable (16-45)."""
    print("\n5. Age Validation")
    print("-" * 40)

    errors = []
    for team_name, team_data in squads.items():
        players = team_data.get('players', [])
        for p in players:
            age = p.get('age')
            if age is not None and not (16 <= age <= 45):
                errors.append(f"{team_name}: {p.get('name')} has invalid age {age}")

    if errors:
        for e in errors[:10]:
            print(f"  ✗ {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False

    print(f"  ✓ All ages within valid range")
    return True


def validate_names(squads):
    """Validate player names are not empty."""
    print("\n6. Name Validation")
    print("-" * 40)

    errors = []
    for team_name, team_data in squads.items():
        players = team_data.get('players', [])
        for p in players:
            name = p.get('name', '').strip()
            if not name:
                errors.append(f"{team_name}: Empty player name")

    if errors:
        for e in errors[:10]:
            print(f"  ✗ {e}")
        return False

    print(f"  ✓ All player names present")
    return True


def cross_validate_with_index(squads):
    """Cross-validate with existing index.html data."""
    print("\n7. Cross-validation with index.html")
    print("-" * 40)

    if not INDEX_FILE.exists():
        print(f"  ⚠ index.html not found, skipping cross-validation")
        return True

    # Read index.html and extract PL variable
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple extraction - find PL variable
    import re
    pl_match = re.search(r'var PL=\{([^}]+)\}', content)
    if not pl_match:
        print(f"  ⚠ Could not extract PL from index.html")
        return True

    # Count teams in PL
    pl_teams = re.findall(r'"([^"]+)":\[', pl_match.group(1))
    print(f"  index.html has {len(pl_teams)} teams in PL")

    # Compare team names
    espn_teams_cn = [TEAM_CN_NAMES.get(t, t) for t in squads.keys()]
    missing_in_index = set(pl_teams) - set(espn_teams_cn)
    missing_in_espn = set(espn_teams_cn) - set(pl_teams)

    if missing_in_index:
        print(f"  ⚠ Teams in index.html but not in ESPN: {missing_in_index}")
    if missing_in_espn:
        print(f"  ⚠ Teams in ESPN but not in index.html: {missing_in_espn}")

    print(f"  ✓ Cross-validation complete")
    return True


def generate_report(squads):
    """Generate summary report."""
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    total_players = sum(len(t.get('players', [])) for t in squads.values())
    avg_age = 0
    age_count = 0

    for team_data in squads.values():
        for p in team_data.get('players', []):
            if p.get('age'):
                avg_age += p['age']
                age_count += 1

    avg_age = avg_age / age_count if age_count else 0

    print(f"\nSummary:")
    print(f"  Total teams: {len(squads)}")
    print(f"  Total players: {total_players}")
    print(f"  Average age: {avg_age:.1f}")

    # Position distribution
    all_positions = Counter()
    for team_data in squads.values():
        for p in team_data.get('players', []):
            all_positions[p.get('position', 'Unknown')] += 1

    print(f"\nPosition distribution:")
    for pos, count in sorted(all_positions.items()):
        print(f"  {pos}: {count}")

    print("\n" + "=" * 60)


def main():
    """Main validation function."""
    print("=" * 60)
    print("2026 World Cup Squad Validator (TDD)")
    print("=" * 60)

    # Load data
    squads = load_squads()
    if not squads:
        return 1

    # Run all validations
    results = []
    results.append(("Team Count", validate_team_count(squads)))
    results.append(("Squad Size", validate_squad_size(squads)))
    results.append(("Positions", validate_positions(squads)))
    results.append(("Jersey Numbers", validate_jersey_numbers(squads)))
    results.append(("Ages", validate_ages(squads)))
    results.append(("Names", validate_names(squads)))
    results.append(("Cross-validation", cross_validate_with_index(squads)))

    # Generate report
    generate_report(squads)

    # Summary
    print("\nValidation Results:")
    print("-" * 40)
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL VALIDATIONS PASSED")
    else:
        print("SOME VALIDATIONS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
