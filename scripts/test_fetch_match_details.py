#!/usr/bin/env python3
"""Tests for fetch_match_details.py - player name resolution."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import fetch_match_details as fdm


def add_player_mapping(key, info):
    """Add one mapping entry using the same indexes as load_player_mapping()."""
    fdm.PLAYER_DATA[key] = info
    fdm.PLAYER_DATA_NORMALIZED.setdefault(fdm.normalize_name(key), []).append((key, info))
    base_name = fdm.base_player_key(key)
    if base_name and base_name != key:
        fdm.PLAYER_DATA_NORMALIZED.setdefault(fdm.normalize_name(base_name), []).append((key, info))


class TestResolvePlayer(unittest.TestCase):
    """Test resolve_player() prefers qualified keys over bare keys."""

    def setUp(self):
        fdm.PLAYER_DATA.clear()
        fdm.PLAYER_DATA_NORMALIZED.clear()
        fdm.PLAYER_DISPLAY_CN.clear()

    def test_prefers_qualified_key_over_bare(self):
        """Qualified key 'X (Team)' should win over bare key 'X'."""
        add_player_mapping("Raúl Jiménez", {"cn": "希门尼斯", "team": "墨西哥", "jersey": 9})
        add_player_mapping("Raúl Jiménez (Mexico)", {"cn": "希门尼斯MEX", "team": "墨西哥", "jersey": 9})

        result = fdm.resolve_player("Raúl Jiménez", "墨西哥")
        self.assertEqual(result["app_alias"], "希门尼斯MEX")
        self.assertEqual(result["mapping_key"], "Raúl Jiménez (Mexico)")

    def test_real_mapping_prefers_qualified_key_over_bare(self):
        """The checked-in player mapping should resolve the known collision."""
        fdm.load_player_mapping()

        result = fdm.resolve_player("Raúl Jiménez", "墨西哥")

        self.assertEqual(result["app_alias"], "希门尼斯MEX")
        self.assertEqual(result["mapping_key"], "Raúl Jiménez (Mexico)")

    def test_bare_key_fallback_when_no_qualified(self):
        """Bare key should work when no qualified key exists."""
        add_player_mapping("Kylian Mbappé", {"cn": "姆巴佩", "team": "法国", "jersey": 10})

        result = fdm.resolve_player("Kylian Mbappé", "法国")
        self.assertEqual(result["app_alias"], "姆巴佩")
        self.assertEqual(result["mapping_key"], "Kylian Mbappé")

    def test_team_filter_still_applies(self):
        """Qualified key for wrong team should not match."""
        add_player_mapping("Emiliano Martínez", {"cn": "马丁内斯", "team": "乌拉圭", "jersey": 1})
        add_player_mapping("Emiliano Martínez (Argentina)", {"cn": "马丁内斯ARG", "team": "阿根廷", "jersey": 23})
        add_player_mapping("Emiliano Martínez (Uruguay)", {"cn": "马丁内斯URU", "team": "乌拉圭", "jersey": 1})

        result = fdm.resolve_player("Emiliano Martínez", "阿根廷")
        self.assertEqual(result["app_alias"], "马丁内斯ARG")
        self.assertEqual(result["mapping_key"], "Emiliano Martínez (Argentina)")

    def test_normalized_match_prefers_qualified(self):
        """Normalized lookup should also prefer qualified keys."""
        add_player_mapping("José María Giménez", {"cn": "希门内斯", "team": "乌拉圭", "jersey": 2})
        add_player_mapping("José María Giménez (Uruguay)", {"cn": "希门内斯URU", "team": "乌拉圭", "jersey": 2})

        # ESPN gives slightly different accent
        result = fdm.resolve_player("Jose Maria Gimenez", "乌拉圭")
        self.assertEqual(result["app_alias"], "希门内斯URU")
        self.assertEqual(result["mapping_key"], "José María Giménez (Uruguay)")

    def test_returns_source_only_when_no_match(self):
        """Should return source_only status when no match found."""
        result = fdm.resolve_player("Unknown Player", "Unknown Team")
        self.assertEqual(result["mapping_status"], "source_only")
        self.assertIsNone(result["app_alias"])

    def test_display_cn_override(self):
        """PLAYER_DISPLAY_CN should override app_alias for display_name_cn."""
        fdm.PLAYER_DISPLAY_CN["Raúl Jiménez"] = "劳尔·希门尼斯"
        add_player_mapping("Raúl Jiménez", {"cn": "希门尼斯", "team": "墨西哥", "jersey": 9})
        add_player_mapping("Raúl Jiménez (Mexico)", {"cn": "希门尼斯MEX", "team": "墨西哥", "jersey": 9})

        result = fdm.resolve_player("Raúl Jiménez", "墨西哥")
        # display_name_cn uses PLAYER_DISPLAY_CN override
        self.assertEqual(result["display_name_cn"], "劳尔·希门尼斯")
        # app_alias uses mapping cn (qualified key preferred)
        self.assertEqual(result["app_alias"], "希门尼斯MEX")


class TestParseKeyEvents(unittest.TestCase):
    """Test ESPN scoring event normalization."""

    def setUp(self):
        fdm.PLAYER_DATA.clear()
        fdm.PLAYER_DATA_NORMALIZED.clear()
        fdm.PLAYER_DISPLAY_CN.clear()
        add_player_mapping("Penalty Taker", {"cn": "点球手", "team": "主队", "jersey": 10})
        add_player_mapping("Defender OG", {"cn": "乌龙后卫", "team": "客队", "jersey": 4})

    def test_penalty_and_own_goal_are_scoring_events(self):
        events = fdm.parse_key_events(
            [
                {
                    "type": {"id": "70", "text": "Penalty - Scored"},
                    "penaltyKick": True,
                    "team": {"id": "1"},
                    "clock": {"displayValue": "17'"},
                    "participants": [{"athlete": {"displayName": "Penalty Taker"}}],
                },
                {
                    "type": {"id": "70", "text": "Own Goal"},
                    "ownGoal": True,
                    "team": {"id": "1"},
                    "clock": {"displayValue": "44'"},
                    "participants": [{"athlete": {"displayName": "Defender OG"}}],
                },
            ],
            "1",
            "主队",
            "客队",
        )

        self.assertEqual([event["type"] for event in events], ["penalty_goal", "own_goal"])
        self.assertTrue(events[0]["penalty_kick"])
        self.assertFalse(events[0]["own_goal"])
        self.assertEqual(events[0]["scorer_team_cn"], "主队")
        self.assertEqual(events[1]["team_cn"], "主队")
        self.assertEqual(events[1]["scoring_team_cn"], "主队")
        self.assertEqual(events[1]["player_team_cn"], "客队")
        self.assertEqual(events[1]["scorer_team_cn"], "客队")


if __name__ == "__main__":
    unittest.main()
