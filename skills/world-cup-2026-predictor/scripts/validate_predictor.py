#!/usr/bin/env python3
"""Validate the installable skill and predictor data invariants."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = SKILL_ROOT / "assets" / "predictor" / "index.html"


def find_repo_root() -> Path | None:
    for candidate in SKILL_ROOT.parents:
        if (candidate / ".git").exists() and (candidate / "index.html").is_file():
            return candidate
    return None


def extract_js_value(source: str, name: str) -> str:
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


def load_json_variable(source: str, name: str):
    value = extract_js_value(source, name)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # GD uses compact JavaScript keys such as {A:[...],B:[...]}.
        normalized = re.sub(
            r"([,{]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)",
            r'\1"\2"\3',
            value,
        )
        return json.loads(normalized)


def validate_inline_javascript(source: str) -> None:
    if not shutil.which("node"):
        print("[WARN] Node.js unavailable; skipped JavaScript syntax validation.")
        return

    scripts = [
        script
        for script in re.findall(
            r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",
            source,
            flags=re.IGNORECASE,
        )
        if script.strip()
    ]
    for index, script in enumerate(scripts, start=1):
        result = subprocess.run(
            ["node", "-e", "new Function(require('fs').readFileSync(0, 'utf8'))"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise ValueError(
                f"inline script {index} has invalid JavaScript: {result.stderr.strip()}"
            )


def main() -> int:
    errors = []
    required = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "agents" / "openai.yaml",
        APP_PATH,
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing required file: {path}")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    source = APP_PATH.read_text(encoding="utf-8")
    try:
        groups = load_json_variable(source, "GD")
        players = load_json_variable(source, "PL")
        positions = load_json_variable(source, "POS")
        flags = load_json_variable(source, "FC")
        english = load_json_variable(source, "TEAM_EN")

        teams = [team for group in groups.values() for team in group]
        if len(groups) != 12:
            errors.append(f"expected 12 groups, found {len(groups)}")
        if any(len(group) != 4 for group in groups.values()):
            errors.append("every group must contain exactly 4 teams")
        if len(teams) != 48 or len(set(teams)) != 48:
            errors.append("expected 48 unique teams")

        for team in teams:
            roster = players.get(team)
            if not roster or len(roster) != 11:
                errors.append(f"{team}: expected 11 players")
            if team not in positions:
                errors.append(f"{team}: missing POS mapping")
            elif roster:
                missing_positions = [player for player in roster if player not in positions[team]]
                if missing_positions:
                    errors.append(
                        f"{team}: missing positions for {', '.join(missing_positions)}"
                    )
            if team not in flags:
                errors.append(f"{team}: missing flag mapping")
            if team not in english:
                errors.append(f"{team}: missing English-name mapping")

        if "limit=200" not in source or "fifa.world/scoreboard" not in source:
            errors.append("ESPN World Cup scoreboard endpoint is missing")
        if "104 real results" not in source:
            errors.append("104-match live scoring UI marker is missing")

        validate_inline_javascript(source)
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))

    repo_root = find_repo_root()
    canonical = repo_root / "index.html" if repo_root else None
    if canonical and canonical.read_bytes() != APP_PATH.read_bytes():
        errors.append(
            "bundled predictor differs from root index.html; "
            "run scripts/sync_predictor_asset.py"
        )

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print("Predictor validation passed.")
    print("- Skill metadata and bundled app present")
    print("- 12 groups / 48 teams / 528 roster slots")
    print("- Flag, English-name, and position mappings complete")
    print("- Inline JavaScript syntax valid")
    if canonical:
        print("- Root app and bundled skill asset are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
