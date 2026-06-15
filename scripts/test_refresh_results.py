#!/usr/bin/env python3
"""
TDD test suite for scripts/refresh_results.py and the
validate_match_data_consistency() addition to scripts/release_check.py.

Tests cover:
  1. extract_js_value — bracket-depth parser (core of the consistency check)
  2. assert_consistency — 4-way drift detection
  3. run_step — retry logic
  4. show_diff — new match diff printing
  5. End-to-end --check mode with real data

Run:  python3 scripts/test_refresh_results.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from io import StringIO
from pathlib import Path
from unittest import mock

# ── Import the module under test ────────────────────────────────────
# Add scripts/ to path so we can import refresh_results
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh_results as rr

PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


# ═══════════════════════════════════════════════════════════════════
#  1. extract_js_value
# ═══════════════════════════════════════════════════════════════════


def test_extract_js_value():
    print("\n=== 1. extract_js_value ===")

    # 1.1 Simple object
    src = 'var X={"a":1,"b":2};\nvar Y=999;'
    result = rr.extract_js_value(src, "X")
    report("simple object", result == '{"a":1,"b":2}')

    # 1.2 Nested object
    src = 'var X={"a":{"nested":true},"b":[1,2,3]};'
    result = rr.extract_js_value(src, "X")
    report("nested object", result == '{"a":{"nested":true},"b":[1,2,3]}')

    # 1.3 String containing closing brace
    src = 'var X={"text":"hello } world","val":42};'
    result = rr.extract_js_value(src, "X")
    report("string with brace", result == '{"text":"hello } world","val":42}')

    # 1.4 String containing escaped quote
    src = r'var X={"text":"he said \"hi\"","val":1};'
    result = rr.extract_js_value(src, "X")
    report("escaped quotes", result == '{"text":"he said \\"hi\\"","val":1}')

    # 1.5 Array literal
    src = 'var X=[1,2,{"a":3}];'
    result = rr.extract_js_value(src, "X")
    report("array literal", result == '[1,2,{"a":3}]')

    # 1.6 Multiple variables — picks the right one
    src = 'var A={"x":1};\nvar B={"y":2};\nvar C={"z":3};'
    result = rr.extract_js_value(src, "B")
    report("multiple vars, pick B", result == '{"y":2}')

    # 1.7 Missing variable → ValueError
    try:
        rr.extract_js_value('var A={};', "MISSING")
        report("missing var raises ValueError", False)
    except ValueError as e:
        report("missing var raises ValueError", "missing" in str(e).lower())

    # 1.8 Unterminated value → ValueError
    try:
        rr.extract_js_value('var X={"a":1', "X")
        report("unterminated raises ValueError", False)
    except ValueError as e:
        report("unterminated raises ValueError", "unterminated" in str(e).lower())

    # 1.9 Variable is not an object (e.g. number) → ValueError
    try:
        rr.extract_js_value('var X=42;', "X")
        report("non-object raises ValueError", False)
    except ValueError as e:
        report("non-object raises ValueError", "not an object" in str(e).lower())

    # 1.10 Deeply nested
    src = 'var X={"a":{"b":{"c":{"d":"deep"}}}};'
    result = rr.extract_js_value(src, "X")
    report("4 levels deep", result == '{"a":{"b":{"c":{"d":"deep"}}}}')

    # 1.11 Real-world MATCH_DETAILS shaped data
    real_data = {
        "760415": {"homeTeamCn": "墨西哥", "awayTeamCn": "南非", "homeScore": 2, "awayScore": 0},
        "760414": {"homeTeamCn": "韩国", "awayTeamCn": "捷克", "homeScore": 2, "awayScore": 1},
    }
    minified = json.dumps(real_data, ensure_ascii=False, separators=(",", ":"))
    src = f"var MATCH_DETAILS={minified};\n// === END REAL DATA ==="
    result = rr.extract_js_value(src, "MATCH_DETAILS")
    parsed = json.loads(result)
    report("real-world MATCH_DETAILS", len(parsed) == 2 and "760415" in parsed)

    # 1.12 Match details value with special chars in scorer name
    special = {"760415": {"scorer": "Julián Quiñones", "note": "line1\nline2"}}
    minified = json.dumps(special, ensure_ascii=False, separators=(",", ":"))
    src = f"var TEST={minified};"
    result = rr.extract_js_value(src, "TEST")
    parsed = json.loads(result)
    report("unicode + newline in values", parsed["760415"]["scorer"] == "Julián Quiñones")


# ═══════════════════════════════════════════════════════════════════
#  2. assert_consistency (with temp files)
# ═══════════════════════════════════════════════════════════════════


def _make_temp_data(tmpdir, details_count, manifest_count, html_count, bundled_count):
    """Create temp data files simulating a specific drift state."""
    match_dir = Path(tmpdir) / "data" / "matches"
    match_dir.mkdir(parents=True, exist_ok=True)

    # match_details.json
    details = {f"m{i}": {"homeTeamCn": "A", "awayTeamCn": "B"} for i in range(details_count)}
    (match_dir / "match_details.json").write_text(json.dumps(details), encoding="utf-8")

    # manifest.json
    manifest = {"completed_count": manifest_count, "match_count": 100}
    (match_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Helper to build HTML with MATCH_DETAILS
    def make_html(count):
        d = {f"m{i}": {} for i in range(count)}
        minified = json.dumps(d, separators=(",", ":"))
        return f"<script>var MATCH_DETAILS={minified};\n// === END REAL DATA ===\n</script>"

    index_html = Path(tmpdir) / "index.html"
    index_html.write_text(make_html(html_count), encoding="utf-8")

    skill_dir = Path(tmpdir) / "skills" / "world-cup-2026-predictor" / "assets" / "predictor"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_html = skill_dir / "index.html"
    skill_html.write_text(make_html(bundled_count), encoding="utf-8")

    return match_dir, index_html, skill_html


def test_assert_consistency():
    print("\n=== 2. assert_consistency ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir, index_html, skill_html = _make_temp_data(tmpdir, 12, 12, 12, 12)

        # Patch module-level paths
        with mock.patch.object(rr, "MATCH_DIR", match_dir), \
             mock.patch.object(rr, "INDEX_HTML", index_html), \
             mock.patch.object(rr, "SKILL_HTML", skill_html):

            # 2.1 All consistent
            ok, counts = rr.assert_consistency()
            report("all 4 consistent → ok", ok)
            report("count == 12", counts["manifest"] == 12)

    # 2.2 Manifest drift
    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir, index_html, skill_html = _make_temp_data(tmpdir, 12, 2, 12, 12)
        with mock.patch.object(rr, "MATCH_DIR", match_dir), \
             mock.patch.object(rr, "INDEX_HTML", index_html), \
             mock.patch.object(rr, "SKILL_HTML", skill_html):
            ok, counts = rr.assert_consistency()
            report("manifest drift → not ok", not ok)
            report("manifest=2, file=12", counts["manifest"] == 2 and counts["file"] == 12)

    # 2.3 HTML drift
    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir, index_html, skill_html = _make_temp_data(tmpdir, 12, 12, 2, 12)
        with mock.patch.object(rr, "MATCH_DIR", match_dir), \
             mock.patch.object(rr, "INDEX_HTML", index_html), \
             mock.patch.object(rr, "SKILL_HTML", skill_html):
            ok, counts = rr.assert_consistency()
            report("html drift → not ok", not ok)
            report("html=2 vs rest=12", counts["html"] == 2 and counts["file"] == 12)

    # 2.4 Bundled drift
    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir, index_html, skill_html = _make_temp_data(tmpdir, 12, 12, 12, 2)
        with mock.patch.object(rr, "MATCH_DIR", match_dir), \
             mock.patch.object(rr, "INDEX_HTML", index_html), \
             mock.patch.object(rr, "SKILL_HTML", skill_html):
            ok, counts = rr.assert_consistency()
            report("bundled drift → not ok", not ok)
            report("bundled=2 vs rest=12", counts["bundled"] == 2 and counts["file"] == 12)

    # 2.5 All zero
    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir, index_html, skill_html = _make_temp_data(tmpdir, 0, 0, 0, 0)
        with mock.patch.object(rr, "MATCH_DIR", match_dir), \
             mock.patch.object(rr, "INDEX_HTML", index_html), \
             mock.patch.object(rr, "SKILL_HTML", skill_html):
            ok, counts = rr.assert_consistency()
            report("all zero → ok", ok)


# ═══════════════════════════════════════════════════════════════════
#  3. run_step retry logic
# ═══════════════════════════════════════════════════════════════════


def test_run_step():
    print("\n=== 3. run_step ===")

    # 3.1 Success on first try
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0)
        try:
            rr.run_step(["echo", "hi"], retries=3)
            report("success on first try", mock_run.call_count == 1)
        except Exception:
            report("success on first try", False)

    # 3.2 Fail twice, succeed on third
    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise subprocess.CalledProcessError(1, "cmd")
        return subprocess.CompletedProcess([], 0)

    with mock.patch("subprocess.run", side_effect=side_effect), \
         mock.patch("time.sleep"):  # skip real sleep
        try:
            rr.run_step(["cmd"], retries=3)
            report("retry succeeds on attempt 3", call_count[0] == 3)
        except Exception:
            report("retry succeeds on attempt 3", False)

    # 3.3 All retries exhausted → CalledProcessError
    with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")), \
         mock.patch("time.sleep"):
        try:
            rr.run_step(["cmd"], retries=3)
            report("all retries → raises", False)
        except subprocess.CalledProcessError:
            report("all retries → raises", True)

    # 3.4 retries=1 → no retry, immediate raise
    with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
        try:
            rr.run_step(["cmd"], retries=1)
            report("retries=1 → no retry", False)
        except subprocess.CalledProcessError:
            report("retries=1 → no retry", True)


# ═══════════════════════════════════════════════════════════════════
#  4. show_diff
# ═══════════════════════════════════════════════════════════════════


def test_show_diff():
    print("\n=== 4. show_diff ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "data" / "matches"
        match_dir.mkdir(parents=True, exist_ok=True)

        # Mock MATCH_DIR
        with mock.patch.object(rr, "MATCH_DIR", match_dir):
            # 4.1 New matches
            details = {
                "m1": {"homeTeamCn": "A", "awayTeamCn": "B", "homeScore": 2, "awayScore": 1},
                "m2": {"homeTeamCn": "C", "awayTeamCn": "D", "homeScore": 0, "awayScore": 0},
                "m3": {"homeTeamCn": "E", "awayTeamCn": "F", "homeScore": 3, "awayScore": 2},
            }
            (match_dir / "match_details.json").write_text(json.dumps(details), encoding="utf-8")

            before = {"m1"}
            after = {"m1", "m2", "m3"}

            captured = StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            rr.show_diff(before, after)
            sys.stdout = old_stdout

            output = captured.getvalue()
            report("new matches detected (m2, m3)", "m2" in output and "m3" in output)
            report("score shown", "2-1" in output or "0-0" in output)
            report("team names shown", "A" in output or "C" in output)

            # 4.2 No new matches
            captured2 = StringIO()
            sys.stdout = captured2
            rr.show_diff(after, after)
            sys.stdout = old_stdout
            report("no new matches message", "No newly" in captured2.getvalue())


# ═══════════════════════════════════════════════════════════════════
#  5. End-to-end --check with real data
# ═══════════════════════════════════════════════════════════════════


def test_e2e_check_mode():
    print("\n=== 5. End-to-end --check ===")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "refresh_results.py"), "--check"],
        capture_output=True, text=True
    )
    report("--check exit code == 0", result.returncode == 0)
    report("stdout contains [OK]", "[OK]" in result.stdout)
    report("stderr is empty", result.stderr.strip() == "")


# ═══════════════════════════════════════════════════════════════════
#  6. release_check.py consistency integration
# ═══════════════════════════════════════════════════════════════════


def test_release_check_consistency():
    print("\n=== 6. release_check.py validate_match_data_consistency ===")

    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib
    import release_check as rc
    importlib.reload(rc)  # ensure fresh import

    # 6.1 Current real data should pass (we just fixed the drift)
    try:
        rc.validate_match_data_consistency()
        report("real data consistency passes", True)
    except RuntimeError as e:
        report("real data consistency passes", False, str(e))

    # 6.2 Simulate drift: corrupt manifest count
    original_load_json = rc.load_json
    def mock_load_json_drift_manifest(path):
        data = original_load_json(path)
        if "manifest.json" in str(path):
            data["completed_count"] = 999  # inject drift
        return data

    with mock.patch.object(rc, "load_json", side_effect=mock_load_json_drift_manifest):
        try:
            rc.validate_match_data_consistency()
            report("drift detection → raises RuntimeError", False)
        except RuntimeError as e:
            report("drift detection → raises RuntimeError", "drift" in str(e).lower())
            report("error message includes counts", "999" in str(e))


# ═══════════════════════════════════════════════════════════════════
#  7. Cross-module consistency: refresh_results and release_check use
#    same extraction logic
# ═══════════════════════════════════════════════════════════════════


def test_cross_module_consistency():
    print("\n=== 7. Cross-module extraction parity ===")

    import importlib
    import release_check as rc
    importlib.reload(rc)

    test_cases = [
        ('var X={"a":1};', "X", '{"a":1}'),
        ('var X=[1,2,3];', "X", '[1,2,3]'),
        ('var X={"a":{"b":"c"},"d":"e}f"};', "X", '{"a":{"b":"c"},"d":"e}f"}'),
    ]

    for src, name, expected in test_cases:
        r1 = rr.extract_js_value(src, name)
        r2 = rc.extract_js_object(src, name)
        match = (r1 == r2 == expected)
        report(f"parity: {expected[:30]}...", match)


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print("=" * 60)
    print("TDD Tests: refresh_results.py + release_check.py consistency")
    print("=" * 60)

    test_extract_js_value()
    test_assert_consistency()
    test_run_step()
    test_show_diff()
    test_e2e_check_mode()
    test_release_check_consistency()
    test_cross_module_consistency()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)

    raise SystemExit(0 if FAIL == 0 else 1)
