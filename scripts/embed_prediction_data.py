#!/usr/bin/env python3
"""
Embed prediction data into index.html.

Adds/updates:
- ELO_RATINGS: expanded to all 48 teams
- POWER_SCORES: new variable
- PLAYER_THREATS_MAP: new variable (goal + assist multipliers)
- COMPLETE_ODDS: new variable (decimal odds per match)
- MATCH_SCHEDULE: ESPN fixture snapshot, including bilingual venue fields
- MATCH_DETAILS: completed match events, including team-scoped player mappings
- MATCH_DATA_META: source manifest for the match snapshot
- TEAM_STRENGTH_TIERS: sync with corrected JSON
- STRENGTH: derived 1-5 team power values
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
INDEX_FILE = BASE / "index.html"
SKILL_INDEX = BASE / "skills" / "world-cup-2026-predictor" / "assets" / "predictor" / "index.html"
PREDICTION_FILE = BASE / "data" / "prediction" / "prediction_data_v1.json"
ELO_FILE = BASE / "data" / "rankings" / "elo_ratings_full.json"
STRENGTH_TIERS_FILE = BASE / "data" / "rankings" / "team_strength_tiers.json"
MATCH_SCHEDULE_FILE = BASE / "data" / "matches" / "match_schedule.json"
MATCH_DETAILS_FILE = BASE / "data" / "matches" / "match_details.json"
MATCH_MANIFEST_FILE = BASE / "data" / "matches" / "manifest.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def to_minified_js(obj):
    """Convert Python object to minified JS-compatible string with inline Chinese."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def upsert_var(html, var_name, js_value):
    """Keep exactly one generated variable declaration."""
    pattern = rf"\n?var\s+{re.escape(var_name)}\s*=.*?;\n?"
    html = re.sub(pattern, "\n", html, flags=re.DOTALL)
    marker = "// === END REAL DATA ==="
    idx = html.find(marker)
    if idx < 0:
        raise RuntimeError(f"missing data marker: {marker}")
    return html[:idx] + f"var {var_name}={js_value};\n" + html[idx:]


def validate_runtime_integrations(html):
    """Keep data generation from silently rewriting application behavior."""
    required = {
        "player threat integration": (
            "function weightedPick(players,team,weights,fallback,type)",
            'type==="assist"',
            'threatMap[team+"|"+p]',
        ),
        "complete odds integration": (
            "function normalizeOddsMarket(market,matchId)",
            "COMPLETE_ODDS[matchId]",
            "normalizeOddsMarket(options.oddsMarket,options.matchId)",
        ),
    }
    missing = [
        name
        for name, markers in required.items()
        if not all(marker in html for marker in markers)
    ]
    if missing:
        raise RuntimeError(
            "index.html is missing runtime integration: " + ", ".join(missing)
        )


def main():
    # Load data
    prediction = load_json(PREDICTION_FILE)
    elo_data = load_json(ELO_FILE)
    strength_tiers = load_json(STRENGTH_TIERS_FILE)
    match_schedule = load_json(MATCH_SCHEDULE_FILE)
    match_details = load_json(MATCH_DETAILS_FILE)
    match_manifest = load_json(MATCH_MANIFEST_FILE)

    # Build ELO_RATINGS (all 48 teams, simple {team: elo} format)
    elo_ratings = {}
    for team, data in elo_data.items():
        elo_ratings[team] = data["elo"]

    # Build POWER_SCORES (team -> 0-100 float)
    power_scores = {}
    for t in prediction["teams"]:
        power_scores[t["team_cn"]] = t["power_score_0_100"]
    strength_float = {
        team_cn: round(power_score / 20, 1)
        for team_cn, power_score in power_scores.items()
    }

    # Build PLAYER_THREATS_MAP (team-qualified `team|player` key + bare key fallback).
    # Cross-team同名球员（"阿尔瓦雷斯"在阿根廷+墨西哥）需要 team-qualified 区分；
    # weightedPick 优先 PLAYER_THREATS_MAP[team+"|"+player]，再 fallback bare key。
    player_threats_map = {}
    for p in prediction["player_threats"]:
        alias = p["player_name_app_alias"]
        team_cn = p.get("team_cn", "")
        if not alias:
            continue
        entry = {
            "g": p["goal_threat"]["multiplier"],
            "a": p["assist_threat"]["multiplier"],
        }
        if team_cn:
            player_threats_map[f"{team_cn}|{alias}"] = entry
        # Bare key (last write wins on collisions; the team-qualified key above is precise).
        player_threats_map[alias] = entry

    # Build COMPLETE_ODDS (match_id -> {home: decimal, draw: decimal, away: decimal})
    complete_odds = {}
    for m in prediction["matches"]:
        if m.get("odds") and m["odds"].get("home_decimal"):
            complete_odds[m["match_id"]] = {
                "h": m["odds"]["home_decimal"],
                "d": m["odds"]["draw_decimal"],
                "a": m["odds"]["away_decimal"],
                "m": m["odds"].get("method", "unknown"),
                "c": m.get("confidence", "low"),
            }

    # Minify all JS objects
    elo_js = to_minified_js(elo_ratings)
    power_js = to_minified_js(power_scores)
    threats_js = to_minified_js(player_threats_map)
    odds_js = to_minified_js(complete_odds)
    tiers_js = to_minified_js(strength_tiers)
    strength_js = to_minified_js(strength_float)
    schedule_js = to_minified_js(match_schedule)
    details_js = to_minified_js(match_details)
    manifest_js = to_minified_js(match_manifest)

    print(f"[embed] ELO_RATINGS: {len(elo_ratings)} teams")
    print(f"[embed] POWER_SCORES: {len(power_scores)} teams")
    print(f"[embed] PLAYER_THREATS_MAP: {len(player_threats_map)} players")
    print(f"[embed] COMPLETE_ODDS: {len(complete_odds)} matches")
    print(f"[embed] TEAM_STRENGTH_TIERS: synced")
    print(f"[embed] MATCH_SCHEDULE: {len(match_schedule)} matches")
    print(f"[embed] MATCH_DETAILS: {len(match_details)} completed matches")
    print("[embed] MATCH_DATA_META: synced")

    # Read index.html
    html = INDEX_FILE.read_text(encoding="utf-8")
    original_len = len(html)
    changes = []

    html = upsert_var(html, "ELO_RATINGS", elo_js)
    html = upsert_var(html, "TEAM_STRENGTH_TIERS", tiers_js)
    html = upsert_var(html, "STRENGTH", strength_js)
    html = upsert_var(html, "POWER_SCORES", power_js)
    html = upsert_var(html, "PLAYER_THREATS_MAP", threats_js)
    html = upsert_var(html, "COMPLETE_ODDS", odds_js)
    html = upsert_var(html, "MATCH_SCHEDULE", schedule_js)
    html = upsert_var(html, "MATCH_DETAILS", details_js)
    html = upsert_var(html, "MATCH_DATA_META", manifest_js)
    changes.append(
        "ELO_RATINGS, TEAM_STRENGTH_TIERS, STRENGTH, POWER_SCORES, "
        "PLAYER_THREATS_MAP, COMPLETE_ODDS, MATCH_SCHEDULE, "
        "MATCH_DETAILS, MATCH_DATA_META (idempotent)"
    )

    validate_runtime_integrations(html)
    changes.append("runtime integration contract (validated, not rewritten)")

    # Write output
    INDEX_FILE.write_text(html, encoding="utf-8")
    new_len = len(html)
    print(f"\n[embed] Changes applied to index.html ({original_len} → {new_len} bytes):")
    for c in changes:
        print(f"  - {c}")

    # Sync to skill copy
    if SKILL_INDEX.exists():
        import shutil
        shutil.copy2(INDEX_FILE, SKILL_INDEX)
        print(f"\n[embed] Synced to skill copy: {SKILL_INDEX}")
    else:
        print(f"\n[embed] Skill copy not found at {SKILL_INDEX}, skipping sync")


if __name__ == "__main__":
    main()
