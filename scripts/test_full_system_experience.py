#!/usr/bin/env python3
"""Tests for the full-system experience validation script."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "full_system_experience_test.py"


def load_module():
    spec = importlib.util.spec_from_file_location("full_system_experience_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("full_system_experience_test.py must be importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFullSystemExperienceScript(unittest.TestCase):
    def test_script_exists_and_has_a_clear_coverage_contract(self):
        self.assertTrue(SCRIPT.is_file(), "full_system_experience_test.py must exist")
        module = load_module()
        areas = {item["area"] for item in module.COVERAGE_CONTRACT}
        self.assertEqual(
            areas,
            {
                "skill_install_learn_use_verify",
                "skill_live_and_maintenance_commands",
                "browser_guided_prediction",
                "browser_mode_matrix",
                "share_and_readonly_state",
                "public_deployment",
            },
        )

    def test_coverage_contract_names_authoritative_evidence(self):
        module = load_module()
        for item in module.COVERAGE_CONTRACT:
            with self.subTest(area=item["area"]):
                self.assertGreaterEqual(len(item["requirements"]), 2)
                self.assertGreaterEqual(len(item["evidence"]), 2)
                self.assertTrue(all(isinstance(value, str) and value for value in item["requirements"]))
                self.assertTrue(all(isinstance(value, str) and value for value in item["evidence"]))

    def test_cli_exposes_local_public_and_browser_controls(self):
        module = load_module()
        parser = module.build_parser()
        args = parser.parse_args(
            [
                "--skip-browser",
                "--public-url",
                "https://www.cameraclaw.cn/2026",
                "--browser",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        )
        self.assertTrue(args.skip_browser)
        self.assertEqual(args.public_url, "https://www.cameraclaw.cn/2026")
        self.assertIn("Google Chrome", args.browser)

    def test_browser_executable_resolution_prefers_existing_system_chrome(self):
        module = load_module()
        path = module.resolve_browser_executable(None)
        if path is not None:
            self.assertTrue(path.is_file())
            self.assertIn(path.name, {"Google Chrome", "Chromium", "Microsoft Edge"})

    def test_playbook_mode_matrix_is_complete(self):
        module = load_module()
        payload = module.load_json(module.PLAYBOOKS)
        matrix = module.build_mode_matrix(payload)
        self.assertEqual(
            set(matrix),
            {"guided_play", "one_shot_simulation", "live_results", "scoring", "maintenance"},
        )
        self.assertTrue(all(item["scenario_count"] >= 4 for item in matrix.values()))
        self.assertTrue(any(item["primary_surface"] == "browser_app" for item in matrix.values()))
        self.assertTrue(any(item["primary_surface"] == "codex_skill" for item in matrix.values()))
        self.assertTrue(any(item["primary_surface"] == "hybrid" for item in matrix.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
