#!/usr/bin/env python3
"""Full-system experience checks for the World Cup 2026 predictor.

This is intentionally a product-level script, not just another unit test. It
validates the skill journey, command playbooks, local browser flows, share-state
read-only behavior, and optionally the public deployment.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "world-cup-2026-predictor"
PLAYBOOKS = SKILL / "references" / "user-playbooks.json"
INDEX = ROOT / "index.html"
BUNDLED_INDEX = SKILL / "assets" / "predictor" / "index.html"

SYSTEM_BROWSER_CANDIDATES = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
]

COVERAGE_CONTRACT = [
    {
        "area": "skill_install_learn_use_verify",
        "requirements": [
            "learning_journey covers install, learn, use, and verify in order",
            "README, SKILL.md, plugin prompts, and in-app help expose runnable commands",
            "20 user scenarios keep the skill more than a static web wrapper",
        ],
        "evidence": [
            "skills/world-cup-2026-predictor/references/user-playbooks.json",
            "scripts/test_skill_product_ux.py",
            "skills/world-cup-2026-predictor/SKILL.md",
        ],
    },
    {
        "area": "skill_live_and_maintenance_commands",
        "requirements": [
            "ESPN/live-result commands are represented by script contracts and fixture tests",
            "freshness/update checks stay explicit instead of silently mutating installs",
            "canonical app and bundled skill asset are checked for drift",
        ],
        "evidence": [
            "scripts/test_espn_source_contract.py",
            "scripts/test_check_updates.py",
            "skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py --check",
        ],
    },
    {
        "area": "browser_guided_prediction",
        "requirements": [
            "the local web app can complete group stage and knockout predictions",
            "a champion, third place, scorers page, and share URL are produced",
            "the test exercises the real browser surface, not only pure functions",
        ],
        "evidence": [
            "Playwright browser run against scripts/serve_local.mjs",
            "window.raG(), window.raKO(), and getSharePredictionUrl() runtime state",
        ],
    },
    {
        "area": "browser_mode_matrix",
        "requirements": [
            "normal, clone, and chaos gameplay modes are exercised",
            "random, strength, and ensemble prediction modes are exercised where compatible",
            "the product playbooks expose five primary modes with four scenarios each",
        ],
        "evidence": [
            "browser mode matrix in run_browser_experience()",
            "build_mode_matrix(user-playbooks.json)",
            "scripts/test_full_system_experience.py",
        ],
    },
    {
        "area": "share_and_readonly_state",
        "requirements": [
            "generated share links restore the completed bracket in a fresh page",
            "shared views enter read-only mode and preserve winner data",
            "share-state schema markers remain present in the canonical HTML",
        ],
        "evidence": [
            "fresh browser page opened from getSharePredictionUrl()",
            "body.view-mode and disabled form controls",
            "SHARE_STATE_VERSION marker in index.html",
        ],
    },
    {
        "area": "public_deployment",
        "requirements": [
            "when a public URL is supplied, the fetched route must match local canonical HTML",
            "the public HTML must expose core simulation, data, skill-help, and share markers",
            "deployment proof is HTTP/content based instead of only CLI success text",
        ],
        "evidence": [
            "urllib fetch of --public-url",
            "SHA-256 comparison with index.html",
            "required public marker checks",
        ],
    },
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fail(message: str) -> None:
    raise RuntimeError(message)


def ok(message: str) -> None:
    print(f"[OK] {message}", flush=True)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{relative(path)} is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        fail(f"{relative(path)} must contain a JSON object")
    return payload


def build_mode_matrix(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    modes = payload.get("modes")
    scenarios = payload.get("scenarios")
    if not isinstance(modes, list) or not isinstance(scenarios, list):
        fail("user-playbooks.json must contain modes and scenarios lists")

    matrix: Dict[str, Dict[str, Any]] = {}
    for mode in modes:
        if not isinstance(mode, dict) or not mode.get("id"):
            fail("every playbook mode must be an object with an id")
        mode_id = str(mode["id"])
        matrix[mode_id] = {
            "label": mode.get("label"),
            "primary_surface": mode.get("primary_surface"),
            "scenario_count": 0,
            "commands": [mode.get("zh_command"), mode.get("en_command")],
        }

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            fail("every scenario must be an object")
        mode_id = scenario.get("mode")
        if mode_id not in matrix:
            fail(f"scenario {scenario.get('id')!r} references unknown mode {mode_id!r}")
        matrix[str(mode_id)]["scenario_count"] += 1
    return matrix


def resolve_browser_executable(browser: Optional[str]) -> Optional[Path]:
    if browser:
        path = Path(browser).expanduser()
        if not path.is_file():
            fail(f"--browser does not exist: {path}")
        return path
    for path in SYSTEM_BROWSER_CANDIDATES:
        if path.is_file():
            return path
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate skill, browser, share, and optional public deployment experience."
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Skip Playwright browser automation; static and command checks still run.",
    )
    parser.add_argument(
        "--public-url",
        default="",
        help="Optional public route to verify against local index.html, e.g. https://www.cameraclaw.cn/2026.",
    )
    parser.add_argument(
        "--browser",
        default="",
        help="Optional browser executable path. Defaults to system Chrome/Chromium/Edge when available.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Local preview host.")
    parser.add_argument("--port", type=int, default=0, help="Local preview port, or 0 for an open port.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds to wait for browser/server steps.")
    return parser


def run_command(label: str, command: List[str], timeout: float = 120.0, cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in (exc.stdout, exc.stderr) if part)
        fail(f"{label} failed with exit {exc.returncode}\n{output[-4000:]}")
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            part.decode("utf-8", "replace") if isinstance(part, bytes) else part
            for part in (exc.stdout, exc.stderr)
            if part
        )
        fail(f"{label} timed out after {timeout}s\n{output[-4000:]}")
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    if output:
        print(output[-3000:], flush=True)
    ok(label)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_valid_share_url(url: Any) -> bool:
    return isinstance(url, str) and ("#s=" in url or "#p=" in url)


def validate_coverage_contract() -> None:
    expected = {
        "skill_install_learn_use_verify",
        "skill_live_and_maintenance_commands",
        "browser_guided_prediction",
        "browser_mode_matrix",
        "share_and_readonly_state",
        "public_deployment",
    }
    actual = {item.get("area") for item in COVERAGE_CONTRACT}
    if actual != expected:
        fail(f"coverage contract areas drifted: {sorted(actual)}")
    for item in COVERAGE_CONTRACT:
        requirements = item.get("requirements")
        evidence = item.get("evidence")
        if not isinstance(requirements, list) or len(requirements) < 2:
            fail(f"{item.get('area')} must name at least two requirements")
        if not isinstance(evidence, list) or len(evidence) < 2:
            fail(f"{item.get('area')} must name at least two evidence surfaces")
    ok("coverage contract names all full-system areas")


def validate_playbooks() -> None:
    payload = load_json(PLAYBOOKS)
    journey = payload.get("learning_journey")
    if not isinstance(journey, list):
        fail("learning_journey must be a list")
    stages = [item.get("stage") for item in journey if isinstance(item, dict)]
    if stages != ["install", "learn", "use", "verify"]:
        fail(f"learning_journey must be install/learn/use/verify, got {stages}")

    matrix = build_mode_matrix(payload)
    if set(matrix) != {
        "guided_play",
        "one_shot_simulation",
        "live_results",
        "scoring",
        "maintenance",
    }:
        fail(f"unexpected mode matrix: {sorted(matrix)}")
    for mode_id, entry in sorted(matrix.items()):
        if entry["scenario_count"] < 4:
            fail(f"{mode_id} must have at least 4 scenarios")
        if entry["primary_surface"] not in {"browser_app", "codex_skill", "hybrid"}:
            fail(f"{mode_id} has invalid primary surface: {entry['primary_surface']!r}")
    ok("playbook journey and 5x4 mode matrix are complete")


def validate_static_html_contracts() -> None:
    if not INDEX.is_file():
        fail("index.html is missing")
    if not BUNDLED_INDEX.is_file():
        fail("bundled predictor index is missing")

    local_hash = sha256_file(INDEX)
    bundled_hash = sha256_file(BUNDLED_INDEX)
    if local_hash != bundled_hash:
        fail(
            "canonical index.html and bundled skill asset differ; run "
            "skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py"
        )

    html = INDEX.read_text(encoding="utf-8")
    markers = [
        "skillHelpHTML",
        "Codex Skill",
        "var SHARE_STATE_VERSION=3",
        "function getSharePredictionUrl",
        "function applyViewModeLockdown",
        "function setPlayMode",
        "function raG",
        "function raKO",
        "function simulateKnockoutMatch",
        "function isScoringEvent",
        "function pushAutoGoalFromEvent",
        "function autoScoreKO",
        "var MATCH_DETAILS=",
        "var COMPLETE_ODDS=",
        "var PLAYER_THREATS_MAP=",
        "var PHOTO_MAP=",
    ]
    missing = [marker for marker in markers if marker not in html]
    if missing:
        fail(f"index.html missing full-system markers: {missing}")
    ok("canonical and bundled HTML are synced and expose core runtime markers")


def validate_command_contracts() -> None:
    run_command("skill product UX test", [sys.executable, str(ROOT / "scripts" / "test_skill_product_ux.py")])
    run_command(
        "ESPN source fixture contract",
        [sys.executable, str(ROOT / "scripts" / "test_espn_source_contract.py")],
    )
    run_command(
        "skill update checker contract",
        [sys.executable, str(ROOT / "scripts" / "test_check_updates.py")],
    )
    run_command(
        "predictor validator",
        [sys.executable, str(SKILL / "scripts" / "validate_predictor.py")],
    )
    run_command(
        "bundled asset sync check",
        [sys.executable, str(SKILL / "scripts" / "sync_predictor_asset.py"), "--check"],
    )


def find_open_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_http(url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last_error: Optional[BaseException] = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(0.2)
    fail(f"local preview did not become ready at {url}: {last_error}")


@contextlib.contextmanager
def local_preview(host: str, port: int, timeout: float) -> Iterator[str]:
    actual_port = port or find_open_port(host)
    url = f"http://{host}:{actual_port}/"
    command = ["node", str(ROOT / "scripts" / "serve_local.mjs"), "--host", host, "--port", str(actual_port)]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_http(url, timeout)
        ok(f"local preview ready at {url}")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()


def has_visible_label(values: Any, expected: str) -> bool:
    if not isinstance(values, list):
        return False
    return any(isinstance(value, str) and value.strip().startswith(expected) for value in values)


def assert_browser_result(payload: Dict[str, Any]) -> None:
    landing = payload.get("landing")
    if not isinstance(landing, dict):
        fail("browser did not return landing summary")
    tabs = landing.get("tabs")
    modes = landing.get("modes")
    if not all(has_visible_label(tabs, label) for label in ("小组赛", "淘汰赛", "数据榜")):
        fail(f"browser tabs are incomplete: {tabs}")
    if not isinstance(modes, list) or not {"标准模式", "娱乐模式", "爆冷模式"}.issubset(set(modes)):
        fail(f"browser play modes are incomplete: {modes}")

    mode_runs = payload.get("modeRuns")
    if not isinstance(mode_runs, list) or len(mode_runs) < 5:
        fail(f"expected at least five browser mode runs, got {mode_runs}")
    for run in mode_runs:
        if not run.get("groupDone"):
            fail(f"browser run did not finish groups: {run}")
        if not run.get("champion"):
            fail(f"browser run did not produce champion: {run}")
        if not run.get("third"):
            fail(f"browser run did not produce third place: {run}")
        if int(run.get("koCount") or 0) < 32:
            fail(f"browser run did not populate knockout bracket: {run}")
        if not is_valid_share_url(run.get("shareUrl")):
            fail(f"browser run did not create share URL: {run}")

    share = payload.get("share")
    if not isinstance(share, dict) or not share.get("isViewMode"):
        fail(f"shared page did not enter read-only view mode: {share}")
    if not share.get("champion"):
        fail(f"shared page did not restore champion: {share}")
    if int(share.get("enabledFormControls") or 0) != 0:
        fail(f"shared page still has enabled controls: {share}")
    ok("browser completed mode matrix and read-only share flow")


def run_browser_experience(args: argparse.Namespace) -> None:
    if args.skip_browser:
        print("[SKIP] Browser automation skipped by --skip-browser.", flush=True)
        return

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        fail(f"Python Playwright is required for browser checks: {exc}")

    browser_executable = resolve_browser_executable(args.browser or None)
    if browser_executable:
        ok(f"using browser executable {browser_executable}")
    else:
        print("[INFO] No system browser path found; trying Playwright's bundled Chromium.", flush=True)

    with local_preview(args.host, args.port, args.timeout) as url:
        with sync_playwright() as playwright:
            launch_args: Dict[str, Any] = {"headless": True}
            if browser_executable:
                launch_args["executable_path"] = str(browser_executable)
            try:
                browser = playwright.chromium.launch(**launch_args)
            except Exception as exc:
                fail(f"could not launch Chromium/Chrome for browser checks: {exc}")

            console_errors: List[str] = []
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 960})
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: console_errors.append(str(exc)))
                page.goto(url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                page.wait_for_selector("#tabs .tabs-inner", timeout=int(args.timeout * 1000))

                payload = page.evaluate(
                    """
async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const landing = {
    title: document.title,
    tabs: Array.from(document.querySelectorAll("#tabs button")).map((button) => button.textContent.trim()),
    modes: Array.from(document.querySelectorAll(".play-mode button")).map((button) => button.textContent.trim()),
    hasSkillHelp: document.body.innerText.includes("Codex Skill")
  };
  if (!landing.hasSkillHelp) {
    throw new Error("in-app skill help text is missing");
  }
  const combos = [
    {playModeValue: "normal", predictionValue: "strength"},
    {playModeValue: "normal", predictionValue: "ensemble"},
    {playModeValue: "clone", predictionValue: "random"},
    {playModeValue: "clone", predictionValue: "strength"},
    {playModeValue: "chaos", predictionValue: "random"}
  ];
  const modeRuns = [];
  for (const combo of combos) {
    clearState();
    setPlayMode(combo.playModeValue);
    setPredictionMode(combo.predictionValue);
    raG();
    tab = "knockout";
    render();
    raKO();
    tab = "scorers";
    render();
    modeRuns.push({
      requestedPlayMode: combo.playModeValue,
      requestedPredictionMode: combo.predictionValue,
      playMode,
      predictionMode,
      groupDone: allDone(),
      champion: getKOResult("FINAL") && getKOResult("FINAL").w ? getKOResult("FINAL").w : "",
      third: getKOResult("3RD") && getKOResult("3RD").w ? getKOResult("3RD").w : "",
      koCount: KO_SHARE_IDS.filter((id) => Boolean(getKOResult(id))).length,
      scoreRows: document.querySelectorAll("tbody tr").length,
      shareUrl: getSharePredictionUrl()
    });
    await sleep(0);
  }
  return {
    landing,
    modeRuns,
    finalShareUrl: modeRuns[modeRuns.length - 1].shareUrl
  };
}
                    """
                )
                share_url = payload.get("finalShareUrl")
                if not is_valid_share_url(share_url):
                    fail(f"browser did not create a valid final share URL: {share_url!r}")

                view = browser.new_page(viewport={"width": 1280, "height": 900})
                view.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                view.on("pageerror", lambda exc: console_errors.append(str(exc)))
                view.goto(share_url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                view.wait_for_function("document.body.classList.contains('view-mode')", timeout=int(args.timeout * 1000))
                payload["share"] = view.evaluate(
                    """
() => {
  const hash = window.location.hash;
  const decoded = hash.startsWith("#p=") ? shareDecodeJson(hash.slice(3)) : null;
  return ({
  isViewMode: window.isViewMode === true,
  champion: getKOResult("FINAL") && getKOResult("FINAL").w ? getKOResult("FINAL").w : "",
  koKeys: Object.keys(window.ko || {}),
  finalRaw: window.ko && window.ko.FINAL ? window.ko.FINAL : null,
  hashPrefix: hash.slice(0, 3),
  decodedKoKeys: decoded && decoded.k ? Object.keys(decoded.k) : [],
  decodedFinal: decoded && decoded.k ? decoded.k.FINAL : null,
  decodedFinalTeams: decoded && decoded.k && decoded.k.FINAL
    ? [Object.keys(PL)[decoded.k.FINAL[0]], Object.keys(PL)[decoded.k.FINAL[1]]]
    : [],
  enabledFormControls: Array.from(document.querySelectorAll("input, button, select, textarea"))
    .filter((control) => !control.disabled && control.getAttribute("aria-disabled") !== "true")
    .filter((control) => {
      const onclick = control.getAttribute("onclick") || "";
      if (/cM\\(\\)|toggleLang|toggleTheme|toggleMusic|skipSong|exitViewMode|tab=|scrollTo/.test(onclick)) return false;
      if (control.closest(".view-mode-banner,#tabs,.tabs,.tabs-inner,.lang,.top-actions")) return false;
      return true;
    })
    .length,
  hasViewCopy: document.body.innerText.includes("分享") || document.body.innerText.includes("read-only")
})}
                    """
                )
                assert_browser_result(payload)
            except RuntimeError:
                raise
            except Exception as exc:
                fail(f"browser automation failed: {exc}")
            finally:
                browser.close()

    if console_errors:
        fail("browser console/page errors were reported:\n" + "\n".join(console_errors[-20:]))


def fetch_public_html(public_url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        public_url,
        headers={"User-Agent": "codex-full-system-experience-test/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                fail(f"{public_url} returned HTTP {response.status}")
            return response.read()
    except urllib.error.URLError as exc:
        fail(f"could not fetch public URL {public_url}: {exc}")


def validate_public_deployment(public_url: str, timeout: float) -> None:
    if not public_url:
        print("[SKIP] No --public-url supplied; skipped public deployment proof.", flush=True)
        return

    remote_bytes = fetch_public_html(public_url, timeout)
    local_bytes = INDEX.read_bytes()
    remote_hash = sha256_bytes(remote_bytes)
    local_hash = sha256_bytes(local_bytes)
    if remote_hash != local_hash:
        fail(
            f"public URL does not match local canonical index.html: "
            f"public={remote_hash} local={local_hash}"
        )

    html = remote_bytes.decode("utf-8", "replace")
    markers = [
        "var SHARE_STATE_VERSION=3",
        "function simulateKnockoutMatch",
        "function koDecisionText",
        "skillHelpHTML",
        "var MATCH_DETAILS=",
        "var PHOTO_MAP=",
    ]
    missing = [marker for marker in markers if marker not in html]
    if missing:
        fail(f"public URL missing deployment markers: {missing}")
    ok(f"public deployment matches local index.html at {public_url}")


def main() -> int:
    args = build_parser().parse_args()
    try:
        validate_coverage_contract()
        validate_playbooks()
        validate_static_html_contracts()
        validate_command_contracts()
        run_browser_experience(args)
        validate_public_deployment(args.public_url, args.timeout)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print("Full-system experience validation passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
