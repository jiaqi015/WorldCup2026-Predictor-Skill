#!/usr/bin/env python3
"""Regression tests for the shared ESPN position fallback."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from compute_player_threats import extract_js_var, parse_js_dict
from player_positions import ESPN_POSITION_FALLBACK, normalize_espn_position
from update_index import generate_new_variables, load_data


class TestPlayerPositionFallback(unittest.TestCase):
    def test_all_espn_categories_are_supported(self):
        self.assertEqual(
            ESPN_POSITION_FALLBACK,
            {"G": "门将", "D": "后卫", "M": "中场", "F": "前锋"},
        )

    def test_codes_are_normalized(self):
        self.assertEqual(normalize_espn_position(" g "), "门将")
        self.assertEqual(normalize_espn_position("d"), "后卫")
        self.assertEqual(normalize_espn_position("M"), "中场")
        self.assertEqual(normalize_espn_position("F"), "前锋")

    def test_unknown_values_use_midfield_fallback(self):
        for value in (None, "", "X", 10):
            self.assertEqual(normalize_espn_position(value), "中场")

    def test_known_centre_backs_are_not_guessed_from_jersey_number(self):
        squads = json.loads(
            (ROOT / "data" / "squads" / "squads_partial.json").read_text()
        )
        known_centre_backs = (
            ("Portugal", "Rúben Dias"),
            ("Mexico", "César Montes"),
            ("Brazil", "Gabriel Magalhães"),
        )
        for team, name in known_centre_backs:
            player = next(p for p in squads[team]["players"] if p["name"] == name)
            self.assertEqual(player["position"], "D")
            self.assertEqual(normalize_espn_position(player["position"]), "后卫")

    def test_forward_number_ten_is_not_misclassified_as_midfielder(self):
        squads = json.loads(
            (ROOT / "data" / "squads" / "squads_partial.json").read_text()
        )
        mbappe = next(
            p for p in squads["France"]["players"] if p["name"] == "Kylian Mbappé"
        )
        self.assertEqual(mbappe["position"], "F")
        self.assertEqual(mbappe["jersey"], "10")
        self.assertEqual(normalize_espn_position(mbappe["position"]), "前锋")

    def test_selected_starter_wins_a_localized_name_collision(self):
        squads, mapping = load_data()
        generated = generate_new_variables(squads, mapping)
        positions = parse_js_dict(extract_js_var(generated, "POS"))
        # Gabriel Magalhães (#3, D) is selected before Gabriel Martinelli
        # (#22, F); both currently share the app alias "加布里埃尔".
        self.assertEqual(positions["巴西"]["加布里埃尔"], "后卫")

    def test_generated_positions_keep_source_granularity(self):
        squads, mapping = load_data()
        generated = generate_new_variables(squads, mapping)
        positions = parse_js_dict(extract_js_var(generated, "POS"))

        self.assertEqual(positions["加拿大"]["拉林"], "前锋")
        self.assertEqual(positions["加拿大"]["戴维"], "前锋")
        self.assertEqual(positions["英格兰"]["凯恩"], "前锋")
        self.assertEqual(positions["苏格兰"]["罗伯逊"], "后卫")
        self.assertEqual(positions["苏格兰"]["麦金"], "中场")


if __name__ == "__main__":
    unittest.main()
