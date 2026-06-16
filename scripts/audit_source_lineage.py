#!/usr/bin/env python3
"""Audit source lineage across data files, app embeds, and skill assets."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
SKILL_HTML = (
    ROOT / "skills" / "world-cup-2026-predictor" / "assets" / "predictor" / "index.html"
)
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from update_index import TEAM_CN_MAP, get_player_cn_name  # noqa: E402

EMBEDDED_JSON_SOURCES = {
    "FIFA_RANKINGS": ROOT / "data" / "rankings" / "fifa_rankings.json",
    "MATCH_SCHEDULE": ROOT / "data" / "matches" / "match_schedule.json",
    "MATCH_DETAILS": ROOT / "data" / "matches" / "match_details.json",
    "MATCH_DATA_META": ROOT / "data" / "matches" / "manifest.json",
    "TEAM_STRENGTH_TIERS": ROOT / "data" / "rankings" / "team_strength_tiers.json",
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_js_value(source: str, name: str):
    marker = f"var {name}="
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"missing JavaScript variable: {name}")
    start += len(marker)
    opening = source[start]
    if opening not in "[{":
        raise ValueError(f"{name} is not a JSON object or array literal")
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
                return json.loads(source[start : index + 1])
    raise ValueError(f"unterminated JavaScript variable: {name}")


def assert_embeds_match_files(errors: list[str]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    skill_html = SKILL_HTML.read_text(encoding="utf-8")
    if html != skill_html:
        fail("skill predictor asset is not synced with root index.html", errors)

    for name, path in EMBEDDED_JSON_SOURCES.items():
        expected = load_json(path)
        try:
            actual = extract_js_value(html, name)
        except (ValueError, json.JSONDecodeError) as exc:
            fail(f"{name}: cannot parse embedded value: {exc}", errors)
            continue
        if actual != expected:
            fail(f"{name}: embedded value differs from {path.relative_to(ROOT)}", errors)

    prediction = load_json(ROOT / "data" / "prediction" / "prediction_data_v1.json")
    expected_odds = {}
    for match in prediction.get("matches", []):
        odds = match.get("odds")
        if odds and odds.get("home_decimal"):
            expected_odds[match["match_id"]] = {
                "h": odds["home_decimal"],
                "d": odds["draw_decimal"],
                "a": odds["away_decimal"],
                "m": odds.get("method", "unknown"),
                "c": match.get("confidence", "low"),
            }
    try:
        embedded_odds = extract_js_value(html, "COMPLETE_ODDS")
    except (ValueError, json.JSONDecodeError) as exc:
        fail(f"COMPLETE_ODDS: cannot parse embedded value: {exc}", errors)
    else:
        if embedded_odds != expected_odds:
            fail("COMPLETE_ODDS: embedded compact odds differ from prediction_data_v1.json", errors)

    expected_photos = expected_photo_map()
    for source_name, source in (("index.html", html), ("skill asset", skill_html)):
        try:
            embedded_photos = extract_js_value(source, "PHOTO_MAP")
        except (ValueError, json.JSONDecodeError) as exc:
            fail(f"PHOTO_MAP: cannot parse embedded value in {source_name}: {exc}", errors)
            continue
        if embedded_photos != expected_photos:
            fail(
                f"PHOTO_MAP: embedded value in {source_name} differs from "
                "data/squads/photo_mapping.json",
                errors,
            )


def expected_photo_map() -> dict[str, str]:
    squads = load_json(ROOT / "data" / "squads" / "squads_partial.json")
    mapping = load_json(ROOT / "data" / "squads" / "player_mapping.json")
    source_photos = load_json(ROOT / "data" / "squads" / "photo_mapping.json")
    display_photos: dict[str, str] = {}

    for team_en, team_data in squads.items():
        team_cn = TEAM_CN_MAP.get(team_en, team_en)
        for player in team_data.get("players", []):
            en_name = player["name"]
            cn_name = get_player_cn_name(en_name, mapping, team_en)
            photo = source_photos.get(f"{en_name} ({team_en})") or source_photos.get(en_name)
            if not photo:
                continue
            path = photo["path"]
            display_photos[f"{team_cn}|{cn_name}"] = path
            display_photos[cn_name] = path
    return display_photos


def assert_match_lineage(errors: list[str]) -> None:
    manifest = load_json(ROOT / "data" / "matches" / "manifest.json")
    schedule = load_json(ROOT / "data" / "matches" / "match_schedule.json")
    details = load_json(ROOT / "data" / "matches" / "match_details.json")

    schedule_completed = {mid for mid, match in schedule.items() if match.get("completed")}
    detail_ids = set(details)
    if manifest.get("match_count") != len(schedule):
        fail("match manifest count differs from schedule length", errors)
    if manifest.get("completed_count") != len(schedule_completed):
        fail("match manifest completed_count differs from completed schedule IDs", errors)
    if detail_ids != schedule_completed:
        fail(
            "match_details IDs differ from completed schedule IDs "
            f"(missing={sorted(schedule_completed - detail_ids)}, "
            f"extra={sorted(detail_ids - schedule_completed)})",
            errors,
        )

    allowed_goal_status = {"complete", "partial", "extra"}
    for mid, match in details.items():
        expected_goals = int(match.get("homeScore", 0)) + int(match.get("awayScore", 0))
        goal_events = [event for event in match.get("events", []) if event.get("type") == "goal"]
        if match.get("expectedGoalCount") != expected_goals:
            fail(f"{mid}: expectedGoalCount does not match scoreline", errors)
        if match.get("goalEventCount") != len(goal_events):
            fail(f"{mid}: goalEventCount does not match goal event list", errors)
        if match.get("goalEventsStatus") not in allowed_goal_status:
            fail(f"{mid}: invalid goalEventsStatus {match.get('goalEventsStatus')!r}", errors)
        if len(goal_events) < expected_goals and match.get("goalEventsStatus") != "partial":
            fail(f"{mid}: missing goal events but status is not partial", errors)
        if len(goal_events) == expected_goals and match.get("goalEventsStatus") != "complete":
            fail(f"{mid}: complete goal event coverage but status is not complete", errors)


def assert_prediction_lineage(errors: list[str]) -> None:
    prediction = load_json(ROOT / "data" / "prediction" / "prediction_data_v1.json")
    schedule = load_json(ROOT / "data" / "matches" / "match_schedule.json")
    odds = load_json(ROOT / "data" / "matches" / "complete_odds.json")
    threats = load_json(ROOT / "data" / "prediction" / "player_threats.json")

    match_ids = {match.get("match_id") for match in prediction.get("matches", [])}
    group_schedule_ids = {
        match_id for match_id, match in schedule.items() if match.get("stage") == "group"
    }
    if match_ids != group_schedule_ids:
        fail("prediction matches do not match group schedule IDs", errors)
    if set(odds) != group_schedule_ids:
        fail("complete_odds IDs do not match group schedule IDs", errors)
    if not threats:
        fail("player_threats is empty", errors)


def assert_photo_lineage(errors: list[str]) -> None:
    mapping = load_json(ROOT / "data" / "squads" / "photo_mapping.json")
    referenced_paths = set()
    for name, info in mapping.items():
        photo_path = info.get("path") if isinstance(info, dict) else info
        if not isinstance(photo_path, str):
            fail(f"photo mapping for {name!r} has no path", errors)
            continue
        referenced_paths.add(photo_path)
        if not (ROOT / photo_path).is_file():
            fail(f"photo mapping for {name!r} points to missing file {photo_path}", errors)
            continue
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", photo_path],
            cwd=ROOT,
            check=False,
        )
        if ignored.returncode == 0:
            fail(
                f"photo mapping for {name!r} points to git-ignored asset {photo_path}",
                errors,
            )
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", photo_path],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if tracked.returncode != 0:
            fail(
                f"photo mapping for {name!r} points to untracked asset {photo_path}",
                errors,
            )

    for path in (ROOT / "data" / "photos").glob("sportsdb_*"):
        rel = path.relative_to(ROOT).as_posix()
        if rel not in referenced_paths:
            fail(f"unreferenced generated photo asset: {rel}", errors)


def assert_docs_are_current(errors: list[str]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "https://www.cameraclaw.cn/2026",
        "Random baseline",
        "Strength model",
        "Ensemble model",
        "$world-cup-2026-predictor",
        "python3 scripts/release_check.py",
    ):
        if required not in readme:
            fail(f"README.md missing current marker: {required}", errors)
    if "普通模式" in readme or "AI 综合" in readme:
        fail("README.md still contains retired UI/model names", errors)

    for image in re.findall(r'<img src="([^"]+)"', readme):
        if image.startswith("http"):
            continue
        if not (ROOT / image).is_file():
            fail(f"README.md references missing image {image}", errors)


def main() -> int:
    errors: list[str] = []
    assert_embeds_match_files(errors)
    assert_match_lineage(errors)
    assert_prediction_lineage(errors)
    assert_photo_lineage(errors)
    assert_docs_are_current(errors)

    if errors:
        print("Source lineage audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Source lineage audit passed.")
    print("- app embeds match canonical JSON files")
    print("- completed match IDs and goal event coverage are internally consistent")
    print("- prediction, odds, and player threat data are connected")
    print("- photo mappings point to existing assets with no unreferenced sportsdb files")
    print("- README contains current public, model, skill, and validation markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
