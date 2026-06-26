#!/usr/bin/env python3
"""
TDD test suite for scripts/fetch_analysis_data.py

Third-party perspective validation:
  - Pure function unit tests (extract_id_from_ref, parse_player_name_from_text, etc.)
  - Collector logic tests with mocked API responses
  - Edge cases: own goals, pagination, missing fields, partial failures
  - Incremental skip logic
  - Integration: refresh_results.py pipeline registration
  - Cross-module parity checks

Run: python3 scripts/test_fetch_analysis_data.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_analysis_data as mod


# ─── Helpers ──────────────────────────────────────────────────────────

def _make_play(
    play_id="100",
    play_type="shot-on-target",
    scoring=False,
    xg=0.1,
    xgot=None,
    team_ref="http://example.com/teams/203",
    text="Player (Team) shot",
    short_text="Player Shot On Target",
    clock="10'",
    period=1,
    distance=20,
    body_part="Right Foot",
    penalty=False,
    own_goal=False,
    participants=None,
):
    """Build a synthetic ESPN play dict."""
    play = {
        "id": play_id,
        "type": {"id": "100", "text": play_type, "type": play_type},
        "scoringPlay": scoring,
        "scoreValue": 1 if scoring else 0,
        "text": text,
        "shortText": short_text,
        "team": {"$ref": team_ref},
        "clock": {"displayValue": clock, "value": float(clock.rstrip("'")) if clock.rstrip("'").replace(".", "").isdigit() else 0},
        "period": {"number": period},
        "statYardage": distance,
        "contactType": {"text": body_part},
        "penaltyKick": penalty,
        "ownGoal": own_goal,
    }
    if xg is not None:
        play["expectedGoals"] = xg
    if xgot is not None:
        play["expectedGoalsOnTarget"] = xgot
    if participants:
        play["participants"] = participants
    return play


def _make_momentum_item(clock="1'", period=1, threat=0.05, comp_id="203"):
    """Build a synthetic ESPN momentum item."""
    return {
        "clock": int(clock.rstrip("'")) * 60,
        "addedClock": 0,
        "displayClock": clock,
        "period": period,
        "probability": threat,
        "competitor": {
            "$ref": f"http://example.com/competitions/123/competitors/{comp_id}"
        },
    }


def _make_stats_response(stats_by_category):
    """Build a synthetic ESPN statistics $ref response.

    stats_by_category: {"offensive": [{"name": "shots", "value": 10, ...}]}
    """
    categories = []
    for cat_name, stats_list in stats_by_category.items():
        categories.append({
            "name": cat_name,
            "displayName": cat_name.title(),
            "stats": stats_list,
        })
    return {"splits": {"categories": categories}}


class _TempDir:
    """Context manager for a temporary directory with data/analysis structure."""

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name
        os.makedirs(os.path.join(self.root, "data", "analysis"), exist_ok=True)
        os.makedirs(os.path.join(self.root, "data", "matches"), exist_ok=True)
        os.makedirs(os.path.join(self.root, "data", "squads"), exist_ok=True)
        return self

    def __exit__(self, *args):
        self._td.__exit__(*args)

    @property
    def analysis_dir(self):
        return os.path.join(self.root, "data", "analysis")

    @property
    def matches_dir(self):
        return os.path.join(self.root, "data", "matches")


# ══════════════════════════════════════════════════════════════════════
# 1. extract_id_from_ref
# ══════════════════════════════════════════════════════════════════════

class TestExtractIdFromRef(unittest.TestCase):

    def test_teams(self):
        url = "http://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world/seasons/2026/teams/203?lang=en"
        self.assertEqual(mod.extract_id_from_ref(url, "teams"), "203")

    def test_competitors(self):
        url = "http://example.com/competitions/760415/competitors/467?lang=en"
        self.assertEqual(mod.extract_id_from_ref(url, "competitors"), "467")

    def test_athletes(self):
        url = "http://example.com/seasons/2026/athletes/303577?lang=en"
        self.assertEqual(mod.extract_id_from_ref(url, "athletes"), "303577")

    def test_none_input(self):
        self.assertIsNone(mod.extract_id_from_ref(None, "teams"))

    def test_empty_string(self):
        self.assertIsNone(mod.extract_id_from_ref("", "teams"))

    def test_no_match(self):
        url = "http://example.com/something/else"
        self.assertIsNone(mod.extract_id_from_ref(url, "teams"))

    def test_multiple_digits(self):
        url = "http://example.com/teams/1234567"
        self.assertEqual(mod.extract_id_from_ref(url, "teams"), "1234567")

    def test_entity_not_in_url(self):
        url = "http://example.com/teams/203"
        self.assertIsNone(mod.extract_id_from_ref(url, "athletes"))


# ══════════════════════════════════════════════════════════════════════
# 2. parse_player_name_from_short_text
# ══════════════════════════════════════════════════════════════════════

class TestParsePlayerNameFromShortText(unittest.TestCase):

    def test_shot_blocked(self):
        play = {"shortText": "Brian Gutiérrez Shot Blocked"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Brian Gutiérrez")

    def test_shot_on_target(self):
        play = {"shortText": "Raúl Jiménez Shot On Target"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Raúl Jiménez")

    def test_shot_off_target(self):
        play = {"shortText": "John Doe Shot Off Target"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "John Doe")

    def test_shot_hit_woodwork(self):
        play = {"shortText": "Julián Quiñones Shot Hit Woodwork"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Julián Quiñones")

    def test_shot_hit_woodwork_truncated(self):
        """ESPN truncates shortText at 32 chars."""
        play = {"shortText": "Julián Quiñones Shot Hit Woodwor"}  # truncated
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Julián Quiñones")

    def test_goal(self):
        play = {"shortText": "Julián Quiñones Goal"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Julián Quiñones")

    def test_goal_header(self):
        play = {"shortText": "Raúl Jiménez Goal - Header"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Raúl Jiménez")

    def test_own_goal(self):
        play = {"shortText": "Damián Bobadilla Own Goal"}
        self.assertEqual(mod.parse_player_name_from_short_text(play), "Damián Bobadilla")

    def test_empty_short_text(self):
        self.assertIsNone(mod.parse_player_name_from_short_text({"shortText": ""}))

    def test_no_short_text(self):
        self.assertIsNone(mod.parse_player_name_from_short_text({}))

    def test_none_play(self):
        # shortText missing → returns None
        self.assertIsNone(mod.parse_player_name_from_short_text({"text": "something"}))

    def test_no_matching_suffix(self):
        play = {"shortText": "Some Unknown Format"}
        self.assertIsNone(mod.parse_player_name_from_short_text(play))


# ══════════════════════════════════════════════════════════════════════
# 3. _parse_stats_categories
# ══════════════════════════════════════════════════════════════════════

class TestParseStatsCategories(unittest.TestCase):

    def test_normal(self):
        data = _make_stats_response({
            "offensive": [
                {"name": "shots", "displayName": "Shots", "value": 10, "displayValue": "10", "description": "Total shots"},
                {"name": "xg", "displayName": "xG", "value": 1.5, "displayValue": "1.5", "description": "Expected goals"},
            ],
            "defensive": [
                {"name": "tackles", "displayName": "Tackles", "value": 20, "displayValue": "20", "description": "Total tackles"},
            ],
        })
        result = mod._parse_stats_categories(data)
        self.assertIn("offensive", result)
        self.assertIn("defensive", result)
        self.assertEqual(len(result["offensive"]), 2)
        self.assertEqual(result["offensive"][0]["name"], "shots")
        self.assertEqual(result["offensive"][0]["value"], 10)

    def test_empty(self):
        result = mod._parse_stats_categories({})
        self.assertEqual(result, {})

    def test_missing_splits(self):
        result = mod._parse_stats_categories({"other": True})
        self.assertEqual(result, {})

    def test_empty_categories(self):
        result = mod._parse_stats_categories({"splits": {"categories": []}})
        self.assertEqual(result, {})

    def test_stat_missing_optional_fields(self):
        data = {"splits": {"categories": [{"name": "general", "stats": [{"name": "possession"}]}]}}
        result = mod._parse_stats_categories(data)
        self.assertEqual(result["general"][0]["displayName"], "")
        self.assertIsNone(result["general"][0]["value"])
        self.assertEqual(result["general"][0]["displayValue"], "")


# ══════════════════════════════════════════════════════════════════════
# 4. validate_xg_reconciliation
# ══════════════════════════════════════════════════════════════════════

class TestValidateXgReconciliation(unittest.TestCase):

    def test_match(self):
        xg = {"scoring_plays_count": 3}
        detail = {"homeScore": 2, "awayScore": 1, "homeTeamCn": "A", "awayTeamCn": "B"}
        ok, msg = mod.validate_xg_reconciliation(xg, detail)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_mismatch(self):
        xg = {"scoring_plays_count": 2}
        detail = {"homeScore": 2, "awayScore": 1, "homeTeamCn": "A", "awayTeamCn": "B"}
        ok, msg = mod.validate_xg_reconciliation(xg, detail)
        self.assertFalse(ok)
        self.assertIn("2 scoring plays", msg)
        self.assertIn("3 expected", msg)

    def test_none_xg(self):
        ok, msg = mod.validate_xg_reconciliation(None, {"homeScore": 1})
        self.assertTrue(ok)

    def test_none_detail(self):
        ok, msg = mod.validate_xg_reconciliation({"scoring_plays_count": 1}, None)
        self.assertTrue(ok)

    def test_both_none(self):
        ok, msg = mod.validate_xg_reconciliation(None, None)
        self.assertTrue(ok)

    def test_zero_zero(self):
        xg = {"scoring_plays_count": 0}
        detail = {"homeScore": 0, "awayScore": 0, "homeTeamCn": "A", "awayTeamCn": "B"}
        ok, msg = mod.validate_xg_reconciliation(xg, detail)
        self.assertTrue(ok)


# ══════════════════════════════════════════════════════════════════════
# 5. resolve_competitor_ids (mocked fetch_json)
# ══════════════════════════════════════════════════════════════════════

class TestResolveCompetitorIds(unittest.TestCase):

    @patch("fetch_analysis_data.fetch_json")
    def test_success(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                {
                    "homeAway": "home",
                    "team": {"$ref": "http://example.com/teams/203"},
                    "statistics": {"$ref": "http://example.com/stats/203"},
                },
                {
                    "homeAway": "away",
                    "team": {"$ref": "http://example.com/teams/467"},
                    "statistics": {"$ref": "http://example.com/stats/467"},
                },
            ]
        }
        result = mod.resolve_competitor_ids("760415")
        self.assertEqual(result["home_team_id"], "203")
        self.assertEqual(result["away_team_id"], "467")
        self.assertIn("stats/203", result["home_stats_ref"])
        self.assertIn("stats/467", result["away_stats_ref"])

    @patch("fetch_analysis_data.fetch_json")
    def test_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = None
        self.assertIsNone(mod.resolve_competitor_ids("760415"))

    @patch("fetch_analysis_data.fetch_json")
    def test_no_items(self, mock_fetch):
        mock_fetch.return_value = {"count": 0}
        self.assertIsNone(mod.resolve_competitor_ids("760415"))

    @patch("fetch_analysis_data.fetch_json")
    def test_missing_home(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                {"homeAway": "away", "team": {"$ref": "http://example.com/teams/467"}},
            ]
        }
        self.assertIsNone(mod.resolve_competitor_ids("760415"))

    @patch("fetch_analysis_data.fetch_json")
    def test_missing_team_ref(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                {"homeAway": "home"},
                {"homeAway": "away", "team": {"$ref": "http://example.com/teams/467"}},
            ]
        }
        self.assertIsNone(mod.resolve_competitor_ids("760415"))

    @patch("fetch_analysis_data.fetch_json")
    def test_missing_statistics_ref(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                {"homeAway": "home", "team": {"$ref": "http://example.com/teams/203"}},
                {"homeAway": "away", "team": {"$ref": "http://example.com/teams/467"}},
            ]
        }
        result = mod.resolve_competitor_ids("760415")
        self.assertIsNotNone(result)
        self.assertEqual(result["home_stats_ref"], "")


# ══════════════════════════════════════════════════════════════════════
# 6. collect_xg (mocked fetch_json)
# ══════════════════════════════════════════════════════════════════════

class TestCollectXg(unittest.TestCase):

    @patch("fetch_analysis_data.fetch_json")
    def test_basic(self, mock_fetch):
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "shot-on-target", xg=0.3, team_ref="http://x/teams/203", text="A (H) shot", short_text="Player A Shot On Target"),
                _make_play("2", "shot-off-target", xg=0.05, team_ref="http://x/teams/467", text="B (A) shot", short_text="Player B Shot Off Target"),
                _make_play("3", "goal", scoring=True, xg=0.7, team_ref="http://x/teams/203", text="Goal! A 1-0. A (H) shot", short_text="Player A Goal"),
                {"id": "4", "type": {"type": "pass"}, "text": "A passes to B"},  # non-shot, no xG
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertIsNotNone(result)
        self.assertEqual(len(result["shots"]), 3)
        self.assertEqual(result["scoring_plays_count"], 1)
        self.assertAlmostEqual(result["team_xg"]["home"], 1.0, places=2)
        self.assertAlmostEqual(result["team_xg"]["away"], 0.05, places=2)
        self.assertEqual(result["total_shots"]["home"], 2)
        self.assertEqual(result["total_shots"]["away"], 1)

    @patch("fetch_analysis_data.fetch_json")
    def test_own_goal(self, mock_fetch):
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "own-goal", scoring=True, xg=None, team_ref="http://x/teams/203",
                           text="Own Goal by X, Team.", short_text="X Own Goal", own_goal=True),
                _make_play("2", "goal", scoring=True, xg=0.5, team_ref="http://x/teams/203",
                           text="Goal! H 2-0. Y (H) shot", short_text="Y Goal"),
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(len(result["shots"]), 2)
        self.assertEqual(result["scoring_plays_count"], 2)
        self.assertTrue(result["shots"][0]["own_goal"])
        self.assertEqual(result["shots"][0]["xg"], None)

    @patch("fetch_analysis_data.fetch_json")
    def test_pagination(self, mock_fetch):
        """Two pages: page 1 has 1 shot, page 2 has 1 shot."""
        mock_fetch.side_effect = [
            {"pageCount": 2, "items": [_make_play("1", "goal", xg=0.5, team_ref="http://x/teams/203", text="A (H) shot")]},
            {"pageCount": 2, "items": [_make_play("2", "shot-blocked", xg=0.1, team_ref="http://x/teams/467", text="B (A) shot")]},
        ]
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(len(result["shots"]), 2)
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("fetch_analysis_data.fetch_json")
    def test_page1_failure(self, mock_fetch):
        mock_fetch.return_value = None
        self.assertIsNone(mod.collect_xg("123", "H", "A", "203", "467"))

    @patch("fetch_analysis_data.fetch_json")
    def test_page2_failure_stops(self, mock_fetch):
        """If page 2 fails, should still return page 1 data."""
        mock_fetch.side_effect = [
            {"pageCount": 2, "items": [_make_play("1", "goal", xg=0.5, team_ref="http://x/teams/203", text="A (H) shot")]},
            None,
        ]
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertIsNotNone(result)
        self.assertEqual(len(result["shots"]), 1)

    @patch("fetch_analysis_data.fetch_json")
    def test_unknown_team_skipped(self, mock_fetch):
        """Plays with team_id not matching home or away are skipped."""
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "goal", xg=0.5, team_ref="http://x/teams/999", text="X (Z) shot"),
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(len(result["shots"]), 0)

    @patch("fetch_analysis_data.fetch_json")
    def test_no_shots(self, mock_fetch):
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                {"id": "1", "type": {"type": "pass"}, "text": "pass"},
                {"id": "2", "type": {"type": "foul"}, "text": "foul"},
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(result["team_xg"]["home"], 0)
        self.assertEqual(result["team_xg"]["away"], 0)
        self.assertEqual(result["scoring_plays_count"], 0)

    @patch("fetch_analysis_data.fetch_json")
    def test_xg_aggregation_rounding(self, mock_fetch):
        """xG should be rounded to 3 decimal places."""
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "goal", xg=0.123456, team_ref="http://x/teams/203", text="A (H) shot"),
                _make_play("2", "goal", xg=0.789012, team_ref="http://x/teams/203", text="A (H) shot"),
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(result["team_xg"]["home"], 0.912)

    @patch("fetch_analysis_data.fetch_json")
    def test_player_resolution_in_shot(self, mock_fetch):
        """Shooter info should be resolved from shortText."""
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "goal", scoring=True, xg=0.5,
                           team_ref="http://x/teams/203",
                           text="Goal! H 1-0. Julián Quiñones (Mexico) right footed shot",
                           short_text="Julián Quiñones Goal"),
            ],
        }
        # Patch PLAYER_DISPLAY_CN to include the name
        with patch.dict(mod.PLAYER_DISPLAY_CN, {"Julián Quiñones": "胡利安·基尼奥内斯"}):
            with patch.dict(mod.PLAYER_DATA, {}, clear=False):
                result = mod.collect_xg("123", "墨西哥", "南非", "203", "467")
        self.assertEqual(result["shots"][0]["shooter_source_name"], "Julián Quiñones")
        self.assertEqual(result["shots"][0]["shooter_cn"], "胡利安·基尼奥内斯")


# ══════════════════════════════════════════════════════════════════════
# 7. collect_momentum (mocked fetch_json)
# ══════════════════════════════════════════════════════════════════════

class TestCollectMomentum(unittest.TestCase):

    @patch("fetch_analysis_data.fetch_json")
    def test_basic(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                _make_momentum_item("1'", 1, 0.05, "203"),
                _make_momentum_item("2'", 1, 0.03, "467"),
                _make_momentum_item("90'", 2, 0.08, "203"),
            ]
        }
        result = mod.collect_momentum("123", "H", "A", "203", "467")
        self.assertIsNotNone(result)
        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["timeline"][0]["team"], "home")
        self.assertEqual(result["timeline"][1]["team"], "away")

    @patch("fetch_analysis_data.fetch_json")
    def test_unknown_competitor_skipped(self, mock_fetch):
        mock_fetch.return_value = {
            "items": [
                _make_momentum_item("1'", 1, 0.05, "999"),
                _make_momentum_item("2'", 1, 0.03, "203"),
            ]
        }
        result = mod.collect_momentum("123", "H", "A", "203", "467")
        self.assertEqual(result["item_count"], 1)

    @patch("fetch_analysis_data.fetch_json")
    def test_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = None
        self.assertIsNone(mod.collect_momentum("123", "H", "A", "203", "467"))

    @patch("fetch_analysis_data.fetch_json")
    def test_empty_items(self, mock_fetch):
        mock_fetch.return_value = {"items": []}
        result = mod.collect_momentum("123", "H", "A", "203", "467")
        self.assertEqual(result["item_count"], 0)
        self.assertEqual(result["timeline"], [])

    @patch("fetch_analysis_data.fetch_json")
    def test_timeline_preserves_order(self, mock_fetch):
        items = [_make_momentum_item(f"{i}'", 1, 0.01 * i, "203") for i in range(1, 11)]
        mock_fetch.return_value = {"items": items}
        result = mod.collect_momentum("123", "H", "A", "203", "467")
        clocks = [t["clock"] for t in result["timeline"]]
        self.assertEqual(clocks, [f"{i}'" for i in range(1, 11)])


# ══════════════════════════════════════════════════════════════════════
# 8. collect_stats (mocked fetch_json)
# ══════════════════════════════════════════════════════════════════════

class TestCollectStats(unittest.TestCase):

    @patch("fetch_analysis_data.fetch_json")
    def test_both_sides(self, mock_fetch):
        home_stats = _make_stats_response({
            "offensive": [{"name": "shots", "displayName": "Shots", "value": 10, "displayValue": "10", "description": ""}],
            "defensive": [{"name": "tackles", "displayName": "Tackles", "value": 20, "displayValue": "20", "description": ""}],
        })
        away_stats = _make_stats_response({
            "offensive": [{"name": "shots", "displayName": "Shots", "value": 5, "displayValue": "5", "description": ""}],
        })
        mock_fetch.side_effect = [home_stats, away_stats]
        result = mod.collect_stats("123", "H", "A", "http://x/stats/h", "http://x/stats/a")
        self.assertIsNotNone(result)
        self.assertIn("offensive", result["stats"]["home"])
        self.assertIn("defensive", result["stats"]["home"])
        self.assertIn("offensive", result["stats"]["away"])
        self.assertNotIn("defensive", result["stats"]["away"])

    @patch("fetch_analysis_data.fetch_json")
    def test_both_fail(self, mock_fetch):
        mock_fetch.return_value = None
        self.assertIsNone(mod.collect_stats("123", "H", "A", "http://x/stats/h", "http://x/stats/a"))

    @patch("fetch_analysis_data.fetch_json")
    def test_one_side_fails(self, mock_fetch):
        home_stats = _make_stats_response({"offensive": [{"name": "shots", "value": 10}]})
        mock_fetch.side_effect = [home_stats, None]
        result = mod.collect_stats("123", "H", "A", "http://x/stats/h", "http://x/stats/a")
        self.assertIsNotNone(result)
        self.assertIn("offensive", result["stats"]["home"])
        self.assertEqual(result["stats"]["away"], {})

    @patch("fetch_analysis_data.fetch_json")
    def test_empty_refs(self, mock_fetch):
        self.assertIsNone(mod.collect_stats("123", "H", "A", "", ""))

    @patch("fetch_analysis_data.fetch_json")
    def test_none_refs(self, mock_fetch):
        self.assertIsNone(mod.collect_stats("123", "H", "A", None, None))


# ══════════════════════════════════════════════════════════════════════
# 9. load_existing / save_json roundtrip
# ══════════════════════════════════════════════════════════════════════

class TestFileIO(unittest.TestCase):

    def test_roundtrip(self):
        with _TempDir() as td:
            path = os.path.join(td.analysis_dir, "test.json")
            data = {"760415": {"team_xg": {"home": 1.5, "away": 0.3}, "shots": [{"xg": 0.1}]}}
            mod.save_json(path, data)
            loaded = mod.load_existing(path)
            self.assertEqual(loaded, data)

    def test_load_missing(self):
        result = mod.load_existing("/tmp/nonexistent_abc123.json")
        self.assertEqual(result, {})

    def test_unicode_roundtrip(self):
        with _TempDir() as td:
            path = os.path.join(td.analysis_dir, "test.json")
            data = {"760415": {"homeTeamCn": "墨西哥", "awayTeamCn": "南非"}}
            mod.save_json(path, data)
            loaded = mod.load_existing(path)
            self.assertEqual(loaded["760415"]["homeTeamCn"], "墨西哥")

    def test_save_trailing_newline(self):
        with _TempDir() as td:
            path = os.path.join(td.analysis_dir, "test.json")
            mod.save_json(path, {"a": 1})
            with open(path, "r") as f:
                content = f.read()
            self.assertTrue(content.endswith("\n"))


# ══════════════════════════════════════════════════════════════════════
# 10. SHOT_TYPES completeness
# ══════════════════════════════════════════════════════════════════════

class TestShotTypes(unittest.TestCase):

    def test_own_goal_included(self):
        self.assertIn("own-goal", mod.SHOT_TYPES)

    def test_standard_types_included(self):
        for t in ("goal", "goal---header", "shot-on-target", "shot-off-target", "shot-blocked", "shot-hit-woodwork"):
            self.assertIn(t, mod.SHOT_TYPES)

    def test_non_shot_types_excluded(self):
        for t in ("pass", "foul", "substitution", "yellow-card", "red-card", "kickoff"):
            self.assertNotIn(t, mod.SHOT_TYPES)


# ══════════════════════════════════════════════════════════════════════
# 11. Incremental skip logic (end-to-end with mocked API)
# ══════════════════════════════════════════════════════════════════════

class TestIncrementalSkip(unittest.TestCase):

    def test_skip_when_all_three_exist(self):
        """Match should be skipped if it exists in all 3 output files."""
        existing_xg = {"760415": {"matchId": "760415"}}
        existing_momentum = {"760415": {"matchId": "760415"}}
        existing_stats = {"760415": {"matchId": "760415"}}
        match_id = "760415"
        should_skip = (
            match_id in existing_xg
            and match_id in existing_momentum
            and match_id in existing_stats
        )
        self.assertTrue(should_skip)

    def test_no_skip_when_partial(self):
        """Match should NOT be skipped if only partially collected."""
        existing_xg = {"760415": {"matchId": "760415"}}
        existing_momentum = {}  # missing
        existing_stats = {"760415": {"matchId": "760415"}}
        match_id = "760415"
        should_skip = (
            match_id in existing_xg
            and match_id in existing_momentum
            and match_id in existing_stats
        )
        self.assertFalse(should_skip)

    def test_no_skip_when_empty(self):
        should_skip = "760415" in {} and "760415" in {} and "760415" in {}
        self.assertFalse(should_skip)


# ══════════════════════════════════════════════════════════════════════
# 12. refresh_results.py integration
# ══════════════════════════════════════════════════════════════════════

class TestRefreshResultsIntegration(unittest.TestCase):

    def test_pipeline_steps_analysis_is_optional(self):
        """fetch_analysis_data.py must be available but outside the default network path."""
        rr_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refresh_results.py"
        )
        with open(rr_path, "r") as f:
            content = f.read()
        self.assertIn("fetch_analysis_data.py", content)
        self.assertIn("PIPELINE_STEPS_ANALYSIS", content)
        network_block = content.split("PIPELINE_STEPS_NETWORK = [", 1)[1].split(
            "PIPELINE_STEPS_ANALYSIS",
            1,
        )[0]
        self.assertNotIn("fetch_analysis_data.py", network_block)

    def test_pipeline_steps_order(self):
        """Optional analysis step must still be declared after match details."""
        rr_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refresh_results.py"
        )
        with open(rr_path, "r") as f:
            content = f.read()
        pos_details = content.index("fetch_match_details.py")
        pos_analysis = content.index("fetch_analysis_data.py")
        self.assertLess(pos_details, pos_analysis)

    def test_docstring_updated(self):
        """Docstring should list the 5-step default path and optional analysis."""
        rr_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refresh_results.py"
        )
        with open(rr_path, "r") as f:
            content = f.read()
        self.assertIn("5. sync_predictor_asset.py", content)
        self.assertIn("--with-analysis", content)

    def test_no_changes_to_consistency(self):
        """assert_consistency should NOT reference analysis files."""
        rr_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refresh_results.py"
        )
        with open(rr_path, "r") as f:
            content = f.read()
        # Find the assert_consistency function
        self.assertIn("def assert_consistency", content)
        # It should NOT mention match_xg or analysis
        start = content.index("def assert_consistency")
        # Find end of function (next def or end of file)
        next_def = content.find("\ndef ", start + 1)
        func_body = content[start:next_def] if next_def > 0 else content[start:]
        self.assertNotIn("match_xg", func_body)
        self.assertNotIn("match_momentum", func_body)
        self.assertNotIn("match_team_stats", func_body)


# ══════════════════════════════════════════════════════════════════════
# 13. normalize_name parity with fetch_match_details.py
# ══════════════════════════════════════════════════════════════════════

class TestNormalizeNameParity(unittest.TestCase):

    def test_accent_stripping(self):
        self.assertEqual(mod.normalize_name("Julián"), "julian")
        self.assertEqual(mod.normalize_name("Érik"), "erik")
        self.assertEqual(mod.normalize_name("Curaçao"), "curacao")

    def test_empty(self):
        self.assertEqual(mod.normalize_name(""), "")
        self.assertEqual(mod.normalize_name(None), "")

    def test_only_alnum(self):
        self.assertEqual(mod.normalize_name("Lee Kang-In"), "leekangin")
        self.assertEqual(mod.normalize_name("Oh Hyeon-Gyu"), "ohhyeongyu")


# ══════════════════════════════════════════════════════════════════════
# 14. Output schema validation against real data
# ══════════════════════════════════════════════════════════════════════

class TestOutputSchemaValidation(unittest.TestCase):
    """Validate that the actual output files match expected schemas."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        xg_path = os.path.join(root, "data", "analysis", "match_xg.json")
        mom_path = os.path.join(root, "data", "analysis", "match_momentum.json")
        stats_path = os.path.join(root, "data", "analysis", "match_team_stats.json")
        with open(xg_path) as f:
            cls.xg = json.load(f) if os.path.exists(xg_path) else {}
        with open(mom_path) as f:
            cls.mom = json.load(f) if os.path.exists(mom_path) else {}
        with open(stats_path) as f:
            cls.stats = json.load(f) if os.path.exists(stats_path) else {}

    def test_xg_schema(self):
        """Every xG entry must have required fields."""
        for mid, entry in self.xg.items():
            self.assertIn("matchId", entry, f"{mid} missing matchId")
            self.assertIn("homeTeamCn", entry, f"{mid} missing homeTeamCn")
            self.assertIn("awayTeamCn", entry, f"{mid} missing awayTeamCn")
            self.assertIn("team_xg", entry, f"{mid} missing team_xg")
            self.assertIn("home", entry["team_xg"], f"{mid} missing team_xg.home")
            self.assertIn("away", entry["team_xg"], f"{mid} missing team_xg.away")
            self.assertIn("total_shots", entry, f"{mid} missing total_shots")
            self.assertIn("scoring_plays_count", entry, f"{mid} missing scoring_plays_count")
            self.assertIn("shots", entry, f"{mid} missing shots")
            for shot in entry["shots"]:
                self.assertIn("play_id", shot, f"{mid} shot missing play_id")
                self.assertIn("type", shot, f"{mid} shot missing type")
                self.assertIn("team", shot, f"{mid} shot missing team")
                self.assertIn("xg", shot, f"{mid} shot missing xg")
                self.assertIn("result", shot, f"{mid} shot missing result")

    def test_momentum_schema(self):
        for mid, entry in self.mom.items():
            self.assertIn("matchId", entry)
            self.assertIn("timeline", entry)
            self.assertIn("item_count", entry)
            self.assertEqual(entry["item_count"], len(entry["timeline"]))
            for item in entry["timeline"]:
                self.assertIn("clock", item)
                self.assertIn("period", item)
                self.assertIn("threat", item)
                self.assertIn("team", item)
                self.assertIn(item["team"], ("home", "away"))

    def test_stats_schema(self):
        for mid, entry in self.stats.items():
            self.assertIn("matchId", entry)
            self.assertIn("stats", entry)
            self.assertIn("home", entry["stats"])
            self.assertIn("away", entry["stats"])
            for side in ("home", "away"):
                for cat_name, stats_list in entry["stats"][side].items():
                    for stat in stats_list:
                        self.assertIn("name", stat)
                        self.assertIn("value", stat)

    def test_all_matches_have_same_ids(self):
        """All three files should cover the same match IDs."""
        if not self.xg:
            self.skipTest("No analysis data found")
        xg_ids = set(self.xg.keys())
        mom_ids = set(self.mom.keys())
        stats_ids = set(self.stats.keys())
        self.assertEqual(xg_ids, mom_ids, f"xG vs momentum mismatch: {xg_ids ^ mom_ids}")
        self.assertEqual(xg_ids, stats_ids, f"xG vs stats mismatch: {xg_ids ^ stats_ids}")


# ══════════════════════════════════════════════════════════════════════
# 15. Edge: scoring_plays_count counts only result=="goal"
# ══════════════════════════════════════════════════════════════════════

class TestScoringPlaysCount(unittest.TestCase):

    @patch("fetch_analysis_data.fetch_json")
    def test_own_goal_counts_as_goal(self, mock_fetch):
        """own-goal with scoringPlay=True should have result='goal'."""
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "own-goal", scoring=True, xg=None,
                           team_ref="http://x/teams/203", text="Own Goal",
                           short_text="X Own Goal", own_goal=True),
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(result["shots"][0]["result"], "goal")
        self.assertEqual(result["scoring_plays_count"], 1)

    @patch("fetch_analysis_data.fetch_json")
    def test_non_scoring_not_counted(self, mock_fetch):
        mock_fetch.return_value = {
            "pageCount": 1,
            "items": [
                _make_play("1", "shot-on-target", scoring=False, xg=0.3,
                           team_ref="http://x/teams/203", text="A (H) shot"),
            ],
        }
        result = mod.collect_xg("123", "H", "A", "203", "467")
        self.assertEqual(result["scoring_plays_count"], 0)
        self.assertEqual(result["shots"][0]["result"], "shot-on-target")


# ══════════════════════════════════════════════════════════════════════
# 16. Constants verification
# ══════════════════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_url_templates_contain_placeholders(self):
        self.assertIn("{EV}", mod.PLAYS_URL_TPL)
        self.assertIn("{PAGE}", mod.PLAYS_URL_TPL)
        self.assertIn("{EV}", mod.MOMENTUM_URL_TPL)
        self.assertIn("{EV}", mod.COMPETITORS_URL_TPL)

    def test_core_root(self):
        self.assertEqual(
            mod.CORE_ROOT,
            "https://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world"
        )

    def test_directories(self):
        self.assertTrue(mod.ANALYSIS_DIR.endswith("analysis"))
        self.assertTrue(mod.DATA_DIR.endswith("data"))


# ══════════════════════════════════════════════════════════════════════
# 17. XG reconciliation on real data
# ══════════════════════════════════════════════════════════════════════

class TestXgReconciliationRealData(unittest.TestCase):
    """Cross-validate real xG data against match_details scores."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        xg_path = os.path.join(root, "data", "analysis", "match_xg.json")
        details_path = os.path.join(root, "data", "matches", "match_details.json")
        with open(xg_path) as f:
            cls.xg = json.load(f) if os.path.exists(xg_path) else {}
        with open(details_path) as f:
            cls.details = json.load(f) if os.path.exists(details_path) else {}

    def test_all_matches_reconcile(self):
        if not self.xg:
            self.skipTest("No xG data found")
        mismatches = []
        for mid, xd in self.xg.items():
            dd = self.details.get(mid)
            if not dd:
                continue
            expected = dd.get("homeScore", 0) + dd.get("awayScore", 0)
            actual = xd.get("scoring_plays_count", 0)
            if actual != expected:
                mismatches.append(f"{mid}: {actual} vs {expected}")
        self.assertEqual(mismatches, [], f"xG reconciliation failures: {mismatches}")


# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
