#!/usr/bin/env python3
"""Regression tests for canonical knockout bracket-slot assignment."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fetch_match_data.py"
SCHEDULE = ROOT / "data" / "matches" / "match_schedule.json"


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_match_data", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("fetch_match_data.py must be importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestKnockoutBracketSlots(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))

    def test_current_schedule_maps_every_knockout_match_once(self):
        schedule = copy.deepcopy(self.schedule)
        assigned = self.module.assign_bracket_slots(schedule)
        knockout = [match for match in schedule.values() if match["stage"] != "group"]

        self.assertEqual(assigned, 32)
        self.assertEqual(len(knockout), 32)
        self.assertEqual(len({match.get("bracketSlot") for match in knockout}), 32)
        self.assertNotIn(None, {match.get("bracketSlot") for match in knockout})

    def test_current_schedule_matches_official_topology(self):
        schedule = copy.deepcopy(self.schedule)
        self.module.assign_bracket_slots(schedule)
        expected = {
            "760486": "R1", "760489": "R2", "760488": "R3", "760487": "R4",
            "760492": "R5", "760490": "R6", "760491": "R7", "760495": "R8",
            "760494": "R9", "760493": "R10", "760496": "R11", "760497": "R12",
            "760498": "R13", "760500": "R14", "760501": "R15", "760499": "R16",
            "760503": "L1", "760502": "L2", "760504": "L3", "760505": "L4",
            "760506": "L5", "760507": "L6", "760509": "L7", "760508": "L8",
            "760510": "Q1", "760511": "Q2", "760512": "Q3", "760513": "Q4",
            "760514": "S1", "760515": "S2", "760516": "3RD", "760517": "FINAL",
        }
        self.assertEqual(
            {match_id: schedule[match_id].get("bracketSlot") for match_id in expected},
            expected,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
