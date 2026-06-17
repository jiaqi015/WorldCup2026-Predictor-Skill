#!/usr/bin/env python3
"""Regression tests for the ESPN source contract used by the skill."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "world-cup-2026-predictor" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import espn_source as es


PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def event(
    event_id: str,
    date: str,
    home: str,
    away: str,
    home_score: str = "0",
    away_score: str = "0",
    completed: bool = False,
    stage: int = 13802,
) -> dict:
    return {
        "id": event_id,
        "date": date,
        "season": {"type": stage},
        "competitions": [
            {
                "venue": {
                    "fullName": "Test Stadium",
                    "address": {"city": "Test City", "country": "USA"},
                },
                "status": {
                    "type": {
                        "completed": completed,
                        "shortDetail": "FT" if completed else "Scheduled",
                        "name": "STATUS_FINAL" if completed else "STATUS_SCHEDULED",
                    }
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": home_score,
                        "team": {"displayName": home},
                    },
                    {
                        "homeAway": "away",
                        "score": away_score,
                        "team": {"displayName": away},
                    },
                ],
            }
        ],
    }


def sample_payload() -> dict:
    return {
        "events": [
            event(
                "m1",
                "2026-06-12T16:00:00Z",
                "Mexico",
                "South Africa",
                "2",
                "0",
                True,
            ),
            event(
                "m2",
                "2026-06-13T02:00:00Z",
                "United States",
                "Czechia",
                "1",
                "1",
                False,
                13801,
            ),
            event(
                "m3",
                "2026-06-13T08:00:00Z",
                "Atlantis",
                "Semifinal 1 Loser",
                "0",
                "0",
                False,
            ),
        ]
    }


def test_contract_shape() -> None:
    print("\n=== contract shape ===")
    aliases = {"Mexico": "墨西哥", "South Africa": "南非", "United States": "美国", "Czechia": "捷克", "Brazil": "巴西"}
    contract = es.build_contract(
        sample_payload(),
        now=datetime(2026, 6, 12, 0, 0, tzinfo=timezone.utc),
        upcoming_limit=1,
        aliases=aliases,
    )
    report("source is ESPN", contract["source"] == "ESPN")
    report("contract version", contract["contract_version"] == 1)
    report("scheduled count", contract["scheduled_count"] == 3)
    report("completed count", contract["completed_count"] == 1)
    report("upcoming limited", len(contract["upcoming"]) == 1 and contract["upcoming"][0]["id"] == "m2")
    report("mapping issue surfaced", contract["mapping_issues"][0]["team"] == "Atlantis")
    report("placeholder ignored", len(contract["mapping_issues"]) == 1)


def test_today_filter() -> None:
    print("\n=== today filter ===")
    events = [es.normalize_event(item) for item in sample_payload()["events"]]
    events = [item for item in events if item]
    selected = es.filter_completed_on_date(
        events,
        es.parse_date("2026-06-13"),
        "Asia/Shanghai",
    )
    report("local date uses timezone", len(selected) == 1 and selected[0]["id"] == "m1")


def test_team_alias_loading() -> None:
    print("\n=== team aliases ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        app_path = Path(tmpdir) / "index.html"
        app_path.write_text(
            '<script>var TEAM_EN={"墨西哥":"Mexico","南非":"South Africa"};</script>',
            encoding="utf-8",
        )
        aliases = es.load_team_aliases(app_path)
    report("english alias", aliases["Mexico"] == "墨西哥")
    report("chinese alias", aliases["南非"] == "南非")
    report("built-in alias", aliases["USA"] == "美国")
    report("bosnia alias", aliases["Bosnia-Herzegovina"] == "波黑")


def main() -> int:
    test_contract_shape()
    test_today_filter()
    test_team_alias_loading()
    print(f"\nESPN source contract tests: {PASS} passed, {FAIL} failed.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
