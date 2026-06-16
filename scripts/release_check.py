#!/usr/bin/env python3
"""Run repository checks required before publishing a plugin release."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "world-cup-2026-predictor"
PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
REPO_SKILL_LINK = ROOT / ".agents" / "skills" / "world-cup-2026-predictor"
DOMAIN_CATALOG = ROOT / "data" / "schema" / "prediction-domain.v1.json"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return payload


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd or ROOT, check=True)


def optional_system_validator(relative_path: str, target: Path) -> None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    validator = codex_home / "skills" / ".system" / relative_path
    if validator.is_file():
        run([sys.executable, str(validator), str(target)])
    else:
        print(f"[SKIP] Optional Codex validator not found: {validator}")


def extract_js_object(source: str, name: str) -> str:
    """Extract the raw JSON text of a JS variable from HTML source."""
    marker = f"var {name}="
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"missing JavaScript variable: {name}")
    start += len(marker)
    opening = source[start]
    if opening not in "[{":
        raise ValueError(f"{name} is not an object or array literal")
    closing = "}" if opening == "{" else "]"
    depth = 0
    quote = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError(f"unterminated JavaScript value: {name}")


def validate_metadata() -> str:
    plugin = load_json(PLUGIN_MANIFEST)
    required = ("name", "version", "description", "author", "skills", "interface")
    missing = [key for key in required if not plugin.get(key)]
    if missing:
        fail(f"plugin.json is missing required fields: {', '.join(missing)}")
    if plugin["name"] != "world-cup-2026-predictor":
        fail("plugin.json name must remain stable")
    if not isinstance(plugin["version"], str) or not SEMVER.fullmatch(plugin["version"]):
        fail("plugin.json version must be strict semantic versioning")
    if plugin["skills"] != "./skills/":
        fail("plugin.json skills must be ./skills/")

    marketplace = load_json(MARKETPLACE)
    plugins = marketplace.get("plugins")
    if marketplace.get("name") != "world-cup-2026" or not isinstance(plugins, list):
        fail("marketplace.json has an invalid name or plugins list")
    entry = next(
        (item for item in plugins if item.get("name") == plugin["name"]),
        None,
    )
    if not entry:
        fail("marketplace.json does not expose the plugin")
    source = entry.get("source", {})
    if source.get("source") != "url" or source.get("ref") != "main":
        fail("marketplace plugin source must track the main branch")

    if not SKILL.is_dir():
        fail("canonical skills/world-cup-2026-predictor directory is missing")
    if not REPO_SKILL_LINK.is_symlink() or REPO_SKILL_LINK.resolve() != SKILL.resolve():
        fail(".agents skill link must point to the canonical skill directory")

    catalog = load_json(DOMAIN_CATALOG)
    if catalog.get("schema_version") != 1:
        fail("prediction domain catalog schema_version must be 1")
    contexts = catalog.get("contexts")
    if not isinstance(contexts, dict) or not all(
        isinstance(entities, list) and entities for entities in contexts.values()
    ):
        fail("prediction domain catalog contexts must contain entity lists")
    return plugin["version"]


def validate_match_data_consistency() -> None:
    """Verify completed match IDs are identical across all 4 data sources."""
    manifest = load_json(ROOT / "data" / "matches" / "manifest.json")
    schedule = load_json(ROOT / "data" / "matches" / "match_schedule.json")
    details = load_json(ROOT / "data" / "matches" / "match_details.json")

    manifest_count = manifest.get("completed_count", -1)
    details_count = len(details)
    schedule_ids = {mid for mid, match in schedule.items() if match.get("completed")}
    detail_ids = set(details.keys())

    html_source = (ROOT / "index.html").read_text(encoding="utf-8")
    embedded_details = json.loads(extract_js_object(html_source, "MATCH_DETAILS"))
    embedded_count = len(embedded_details)
    embedded_ids = set(embedded_details.keys())

    skill_path = SKILL / "assets" / "predictor" / "index.html"
    if skill_path.is_file():
        skill_source = skill_path.read_text(encoding="utf-8")
        skill_details = json.loads(extract_js_object(skill_source, "MATCH_DETAILS"))
        skill_count = len(skill_details)
        skill_ids = set(skill_details.keys())
    else:
        skill_count = -2
        skill_ids = set()

    if not (
        manifest_count == details_count == embedded_count == skill_count
        and schedule_ids == detail_ids == embedded_ids == skill_ids
    ):
        missing_details = sorted(schedule_ids - detail_ids)
        extra_details = sorted(detail_ids - schedule_ids)
        fail(
            f"match data drift: "
            f"manifest.completed_count={manifest_count}, "
            f"match_details.json={details_count}, "
            f"embedded MATCH_DETAILS={embedded_count}, "
            f"bundled MATCH_DETAILS={skill_count}, "
            f"missing_details={missing_details}, "
            f"extra_details={extra_details}"
        )


def main() -> int:
    try:
        version = validate_metadata()
        run(
            [
                sys.executable,
                str(SKILL / "scripts" / "sync_predictor_asset.py"),
                "--check",
            ]
        )
        run([sys.executable, str(SKILL / "scripts" / "validate_predictor.py")])
        run([sys.executable, str(ROOT / "scripts" / "validate_squads.py")])
        run([sys.executable, str(ROOT / "scripts" / "validate_final.py")])
        run([sys.executable, str(ROOT / "scripts" / "validate_rag_corpus.py")])
        run([sys.executable, str(ROOT / "scripts" / "audit_source_lineage.py")])
        run([sys.executable, str(ROOT / "scripts" / "validate_match_data.py")])
        run([sys.executable, str(ROOT / "scripts" / "validate_prediction_data.py")])
        run([sys.executable, str(ROOT / "scripts" / "test_refresh_results.py")])
        run([sys.executable, str(ROOT / "scripts" / "test_fetch_analysis_data.py")])
        run([sys.executable, str(ROOT / "scripts" / "test_player_position_fallback.py")])
        validate_match_data_consistency()
        if shutil.which("node"):
            tests = sorted(str(path) for path in (ROOT / "test").glob("*.test.mjs"))
            if not tests:
                fail("no Node.js tests found under test/")
            # Node 24+ requires the test runner to scan an explicit dir.
            # Run from the test/ directory so the file pattern is picked up.
            run(["node", "--test"], cwd=ROOT / "test")
        else:
            print("[SKIP] Node.js unavailable; skipped prediction engine tests.")
        optional_system_validator(
            "skill-creator/scripts/quick_validate.py",
            SKILL,
        )
        optional_system_validator(
            "plugin-creator/scripts/validate_plugin.py",
            ROOT,
        )
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"Release checks passed for version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
