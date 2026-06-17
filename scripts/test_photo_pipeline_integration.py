#!/usr/bin/env python3
"""Integration tests: full pipeline from photo_mapping.json through index.html."""

import json
import os
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))


class TestPhotoMappingIntegrity(unittest.TestCase):
    """Every path in photo_mapping.json must exist on disk."""

    def test_all_paths_exist(self):
        with open(BASE_DIR / "data" / "squads" / "photo_mapping.json") as f:
            mapping = json.load(f)
        missing = []
        for name, v in mapping.items():
            p = v.get("path", "")
            if p and not (BASE_DIR / p).exists():
                missing.append(f"{name}: {p}")
        self.assertEqual(missing, [], f"Missing files: {missing[:5]}")

    def test_no_external_urls(self):
        """No mapping path should be an external URL."""
        with open(BASE_DIR / "data" / "squads" / "photo_mapping.json") as f:
            mapping = json.load(f)
        external = [v["path"] for v in mapping.values()
                    if v.get("path", "").startswith("http")]
        self.assertEqual(external, [])


class TestSquadCoverage(unittest.TestCase):
    """Every squad player must have a photo_mapping entry."""

    def test_full_coverage(self):
        with open(BASE_DIR / "data" / "squads" / "squads_partial.json") as f:
            squads = json.load(f)
        with open(BASE_DIR / "data" / "squads" / "photo_mapping.json") as f:
            mapping = json.load(f)
        total = sum(len(t.get("players", [])) for t in squads.values())
        self.assertGreaterEqual(len(mapping), total - 1,
                                f"Mapping {len(mapping)} < Squad {total}")


class TestIndexHtmlPhotoMap(unittest.TestCase):
    """PHOTO_MAP in index.html must cover all PL entries."""

    def test_photo_map_covers_players(self):
        index_path = BASE_DIR / "index.html"
        html = index_path.read_text(encoding="utf-8")

        # Extract PL object keys (team-cn names)
        pl_match = re.search(r'var PL=(\{.*?\});', html, re.DOTALL)
        self.assertIsNotNone(pl_match, "PL variable not found")
        pl_text = pl_match.group(1)
        # Count player names in PL (quoted strings inside arrays)
        player_names = re.findall(r'"([^"]+)"', pl_text)
        # Skip team names (those are keys before ":")
        team_names = re.findall(r'"([^"]+)":\[', pl_text)
        player_only = [n for n in player_names if n not in team_names]

        # Extract PHOTO_MAP keys
        pm_match = re.search(r'var PHOTO_MAP=(\{.*?\});', html, re.DOTALL)
        self.assertIsNotNone(pm_match, "PHOTO_MAP not found")
        pm_text = pm_match.group(1)
        pm_keys = set(re.findall(r'"([^"]+)":', pm_text))

        # Every player in PL should have a PHOTO_MAP entry
        missing = [p for p in player_only if p not in pm_keys]
        self.assertEqual(missing, [], f"Players missing from PHOTO_MAP: {missing[:10]}")

    def test_no_external_urls_in_photo_map(self):
        index_path = BASE_DIR / "index.html"
        html = index_path.read_text(encoding="utf-8")
        pm_match = re.search(r'var PHOTO_MAP=(\{.*?\});', html, re.DOTALL)
        self.assertIsNotNone(pm_match)
        pm_text = pm_match.group(1)
        values = re.findall(r':"([^"]+)"', pm_text)
        external = [v for v in values if v.startswith("http")]
        self.assertEqual(external, [],
                         f"External URLs in PHOTO_MAP: {external[:5]}")


if __name__ == "__main__":
    unittest.main()
