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


if __name__ == "__main__":
    unittest.main()
