#!/usr/bin/env python3
"""Validate the Codex skill product journey and user-facing command coverage."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "world-cup-2026-predictor"
PLAYBOOKS = SKILL / "references" / "user-playbooks.json"


def fail(message: str) -> None:
    raise AssertionError(message)


def load_playbooks() -> dict:
    try:
        payload = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{PLAYBOOKS.relative_to(ROOT)} is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        fail("user-playbooks.json must contain a JSON object")
    return payload


def require_contains(text: str, needle: str, surface: str) -> None:
    if needle not in text:
        fail(f"{surface} is missing required text: {needle!r}")


def validate_playbook_schema(payload: dict) -> None:
    if payload.get("schema_version") != 1:
        fail("user playbooks schema_version must be 1")
    if payload.get("skill_name") != "world-cup-2026-predictor":
        fail("user playbooks skill_name must match the skill")

    journey = payload.get("learning_journey")
    if not isinstance(journey, list) or [item.get("stage") for item in journey] != [
        "install",
        "learn",
        "use",
        "verify",
    ]:
        fail("learning_journey must cover install, learn, use, verify in order")
    for item in journey:
        if not item.get("browser_mode") or not item.get("skill_mode"):
            fail(f"learning_journey stage {item.get('stage')!r} must cover both modes")

    modes = payload.get("modes")
    if not isinstance(modes, list) or len(modes) != 5:
        fail("expected exactly 5 primary skill modes")
    mode_ids = [mode.get("id") for mode in modes]
    expected = {
        "guided_play",
        "one_shot_simulation",
        "live_results",
        "scoring",
        "maintenance",
    }
    if set(mode_ids) != expected:
        fail(f"unexpected primary mode ids: {mode_ids}")
    for mode in modes:
        for key in ("label", "zh_command", "en_command", "plugin_prompt", "primary_surface"):
            if not mode.get(key):
                fail(f"mode {mode.get('id')!r} missing {key}")
        if not mode["zh_command"].startswith("$world-cup-2026-predictor "):
            fail(f"mode {mode['id']} zh_command must start with skill prefix")
        if not mode["en_command"].startswith("$world-cup-2026-predictor "):
            fail(f"mode {mode['id']} en_command must start with skill prefix")

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 20:
        fail("expected exactly 20 simulated user scenarios")
    ids = [item.get("id") for item in scenarios]
    if len(set(ids)) != len(ids):
        fail("scenario ids must be unique")

    counts = Counter()
    for item in scenarios:
        sid = item.get("id")
        mode = item.get("mode")
        counts[mode] += 1
        if mode not in expected:
            fail(f"scenario {sid!r} has unknown mode {mode!r}")
        for key in ("zh_prompt", "en_prompt", "user_goal"):
            if not item.get(key):
                fail(f"scenario {sid!r} missing {key}")
        if not item["zh_prompt"].startswith("$world-cup-2026-predictor "):
            fail(f"scenario {sid!r} zh_prompt must start with skill prefix")
        if not item["en_prompt"].startswith("$world-cup-2026-predictor "):
            fail(f"scenario {sid!r} en_prompt must start with skill prefix")
        for key in ("workflow", "done_evidence", "validation", "safety"):
            value = item.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
                fail(f"scenario {sid!r} must define non-empty string list {key}")
    if any(counts[mode_id] != 4 for mode_id in expected):
        fail(f"expected 4 scenarios per mode, got {dict(counts)}")


def validate_surfaces(payload: dict) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    require_contains(readme, "Browser mode", "README.md")
    require_contains(readme, "Codex Skill mode", "README.md")
    require_contains(readme, "Install -> Learn -> Use", "README.md")
    require_contains(readme, "Useful skill play styles", "README.md")

    prompts = plugin.get("interface", {}).get("defaultPrompt", [])
    if not isinstance(prompts, list):
        fail("plugin defaultPrompt must be a list")

    for mode in payload["modes"]:
        require_contains(readme, mode["zh_command"], "README.md")
        require_contains(readme, mode["en_command"], "README.md")
        if mode["plugin_prompt"] not in prompts:
            fail(f"plugin defaultPrompt missing {mode['plugin_prompt']!r}")
        require_contains(index, mode["zh_command"], "index.html help")

    require_contains(skill_md, "references/user-playbooks.json", "SKILL.md")
    require_contains(skill_md, "scripts/check_updates.py", "SKILL.md")
    require_contains(skill_md, "User Intent Playbooks", "SKILL.md")
    require_contains(openai_yaml, "launch, complete, score", "agents/openai.yaml")
    require_contains(openai_yaml, "freshness-check", "agents/openai.yaml")
    require_contains(index, "skillHelpHTML", "index.html help")
    require_contains(index, "Codex Skill", "index.html help")
    require_contains(readme, "检查这个 skill 是不是最新版本", "README.md")
    require_contains(index, "check whether this skill is up to date", "index.html help")


def main() -> int:
    payload = load_playbooks()
    validate_playbook_schema(payload)
    validate_surfaces(payload)
    print("Skill product UX validation passed.")
    print("- 5 primary modes")
    print("- 20 simulated user scenarios")
    print("- install/learn/use/verify journey covers browser and Codex skill modes")
    print("- README, plugin prompts, SKILL.md, and in-app help expose the commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
