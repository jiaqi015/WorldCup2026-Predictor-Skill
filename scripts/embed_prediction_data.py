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
- weightedPick: modified to use PLAYER_THREATS_MAP
- normalizeOddsMarket: modified to try COMPLETE_ODDS
- TEAM_STRENGTH_TIERS: sync with corrected JSON
"""

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
INDEX_FILE = BASE / "index.html"
SKILL_INDEX = BASE / "skills" / "world-cup-2026-predictor" / "assets" / "predictor" / "index.html"
PREDICTION_FILE = BASE / "data" / "prediction" / "prediction_data_v1.json"
ELO_FILE = BASE / "data" / "rankings" / "elo_ratings_full.json"
ODDS_FILE = BASE / "data" / "matches" / "complete_odds.json"
THREATS_FILE = BASE / "data" / "prediction" / "player_threats.json"
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


def main():
    # Load data
    prediction = load_json(PREDICTION_FILE)
    elo_data = load_json(ELO_FILE)
    odds_data = load_json(ODDS_FILE)
    threats_list = load_json(THREATS_FILE)
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
    html = upsert_var(html, "POWER_SCORES", power_js)
    html = upsert_var(html, "PLAYER_THREATS_MAP", threats_js)
    html = upsert_var(html, "COMPLETE_ODDS", odds_js)
    html = upsert_var(html, "MATCH_SCHEDULE", schedule_js)
    html = upsert_var(html, "MATCH_DETAILS", details_js)
    html = upsert_var(html, "MATCH_DATA_META", manifest_js)
    changes.append(
        "ELO_RATINGS, TEAM_STRENGTH_TIERS, POWER_SCORES, "
        "PLAYER_THREATS_MAP, COMPLETE_ODDS, MATCH_SCHEDULE, "
        "MATCH_DETAILS, MATCH_DATA_META (idempotent)"
    )

    # 4. Modify weightedPick to use PLAYER_THREATS_MAP
    old_weighted_pick = '''function weightedPick(players,team,weights,fallback){
  if(!players||!players.length)return null;
  var pool=[];
  for(var i=0;i<players.length;i++){
    var p=players[i],pos=getPos(p,team);
    var w=weights[pos];if(w===undefined)w=fallback;
    for(var j=0;j<w;j++)pool.push(p);
  }
  if(!pool.length)return players[Math.floor(Math.random()*players.length)];
  return pool[Math.floor(Math.random()*pool.length)];
}'''

    new_weighted_pick = '''function weightedPick(players,team,weights,fallback,type){
  if(!players||!players.length)return null;
  var pool=[];
  var threatMap=(typeof PLAYER_THREATS_MAP!=="undefined")?PLAYER_THREATS_MAP:null;
  for(var i=0;i<players.length;i++){
    var p=players[i],pos=getPos(p,team);
    var w=weights[pos];if(w===undefined)w=fallback;
    if(threatMap&&threatMap[p]){
      var mult=(type==="assist")?threatMap[p].a:threatMap[p].g;
      if(mult>0)w=Math.max(1,Math.round(w*mult));
    }
    for(var j=0;j<w;j++)pool.push(p);
  }
  if(!pool.length)return players[Math.floor(Math.random()*players.length)];
  return pool[Math.floor(Math.random()*pool.length)];
}'''

    if old_weighted_pick in html:
        html = html.replace(old_weighted_pick, new_weighted_pick)
        changes.append("weightedPick (added PLAYER_THREATS_MAP integration)")
    elif (
        "function weightedPick(players,team,weights,fallback,type)" in html
        and 'type==="assist"' in html
    ):
        changes.append("weightedPick (already integrated)")
    else:
        # Try minified version matching
        print("[embed] WARNING: Could not find weightedPick exact match, trying fuzzy...")
        # The code might be minified differently, try to find and replace the key logic
        old_pattern = r'var w=weights\[pos\];if\(w===undefined\)w=fallback;\s*for\(var j=0;j<w;j\+\+\)pool\.push\(p\);'
        new_logic = 'var w=weights[pos];if(w===undefined)w=fallback;if(typeof PLAYER_THREATS_MAP!=="undefined"&&PLAYER_THREATS_MAP[p]){var _m=(type==="assist")?PLAYER_THREATS_MAP[p].a:PLAYER_THREATS_MAP[p].g;if(_m>0)w=Math.max(1,Math.round(w*_m));}for(var j=0;j<w;j++)pool.push(p);'
        if re.search(old_pattern, html):
            html = re.sub(old_pattern, new_logic, html)
            # Also need to add the type parameter to the function signature
            html = html.replace(
                'function weightedPick(players,team,weights,fallback)',
                'function weightedPick(players,team,weights,fallback,type)'
            )
            changes.append("weightedPick (fuzzy match)")
        else:
            print("[embed] WARNING: Could not modify weightedPick")

    # 5. Modify normalizeOddsMarket to try COMPLETE_ODDS
    old_normalize = '''function normalizeOddsMarket(market){
  if(!market)return null;
  var implied={};
  if(Number(market.home)>1)implied.home=1/Number(market.home);
  if(Number(market.draw)>1)implied.draw=1/Number(market.draw);
  if(Number(market.away)>1)implied.away=1/Number(market.away);
  if(!implied.home||!implied.away)return null;
  return normalize(implied);
}'''

    new_normalize = '''function normalizeOddsMarket(market,matchId){
  var co=(typeof COMPLETE_ODDS!=="undefined"&&matchId)?COMPLETE_ODDS[matchId]:null;
  if(co){
    var ci={home:1/co.h,draw:1/co.d,away:1/co.a};
    return normalize(ci);
  }
  if(!market)return null;
  var implied={};
  if(Number(market.home)>1)implied.home=1/Number(market.home);
  if(Number(market.draw)>1)implied.draw=1/Number(market.draw);
  if(Number(market.away)>1)implied.away=1/Number(market.away);
  if(!implied.home||!implied.away)return null;
  return normalize(implied);
}'''

    if old_normalize in html:
        html = html.replace(old_normalize, new_normalize)
        changes.append("normalizeOddsMarket (COMPLETE_ODDS integration)")

        # Update call site to pass matchId
        # Find: normalizeOddsMarket(options.oddsMarket)
        # Replace with: normalizeOddsMarket(options.oddsMarket,options.matchId)
        html = html.replace(
            'normalizeOddsMarket(options.oddsMarket)',
            'normalizeOddsMarket(options.oddsMarket,options.matchId)'
        )
        changes.append("normalizeOddsMarket call site (added matchId param)")
    elif (
        "function normalizeOddsMarket(market,matchId)" in html
        and "COMPLETE_ODDS[matchId]" in html
    ):
        changes.append("normalizeOddsMarket (already integrated)")
    else:
        print("[embed] WARNING: Could not find normalizeOddsMarket exact match")

    # 6. Update STRENGTH variable with float power scores (backward compatible)
    # Convert power scores to 1-5 float scale for STRENGTH
    strength_float = {}
    for team_cn, ps in power_scores.items():
        strength_float[team_cn] = round(ps / 20, 1)  # 0→0.0, 50→2.5, 100→5.0
    strength_js = to_minified_js(strength_float)

    # Check if STRENGTH exists and replace it
    strength_pattern = r'var STRENGTH=\{[^}]+\};'
    if re.search(strength_pattern, html, re.DOTALL):
        html = re.sub(strength_pattern, f'var STRENGTH={strength_js};', html, flags=re.DOTALL)
        changes.append("STRENGTH (upgraded from integer tiers to float power scores)")

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
