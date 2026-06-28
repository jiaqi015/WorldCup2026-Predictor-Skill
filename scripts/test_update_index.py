#!/usr/bin/env python3
"""Tests for update_index.py — PHOTO_MAP generation and index update."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import update_index as ui


def generated_text():
    squads = ui.load_data()[0]
    mapping = ui.load_data()[1]
    return ui.generate_new_variables(squads, mapping)


class TestGetPlayerCnName(unittest.TestCase):

    def test_qualified_key_preferred(self):
        mapping = {
            "Martinez (Argentina)": {"cn": "马丁内斯ARG"},
            "Martinez (Uruguay)": {"cn": "马丁内斯URU"},
        }
        result = ui.get_player_cn_name("Martinez", mapping, "Argentina")
        self.assertEqual(result, "马丁内斯ARG")

    def test_bare_key_fallback(self):
        mapping = {"Mbappe": {"cn": "姆巴佩"}}
        result = ui.get_player_cn_name("Mbappe", mapping, "France")
        self.assertEqual(result, "姆巴佩")

    def test_no_key_returns_english(self):
        mapping = {}
        result = ui.get_player_cn_name("Unknown", mapping, "Test")
        self.assertEqual(result, "Unknown")

    def test_qualified_over_bare(self):
        mapping = {
            "Silva": {"cn": "席尔瓦-bare"},
            "Silva (Brazil)": {"cn": "席尔瓦BRA"},
        }
        result = ui.get_player_cn_name("Silva", mapping, "Brazil")
        self.assertEqual(result, "席尔瓦BRA")


class TestGenerateNewVariables(unittest.TestCase):

    def test_photo_map_has_team_qualified_keys(self):
        """PHOTO_MAP should contain 'team|name' qualified keys."""
        text = generated_text()
        # Should contain qualified keys like "法国|姆巴佩"
        self.assertIn("|", text)

    def test_output_contains_pl_var(self):
        text = generated_text()
        self.assertIn("var PL=", text)

    def test_output_contains_photo_map(self):
        text = generated_text()
        self.assertIn("PHOTO_MAP", text)

    def test_output_contains_team_scoped_jersey_map(self):
        text = generated_text()
        self.assertIn("var PLAYER_JERSEYS=", text)
        self.assertIn('"阿根廷"', text)
        self.assertIn('"梅西":"10"', text)

    def test_first_lineups_from_matches_uses_first_group_game(self):
        starters = [
            {
                "appAlias": f"首发{i}",
                "sourceName": f"Starter {i}",
                "jersey": str(i),
                "positionAbbr": "G" if i == 1 else "D" if i < 6 else "M" if i < 10 else "F",
                "positionName": "Position",
                "formationPlace": str(i),
                "mappingStatus": "matched_team_player",
            }
            for i in range(1, 12)
        ]
        result = ui.first_lineups_from_matches(
            {
                "2": {"id": "2", "stage": "group", "date": "2026-06-20T00:00Z", "home": "主队", "away": "客队"},
                "1": {"id": "1", "stage": "group", "date": "2026-06-10T00:00Z", "home": "主队", "away": "另一队"},
            },
            {
                "1": {
                    "lineups": {
                        "home": {
                            "source": "ESPN summary API rosters",
                            "starters": starters,
                        }
                    }
                },
                "2": {
                    "lineups": {
                        "home": {
                            "source": "later match",
                            "starters": [{**p, "appAlias": "不该出现"} for p in starters],
                        }
                    }
                },
            },
        )

        self.assertEqual(result["主队"]["matchId"], "1")
        self.assertEqual(result["主队"]["starters"][0]["name"], "首发1")
        self.assertEqual(len(result["主队"]["starters"]), 11)
        self.assertIn("shape", result["主队"])

    def test_estimate_shape_treats_dm_as_midfield(self):
        starters = [{"positionAbbr": "G"}]
        starters += [{"positionAbbr": pos} for pos in ["RB", "LB", "CD-R", "CD-L"]]
        starters += [{"positionAbbr": pos} for pos in ["DM", "CM-R", "AM", "LM"]]
        starters += [{"positionAbbr": pos} for pos in ["F", "RF"]]

        self.assertEqual(ui.estimate_shape(starters), "4-4-2")


if __name__ == "__main__":
    unittest.main()
