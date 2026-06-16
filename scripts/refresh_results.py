#!/usr/bin/env python3
"""
Idempotent orchestrator for refreshing FIFA World Cup 2026 match results.

Runs the data pipeline in the correct sequence, retries network steps,
shows a before/after diff of newly completed matches, and asserts 4-way
consistency across manifest, match_details, and both HTML embeds.

Usage:
    python3 scripts/refresh_results.py           # Full pipeline
    python3 scripts/refresh_results.py --check   # Consistency assertion only (no network)

Pipeline steps (full mode):
    1. fetch_match_data.py       -> match_schedule.json + manifest.json
    2. fetch_match_details.py    -> match_details.json
    3. fetch_analysis_data.py    -> data/analysis/{match_xg,match_momentum,match_team_stats}.json
    4. build_prediction_data.py  -> data/prediction/prediction_data_v1.json
    5. update_match_data.py      -> index.html (embeds MATCH_DETAILS, MATCH_DATA_META, etc.)
    6. sync_predictor_asset.py   -> skills/.../assets/predictor/index.html

Exit codes:
    0  All data consistent (or --check passed)
    1  Drift detected or pipeline failure

The --check flag validates that these four values are equal:
    manifest.completed_count
    len(match_details.json)
    len(embedded MATCH_DETAILS in index.html)
    len(embedded MATCH_DETAILS in skill copy)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCH_DIR = ROOT / "data" / "matches"
INDEX_HTML = ROOT / "index.html"
SKILL_HTML = (
    ROOT / "skills" / "world-cup-2026-predictor" / "assets" / "predictor" / "index.html"
)
SKILL_SCRIPTS = ROOT / "skills" / "world-cup-2026-predictor" / "scripts"

PIPELINE_STEPS_NETWORK = [
    [sys.executable, str(ROOT / "scripts" / "fetch_match_data.py")],
    [sys.executable, str(ROOT / "scripts" / "fetch_match_details.py")],
    [sys.executable, str(ROOT / "scripts" / "fetch_analysis_data.py")],
]
PIPELINE_STEPS_LOCAL = [
    [sys.executable, str(ROOT / "scripts" / "build_prediction_data.py")],
    [sys.executable, str(ROOT / "scripts" / "update_match_data.py")],
    [sys.executable, str(SKILL_SCRIPTS / "sync_predictor_asset.py")],
]


# ─── JS Variable Extraction ──────────────────────────────────────────


def extract_js_value(source: str, name: str) -> str:
    """Extract the raw text of a JS variable literal from HTML source.

    Uses bracket-depth parsing to correctly handle nested objects/arrays
    and quoted strings containing delimiters.
    """
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


# ─── Counting ────────────────────────────────────────────────────────


def count_manifest() -> int:
    manifest = json.loads((MATCH_DIR / "manifest.json").read_text(encoding="utf-8"))
    return int(manifest["completed_count"])


def completed_schedule_ids() -> set:
    schedule = json.loads((MATCH_DIR / "match_schedule.json").read_text(encoding="utf-8"))
    return {mid for mid, match in schedule.items() if match.get("completed")}


def count_details_file() -> int:
    details = json.loads((MATCH_DIR / "match_details.json").read_text(encoding="utf-8"))
    return len(details)


def details_ids() -> set:
    details = json.loads((MATCH_DIR / "match_details.json").read_text(encoding="utf-8"))
    return set(details.keys())


def count_html_matches(html_path: Path) -> int:
    source = html_path.read_text(encoding="utf-8")
    raw = extract_js_value(source, "MATCH_DETAILS")
    return len(json.loads(raw))


def html_match_ids(html_path: Path) -> set:
    source = html_path.read_text(encoding="utf-8")
    raw = extract_js_value(source, "MATCH_DETAILS")
    return set(json.loads(raw).keys())


def get_all_counts() -> dict:
    """Return completed match counts from all 4 sources plus the ID set."""
    return {
        "manifest": count_manifest(),
        "schedule_ids": completed_schedule_ids(),
        "file": count_details_file(),
        "html": count_html_matches(INDEX_HTML),
        "bundled": count_html_matches(SKILL_HTML),
        "ids": details_ids(),
        "html_ids": html_match_ids(INDEX_HTML),
        "bundled_ids": html_match_ids(SKILL_HTML),
    }


# ─── Pipeline Execution ──────────────────────────────────────────────


def run_step(cmd: list, retries: int = 3) -> None:
    """Run a subprocess with retries. Network steps get 3 attempts."""
    for attempt in range(retries):
        try:
            subprocess.run(cmd, cwd=ROOT, check=True)
            return
        except subprocess.CalledProcessError as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(
                f"  [RETRY {attempt + 1}/{retries}] step failed (exit {exc.returncode}), "
                f"waiting {wait}s...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(wait)


# ─── Consistency Assertion ───────────────────────────────────────────


def assert_consistency() -> tuple:
    """Verify 4-way consistency. Returns (ok, counts_dict)."""
    counts = get_all_counts()
    values = [counts["manifest"], counts["file"], counts["html"], counts["bundled"]]
    expected_ids = counts["schedule_ids"]
    id_sets = [counts["ids"], counts["html_ids"], counts["bundled_ids"]]
    ok = len(set(values)) == 1 and all(ids == expected_ids for ids in id_sets)
    if ok:
        print(f"[OK] Consistency verified: {values[0]} completed matches across all 4 sources")
    else:
        print("[FAIL] Match data drift detected:", file=sys.stderr)
        print(f"  manifest.completed_count = {counts['manifest']}", file=sys.stderr)
        print(f"  match_details.json keys  = {counts['file']}", file=sys.stderr)
        print(f"  index.html MATCH_DETAILS = {counts['html']}", file=sys.stderr)
        print(f"  bundled MATCH_DETAILS    = {counts['bundled']}", file=sys.stderr)
        missing_file = sorted(expected_ids - counts["ids"])
        extra_file = sorted(counts["ids"] - expected_ids)
        missing_html = sorted(expected_ids - counts["html_ids"])
        missing_bundled = sorted(expected_ids - counts["bundled_ids"])
        if missing_file:
            print(f"  missing details for completed schedule ids = {', '.join(missing_file)}", file=sys.stderr)
        if extra_file:
            print(f"  extra detail ids not completed in schedule = {', '.join(extra_file)}", file=sys.stderr)
        if missing_html:
            print(f"  missing index.html MATCH_DETAILS ids = {', '.join(missing_html)}", file=sys.stderr)
        if missing_bundled:
            print(f"  missing bundled MATCH_DETAILS ids = {', '.join(missing_bundled)}", file=sys.stderr)
    return ok, counts


def show_diff(before_ids: set, after_ids: set) -> None:
    """Print newly completed matches."""
    new_ids = sorted(after_ids - before_ids)
    if new_ids:
        print(f"\nNewly completed matches ({len(new_ids)}):")
        details = json.loads((MATCH_DIR / "match_details.json").read_text(encoding="utf-8"))
        for mid in new_ids:
            d = details.get(mid, {})
            home = d.get("homeTeamCn", "?")
            away = d.get("awayTeamCn", "?")
            score = f"{d.get('homeScore', '?')}-{d.get('awayScore', '?')}"
            print(f"  + {mid}  {home} {score} {away}")
    else:
        print("\nNo newly completed matches since last refresh.")


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh FIFA World Cup 2026 match results and assert data consistency."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only assert 4-way consistency (no network, no file writes).",
    )
    args = parser.parse_args()

    if args.check:
        ok, _ = assert_consistency()
        return 0 if ok else 1

    # Full pipeline
    print("=" * 60)
    print("FIFA 2026 Match Results Refresh")
    print("=" * 60)

    # Before snapshot
    try:
        before = get_all_counts()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] Cannot read current state: {exc}", file=sys.stderr)
        return 1
    before_ids = before["ids"]
    print(f"\nBefore: {before['file']} completed matches in data files, "
          f"{before['html']} embedded in HTML")

    # Pipeline steps
    all_steps = (
        [(cmd, 3) for cmd in PIPELINE_STEPS_NETWORK]
        + [(cmd, 1) for cmd in PIPELINE_STEPS_LOCAL]
    )
    for i, (cmd, retries) in enumerate(all_steps, 1):
        script_name = Path(cmd[-1]).name
        print(f"\n--- Step {i}/{len(all_steps)}: {script_name} ---", flush=True)
        try:
            run_step(cmd, retries=retries)
        except subprocess.CalledProcessError as exc:
            print(
                f"\n[FATAL] Step {i} failed: {script_name} (exit {exc.returncode})",
                file=sys.stderr,
            )
            return 1

    # After snapshot + diff
    after = get_all_counts()
    show_diff(before_ids, after["ids"])

    # Hard assertion
    print()
    ok, counts = assert_consistency()

    if ok:
        print(f"\nRefresh complete: {after['file']} completed matches "
              f"(was {before['file']}).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
