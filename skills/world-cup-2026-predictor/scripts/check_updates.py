#!/usr/bin/env python3
"""Check whether the installed predictor skill is aligned with remote main."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION.json"
DEFAULT_REPO = "https://github.com/jiaqi015/WorldCup2026-Predictor-Skill.git"
DEFAULT_REF = "main"
RAW_PLUGIN_JSON = (
    "https://raw.githubusercontent.com/jiaqi015/"
    "WorldCup2026-Predictor-Skill/main/.codex-plugin/plugin.json"
)


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def find_repo_root(skill_root: Path = SKILL_ROOT) -> Path | None:
    for candidate in [skill_root, *skill_root.parents]:
        if (candidate / ".git").exists() and (candidate / ".codex-plugin" / "plugin.json").is_file():
            return candidate
    return None


def git_output(args: list[str], cwd: Path, timeout: float = 10) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    return result.stdout.strip()


def local_state(skill_root: Path = SKILL_ROOT) -> dict:
    repo_root = find_repo_root(skill_root)
    version_meta = load_json(skill_root / "VERSION.json")
    plugin = load_json(repo_root / ".codex-plugin" / "plugin.json") if repo_root else {}
    repo_url = (
        (git_output(["config", "--get", "remote.origin.url"], repo_root) if repo_root else None)
        or version_meta.get("repository")
        or DEFAULT_REPO
    )
    ref = version_meta.get("ref") or DEFAULT_REF
    commit = git_output(["rev-parse", "HEAD"], repo_root) if repo_root else None
    dirty = bool(git_output(["status", "--porcelain"], repo_root)) if repo_root else None
    return {
        "source": "git_worktree" if repo_root else "installed_skill",
        "repo_root": str(repo_root) if repo_root else None,
        "version": plugin.get("version") or version_meta.get("version"),
        "commit": commit,
        "has_local_changes": dirty,
        "repository": repo_url,
        "ref": ref,
        "plugin_marketplace": version_meta.get("plugin_marketplace", "world-cup-2026"),
        "plugin_name": version_meta.get("plugin_name", "world-cup-2026-predictor"),
        "skill_path": version_meta.get("skill_path", "skills/world-cup-2026-predictor"),
    }


def remote_commit(repo_url: str, ref: str, timeout: float = 15) -> str | None:
    result = git_output(["ls-remote", repo_url, f"refs/heads/{ref}"], Path.cwd(), timeout)
    if not result:
        return None
    first = result.split()[0]
    return first if first else None


def fetch_remote_version(timeout: float = 15, url: str = RAW_PLUGIN_JSON) -> str | None:
    try:
        request = Request(url, headers={"User-Agent": "world-cup-2026-predictor-skill/1.1"})
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    return payload.get("version") if isinstance(payload, dict) else None


def compare(local: dict, remote: dict) -> str:
    if not remote.get("commit") and not remote.get("version"):
        return "unknown"
    if local.get("commit") and remote.get("commit"):
        if local["commit"] != remote["commit"]:
            return "update_available"
        if local.get("has_local_changes"):
            return "local_changes"
        return "up_to_date"
    if local.get("version") and remote.get("version"):
        return "up_to_date" if local["version"] == remote["version"] else "update_available"
    return "unknown"


def build_status(timeout: float = 15) -> dict:
    local = local_state()
    remote = {
        "ref": local["ref"],
        "commit": remote_commit(local["repository"], local["ref"], timeout),
        "version": fetch_remote_version(timeout),
    }
    status = compare(local, remote)
    return {
        "status": status,
        "local": local,
        "remote": remote,
        "upgrade_commands": [
            f"codex plugin marketplace upgrade {local['plugin_marketplace']}",
            f"codex plugin add {local['plugin_name']}@{local['plugin_marketplace']}",
        ],
        "skill_only_reinstall": [
            f"rm -rf \"${{CODEX_HOME:-$HOME/.codex}}/skills/{local['plugin_name']}\"",
            "python3 \"${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py\" "
            f"--repo jiaqi015/WorldCup2026-Predictor-Skill --path {local['skill_path']}",
        ],
    }


def print_text(status: dict) -> None:
    local = status["local"]
    remote = status["remote"]
    print("World Cup 2026 Predictor skill update status")
    print(f"- status: {status['status']}")
    print(f"- local version: {local.get('version') or 'unknown'}")
    print(f"- local commit: {(local.get('commit') or 'unknown')[:12]}")
    print(f"- local source: {local.get('source')}")
    print(f"- local changes: {local.get('has_local_changes')}")
    print(f"- remote ref: {remote.get('ref')}")
    print(f"- remote version: {remote.get('version') or 'unknown'}")
    print(f"- remote commit: {(remote.get('commit') or 'unknown')[:12]}")
    print("Upgrade as plugin:")
    for command in status["upgrade_commands"]:
        print(f"  {command}")
    print("Skill-only reinstall:")
    for command in status["skill_only_reinstall"]:
        print(f"  {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    status = build_status(args.timeout)
    if args.as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print_text(status)
    return 0 if status["status"] in {"up_to_date", "local_changes"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
