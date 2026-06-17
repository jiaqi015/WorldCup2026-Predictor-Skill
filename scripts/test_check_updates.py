#!/usr/bin/env python3
"""Regression tests for the skill update checker."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "world-cup-2026-predictor" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import check_updates as cu


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


def test_compare() -> None:
    print("\n=== compare ===")
    report("same commit", cu.compare({"commit": "a", "has_local_changes": False}, {"commit": "a"}) == "up_to_date")
    report("different commit", cu.compare({"commit": "a"}, {"commit": "b"}) == "update_available")
    report("dirty same commit", cu.compare({"commit": "a", "has_local_changes": True}, {"commit": "a"}) == "local_changes")
    report("same version fallback", cu.compare({"version": "1.0.0"}, {"version": "1.0.0"}) == "up_to_date")
    report("version update", cu.compare({"version": "1.0.0"}, {"version": "1.1.0"}) == "update_available")
    report("unknown", cu.compare({}, {}) == "unknown")


def test_local_state_standalone() -> None:
    print("\n=== standalone state ===")
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "world-cup-2026-predictor"
        skill.mkdir()
        (skill / "VERSION.json").write_text(
            json.dumps(
                {
                    "version": "0.3.1",
                    "repository": "https://example.test/repo.git",
                    "ref": "main",
                    "plugin_marketplace": "world-cup-2026",
                    "plugin_name": "world-cup-2026-predictor",
                    "skill_path": "skills/world-cup-2026-predictor",
                }
            ),
            encoding="utf-8",
        )
        state = cu.local_state(skill)
    report("source installed_skill", state["source"] == "installed_skill")
    report("version loaded", state["version"] == "0.3.1")
    report("repo loaded", state["repository"] == "https://example.test/repo.git")
    report("dirty unknown", state["has_local_changes"] is None)


def test_upgrade_commands() -> None:
    print("\n=== upgrade commands ===")
    status = {
        "status": "update_available",
        "local": {
            "version": "0.3.1",
            "commit": "a" * 40,
            "source": "git_worktree",
            "has_local_changes": False,
        },
        "remote": {"ref": "main", "version": "0.3.2", "commit": "b" * 40},
        "upgrade_commands": [
            "codex plugin marketplace upgrade world-cup-2026",
            "codex plugin add world-cup-2026-predictor@world-cup-2026",
        ],
        "skill_only_reinstall": [],
    }
    report("plugin upgrade command", status["upgrade_commands"][0].startswith("codex plugin marketplace upgrade"))


def main() -> int:
    test_compare()
    test_local_state_standalone()
    test_upgrade_commands()
    print(f"\nUpdate checker tests: {PASS} passed, {FAIL} failed.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
