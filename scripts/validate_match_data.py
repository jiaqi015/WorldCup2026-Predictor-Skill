#!/usr/bin/env python3
"""
Validate that real match data is correctly embedded in index.html.
Checks: static variables, enrichGMWithData function, UI helper functions, CSS.
"""

import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def check_file_exists(path, desc):
    """Check if file exists."""
    if os.path.exists(path):
        print(f"✓ {desc}: {path}")
        return True
    else:
        print(f"✗ {desc}: {path} NOT FOUND")
        return False

def check_content_contains(content, pattern, desc):
    """Check if content contains pattern."""
    if pattern in content:
        print(f"✓ {desc}")
        return True
    else:
        print(f"✗ {desc}: pattern not found")
        return False

def main():
    all_passed = True
    print("=" * 60)
    print("MATCH DATA VERIFICATION")
    print("=" * 60)

    # Check data files
    print("\n1. DATA FILES:")
    data_files = [
        ("data/rankings/fifa_rankings.json", "FIFA Rankings"),
        ("data/matches/match_schedule.json", "Match Schedule"),
        ("data/matches/match_details.json", "Match Details"),
        ("data/matches/manifest.json", "Match Source Manifest"),
    ]
    for path, desc in data_files:
        all_passed = check_file_exists(os.path.join(BASE_DIR, path), desc) and all_passed

    # Check scripts
    print("\n2. SCRIPTS:")
    script_files = [
        ("scripts/fetch_match_data.py", "Fetch Match Data"),
        ("scripts/fetch_match_details.py", "Fetch Match Details"),
        ("scripts/update_match_data.py", "Update Match Data"),
    ]
    for path, desc in script_files:
        all_passed = check_file_exists(os.path.join(BASE_DIR, path), desc) and all_passed

    # Check index.html
    print("\n3. INDEX.HTML:")
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(index_path):
        print("✗ index.html NOT FOUND")
        sys.exit(1)

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check static variables
    print("\n4. STATIC VARIABLES:")
    static_vars = [
        ("var FIFA_RANKINGS=", "FIFA_RANKINGS variable"),
        ("var MATCH_SCHEDULE=", "MATCH_SCHEDULE variable"),
        ("var MATCH_DETAILS=", "MATCH_DETAILS variable"),
        ("var MATCH_DATA_META=", "MATCH_DATA_META variable"),
    ]
    for pattern, desc in static_vars:
        all_passed = check_content_contains(content, pattern, desc) and all_passed

    # Check functions
    print("\n5. FUNCTIONS:")
    functions = [
        ("function enrichGMWithData()", "enrichGMWithData function"),
        ("function formatMatchTime(", "formatMatchTime function"),
        ("function formatVenue(", "formatVenue function"),
        ("function formatOdds(", "formatOdds function"),
        ("function getMatchExtra(", "getMatchExtra function"),
    ]
    for pattern, desc in functions:
        all_passed = check_content_contains(content, pattern, desc) and all_passed

    # Check function calls
    print("\n6. FUNCTION CALLS:")
    calls = [
        ("enrichGMWithData();", "enrichGMWithData() call"),
        ("getMatchExtra(m)", "getMatchExtra() call"),
    ]
    for pattern, desc in calls:
        all_passed = check_content_contains(content, pattern, desc) and all_passed

    # Check CSS
    print("\n7. CSS:")
    css_patterns = [
        (".match-extra", "match-extra CSS class"),
    ]
    for pattern, desc in css_patterns:
        all_passed = check_content_contains(content, pattern, desc) and all_passed

    # Check data integration
    print("\n8. DATA INTEGRATION:")
    integrations = [
        ("m.id=id;", "Match ID assignment"),
        ("m.date=ms.date;", "Match date assignment"),
        ("m.venue=ms.venue;", "Match venue assignment"),
        ("m.odds=ms.odds;", "Match odds assignment"),
    ]
    for pattern, desc in integrations:
        all_passed = check_content_contains(content, pattern, desc) and all_passed

    # Check predictor sync
    print("\n9. PREDICTOR SYNC:")
    predictor_path = os.path.join(BASE_DIR, "skills", "world-cup-2026-predictor", "assets", "predictor", "index.html")
    if os.path.exists(predictor_path):
        with open(predictor_path, "r", encoding="utf-8") as f:
            predictor_content = f.read()
        if predictor_content == content:
            print("✓ Predictor index.html is synced")
        else:
            print("✗ Predictor index.html is NOT synced")
            all_passed = False
    else:
        print("✗ Predictor index.html NOT FOUND")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

    # Count checks
    total_checks = len(data_files) + len(script_files) + len(static_vars) + len(functions) + len(calls) + len(css_patterns) + len(integrations) + 1  # +1 for predictor sync
    passed_checks = total_checks if all_passed else 0

    print(f"\nTotal checks: {total_checks}")
    print(f"Status: {'ALL PASSED' if passed_checks == total_checks else 'SOME FAILED'}")
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
