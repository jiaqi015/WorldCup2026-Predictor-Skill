#!/usr/bin/env python3
"""
Assemble the final prediction_data_v1.json from all intermediate data files.

Merges:
- data/rankings/elo_ratings_full.json (Step 1)
- data/matches/complete_odds.json (Step 2)
- data/prediction/player_threats.json (Step 3)
- data/rankings/fifa_rankings.json
- data/matches/match_schedule.json
- data/matches/match_details.json

Computes:
- Power scores (0-100) for all 48 teams
- Coverage report
- Validation errors

Output: data/prediction/prediction_data_v1.json
"""

import json
import math
import sys
from datetime import date
from pathlib import Path
from collections import Counter

BASE = Path(__file__).parent.parent

TEAMS_48 = [
    "墨西哥","南非","韩国","捷克","加拿大","波黑","卡塔尔","瑞士",
    "巴西","摩洛哥","海地","苏格兰","美国","巴拉圭","澳大利亚","土耳其",
    "德国","库拉索","科特迪瓦","厄瓜多尔","荷兰","日本","瑞典","突尼斯",
    "比利时","埃及","伊朗","新西兰","西班牙","佛得角","沙特","乌拉圭",
    "法国","伊拉克","塞内加尔","挪威","阿根廷","阿尔及利亚","奥地利","约旦",
    "葡萄牙","刚果金","乌兹别克","哥伦比亚","英格兰","克罗地亚","加纳","巴拿马",
]

TEAM_EN = {
    "墨西哥":"Mexico","南非":"South Africa","韩国":"South Korea","捷克":"Czechia",
    "加拿大":"Canada","波黑":"Bosnia and Herzegovina","卡塔尔":"Qatar","瑞士":"Switzerland",
    "巴西":"Brazil","摩洛哥":"Morocco","海地":"Haiti","苏格兰":"Scotland",
    "美国":"United States","巴拉圭":"Paraguay","澳大利亚":"Australia","土耳其":"Türkiye",
    "德国":"Germany","库拉索":"Curaçao","科特迪瓦":"Ivory Coast","厄瓜多尔":"Ecuador",
    "荷兰":"Netherlands","日本":"Japan","瑞典":"Sweden","突尼斯":"Tunisia",
    "比利时":"Belgium","埃及":"Egypt","伊朗":"Iran","新西兰":"New Zealand",
    "西班牙":"Spain","佛得角":"Cape Verde","沙特":"Saudi Arabia","乌拉圭":"Uruguay",
    "法国":"France","伊拉克":"Iraq","塞内加尔":"Senegal","挪威":"Norway",
    "阿根廷":"Argentina","阿尔及利亚":"Algeria","奥地利":"Austria","约旦":"Jordan",
    "葡萄牙":"Portugal","刚果金":"DR Congo","乌兹别克":"Uzbekistan","哥伦比亚":"Colombia",
    "英格兰":"England","克罗地亚":"Croatia","加纳":"Ghana","巴拿马":"Panama",
}

FIFA_CODE = {
    "墨西哥":"MEX","南非":"RSA","韩国":"KOR","捷克":"CZE",
    "加拿大":"CAN","波黑":"BIH","卡塔尔":"QAT","瑞士":"SUI",
    "巴西":"BRA","摩洛哥":"MAR","海地":"HAI","苏格兰":"SCO",
    "美国":"USA","巴拉圭":"PAR","澳大利亚":"AUS","土耳其":"TUR",
    "德国":"GER","库拉索":"CUW","科特迪瓦":"CIV","厄瓜多尔":"ECU",
    "荷兰":"NED","日本":"JPN","瑞典":"SWE","突尼斯":"TUN",
    "比利时":"BEL","埃及":"EGY","伊朗":"IRN","新西兰":"NZL",
    "西班牙":"ESP","佛得角":"CPV","沙特":"KSA","乌拉圭":"URU",
    "法国":"FRA","伊拉克":"IRQ","塞内加尔":"SEN","挪威":"NOR",
    "阿根廷":"ARG","阿尔及利亚":"ALG","奥地利":"AUT","约旦":"JOR",
    "葡萄牙":"POR","刚果金":"COD","乌兹别克":"UZB","哥伦比亚":"COL",
    "英格兰":"ENG","克罗地亚":"CRO","加纳":"GHA","巴拿马":"PAN",
}

# Strength tiers (same as STRENGTH in index.html)
STRENGTH = {
    "法国":5,"西班牙":5,"阿根廷":5,"英格兰":5,"葡萄牙":5,"巴西":5,"德国":5,
    "荷兰":4,"比利时":4,"克罗地亚":4,"摩洛哥":4,"乌拉圭":4,"哥伦比亚":4,"日本":4,
    "美国":3,"墨西哥":3,"加拿大":3,"瑞士":3,"韩国":3,"塞内加尔":3,"厄瓜多尔":3,
    "伊朗":3,"澳大利亚":3,"瑞典":3,"土耳其":3,"苏格兰":3,"奥地利":3,"挪威":3,
    "阿尔及利亚":3,"巴拉圭":3,"科特迪瓦":3,"加纳":3,"捷克":3,"突尼斯":3,
    "沙特":2,"卡塔尔":2,"埃及":2,"南非":2,"波黑":2,"伊拉克":2,"乌兹别克":2,
    "约旦":2,"刚果金":2,"新西兰":2,"巴拿马":2,
    "海地":1,"库拉索":1,"佛得角":1,
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_power_score(elo, fifa_rank, team_cn, team_odds_probs):
    """
    Compute composite power score (0-100).
    Formula: 0.40 * elo_norm + 0.25 * fifa_norm + 0.20 * squad_depth + 0.15 * market_strength
    """
    # Elo normalization: 1500 -> 0, 2100 -> 100
    elo_norm = max(0, min(100, (elo - 1500) / 600 * 100))

    # FIFA rank normalization: rank 1 -> 100, rank 105 -> 0
    if fifa_rank and fifa_rank > 0:
        fifa_norm = max(0, min(100, (1 - math.log(fifa_rank) / math.log(106)) * 100))
    else:
        fifa_norm = 50  # default

    # Squad depth: use STRENGTH tier as proxy (data limitation)
    tier = STRENGTH.get(team_cn, 3)
    squad_depth = tier / 5.0 * 100

    # Market strength: average implied win probability across group matches
    if team_odds_probs:
        market_strength = sum(team_odds_probs) / len(team_odds_probs) * 100
    else:
        market_strength = squad_depth  # fallback to tier

    power = 0.40 * elo_norm + 0.25 * fifa_norm + 0.20 * squad_depth + 0.15 * market_strength
    return round(power, 1), {
        "elo": {"value": elo, "normalized": round(elo_norm, 1), "weight": 0.40},
        "fifa_rank": {"value": fifa_rank, "normalized": round(fifa_norm, 1), "weight": 0.25},
        "squad_depth": {"value": tier, "normalized": round(squad_depth, 1), "weight": 0.20, "notes": "Estimated from STRENGTH tier due to lack of club-level data"},
        "market_strength": {"value": round(sum(team_odds_probs) / len(team_odds_probs), 4) if team_odds_probs else None, "normalized": round(market_strength, 1), "weight": 0.15},
    }


def main():
    today = date.today().isoformat()

    # Load all intermediate data
    elo_data = load_json(BASE / "data" / "rankings" / "elo_ratings_full.json")
    fifa_rank = load_json(BASE / "data" / "rankings" / "fifa_rankings.json")
    odds_data = load_json(BASE / "data" / "matches" / "complete_odds.json")
    player_threats = load_json(BASE / "data" / "prediction" / "player_threats.json")
    match_schedule = load_json(BASE / "data" / "matches" / "match_schedule.json")
    match_details = load_json(BASE / "data" / "matches" / "match_details.json")

    print(f"[build] Loaded: {len(elo_data)} Elo, {len(fifa_rank)} FIFA ranks, "
          f"{len(odds_data)} odds, {len(player_threats)} players, "
          f"{len(match_schedule)} matches, {len(match_details)} completed details")

    # --- Build teams array ---
    # First, collect each team's implied win probabilities from odds
    team_win_probs = {t: [] for t in TEAMS_48}
    for mid, entry in odds_data.items():
        o = entry.get("odds")
        if not o:
            continue
        home = entry["home_team_cn"]
        away = entry["away_team_cn"]
        if home in team_win_probs:
            team_win_probs[home].append(o.get("home_raw_implied_probability", 0))
        if away in team_win_probs:
            team_win_probs[away].append(o.get("away_raw_implied_probability", 0))

    teams = []
    for team_cn in TEAMS_48:
        elo_entry = elo_data.get(team_cn, {})
        elo_val = elo_entry.get("elo", 1550)
        rank = fifa_rank.get(team_cn)

        power_score, raw_inputs = compute_power_score(
            elo_val, rank, team_cn, team_win_probs.get(team_cn, [])
        )

        confidence = "high"
        notes = None
        if elo_entry.get("source") == "fifa_rank_regression":
            confidence = "low"
            notes = f"Elo estimated from FIFA rank {rank}"
        elif elo_entry.get("source") == "default":
            confidence = "low"
            notes = "Elo and rank both estimated"

        teams.append({
            "team_cn": team_cn,
            "team_en": TEAM_EN[team_cn],
            "fifa_code": FIFA_CODE[team_cn],
            "fifa_rank": rank,
            "elo": elo_val,
            "raw_power_inputs": raw_inputs,
            "power_score_formula": "normalized weighted blend: elo 0.40, fifa_rank 0.25, squad_depth 0.20, market_strength 0.15",
            "power_score_0_100": power_score,
            "sources": [
                {
                    "type": "elo",
                    "name": "World Football Elo Ratings" if elo_entry.get("source") in ("eloratings.net", "existing_data") else "Estimated from FIFA rank",
                    "url": None,
                    "as_of": elo_entry.get("as_of", today),
                    "source_type": elo_entry.get("source", "observed"),
                },
                {
                    "type": "fifa_rank",
                    "name": "FIFA Official Rankings",
                    "url": None,
                    "as_of": "2026-06-01",
                    "source_type": "observed",
                },
            ],
            "confidence": confidence,
            "notes": notes,
        })

    # --- Build matches array ---
    matches = []
    for mid, entry in odds_data.items():
        sched = match_schedule.get(mid, {})
        odds_entry = entry.get("odds")

        match_record = {
            "match_id": mid,
            "stage": sched.get("stage", "group"),
            "group": sched.get("group"),
            "date_utc": sched.get("date"),
            "home_team_cn": entry["home_team_cn"],
            "away_team_cn": entry["away_team_cn"],
            "odds": None,
            "source_url": None,
            "as_of": today,
            "confidence": entry.get("confidence", "low"),
            "source_type": entry.get("source_type", "unknown"),
            "notes": entry.get("notes"),
            "actual_result": None,
        }

        detail = match_details.get(mid)
        if detail:
            match_record["actual_result"] = {
                "home_score": detail.get("homeScore"),
                "away_score": detail.get("awayScore"),
                "attendance": detail.get("attendance"),
                "referee": detail.get("referee"),
                "events": detail.get("events", []),
                "source": "ESPN summary API",
                "source_url": f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={mid}",
            }

        if odds_entry:
            match_record["odds"] = {
                "provider": odds_entry.get("provider", "DraftKings"),
                "method": odds_entry.get("method", "unknown"),
                "source_type": odds_entry.get("source_type", entry.get("source_type", "unknown")),
                "raw_market_text": odds_entry.get("original_details", ""),
                "home_moneyline_american": odds_entry.get("home_moneyline_american"),
                "draw_moneyline_american": odds_entry.get("draw_moneyline_american"),
                "away_moneyline_american": odds_entry.get("away_moneyline_american"),
                "home_decimal": odds_entry.get("home_decimal"),
                "draw_decimal": odds_entry.get("draw_decimal"),
                "away_decimal": odds_entry.get("away_decimal"),
                "home_raw_implied_probability": odds_entry.get("home_raw_implied_probability"),
                "draw_raw_implied_probability": odds_entry.get("draw_raw_implied_probability"),
                "away_raw_implied_probability": odds_entry.get("away_raw_implied_probability"),
                "home_no_vig_probability": None,
                "draw_no_vig_probability": None,
                "away_no_vig_probability": None,
                "over_under_goals": odds_entry.get("over_under_goals"),
            }
            # All 3 outcomes present, compute no-vig probabilities
            if all(match_record["odds"].get(f"{s}_raw_implied_probability") for s in ("home", "draw", "away")):
                total = sum(match_record["odds"][f"{s}_raw_implied_probability"] for s in ("home", "draw", "away"))
                if total > 0:
                    for s in ("home", "draw", "away"):
                        match_record["odds"][f"{s}_no_vig_probability"] = round(
                            match_record["odds"][f"{s}_raw_implied_probability"] / total, 4
                        )

        matches.append(match_record)

    scoring_event_types = {"goal", "penalty_goal", "own_goal"}
    actual_match_events = []
    for match_id, detail in match_details.items():
        for event_index, event in enumerate(detail.get("events", [])):
            event_type = event.get("type")
            if event_type not in scoring_event_types:
                continue
            record = {
                "event_id": f"{match_id}:{event_type}:{event_index}",
                "match_id": match_id,
                "event_type": event_type,
                "minute": event.get("minute"),
                "team_side": event.get("team"),
                "team_cn": event.get("team_cn"),
                "scoring_team_cn": event.get("scoring_team_cn") or event.get("team_cn"),
                "player_team_cn": event.get("player_team_cn") or event.get("scorer_team_cn"),
                "own_goal": bool(event.get("own_goal")),
                "penalty_kick": bool(event.get("penalty_kick")),
                "player_source_name": event.get("scorer_source_name"),
                "player_display_name_cn": event.get("scorer_cn"),
                "player_app_alias": event.get("scorer_app_alias"),
                "player_mapping_status": event.get("scorer_mapping_status"),
                "player_mapping_key": event.get("scorer_mapping_key"),
                "player_jersey": event.get("scorer_jersey"),
                "player_position": event.get("scorer_position"),
                "assist_source_name": event.get("assist_source_name"),
                "assist_display_name_cn": event.get("assist_cn"),
                "assist_app_alias": event.get("assist_app_alias"),
                "assist_mapping_status": event.get("assist_mapping_status"),
                "source": "ESPN summary API",
                "source_url": f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={match_id}",
                "as_of": today,
            }
            actual_match_events.append(record)

    # --- Build player_threats array (restructure from flat list to schema format) ---
    threats = []
    for p in player_threats:
        threats.append({
            "team_cn": p["team_cn"],
            "team_en": p["team_en"],
            "player_name_source": p["player_name_source"],
            "player_name_app_alias": p["player_name_app_alias"],
            "position": p["position"],
            "role_tags": p["role_tags"],
            "goal_threat": {
                "multiplier": p["goal_threat"]["multiplier"],
                "basis": p["goal_threat"]["basis"],
                "confidence": p["goal_threat"]["confidence"],
            },
            "assist_threat": {
                "multiplier": p["assist_threat"]["multiplier"],
                "basis": p["assist_threat"]["basis"],
                "confidence": p["assist_threat"]["confidence"],
            },
            "star_tier": p["star_tier"],
            "rationale": p["rationale"],
            "sources": p["sources"],
            "confidence": p["confidence"],
        })

    # --- Build coverage_report ---
    team_counts = Counter(p["team_cn"] for p in threats)
    matches_with_complete = sum(1 for m in matches if m["odds"] and all(
        m["odds"].get(f"{s}_moneyline_american") is not None for s in ("home", "draw", "away")
    ))
    matches_with_partial = sum(1 for m in matches if m["odds"])
    matches_with_ou = sum(1 for m in matches if m["odds"] and m["odds"].get("over_under_goals") is not None)

    missing_app_alias = [p["player_name_app_alias"] for p in threats if not p["player_name_app_alias"]]
    low_conf = [p["player_name_app_alias"] for p in threats if p["confidence"] == "low"]
    teams_below_min = [t for t in TEAMS_48 if team_counts.get(t, 0) < 2]

    coverage_report = {
        "teams": {
            "expected_count": 48,
            "actual_count": len(teams),
            "missing_team_cn": [t for t in TEAMS_48 if t not in {x["team_cn"] for x in teams}],
            "extra_team_cn": [x["team_cn"] for x in teams if x["team_cn"] not in TEAMS_48],
        },
        "team_power": {
            "missing_elo": [t["team_cn"] for t in teams if t["elo"] is None],
            "missing_fifa_rank": [t["team_cn"] for t in teams if t["fifa_rank"] is None],
            "estimated_power_score": [t["team_cn"] for t in teams if t["confidence"] in ("medium", "low")],
        },
        "matches": {
            "match_count": len(matches),
            "matches_with_complete_1x2_odds": matches_with_complete,
            "matches_with_partial_odds": matches_with_partial,
            "matches_missing_odds": [m["match_id"] for m in matches if not m["odds"]],
            "matches_with_over_under": matches_with_ou,
        },
        "player_threats": {
            "total_players": len(threats),
            "players_per_team": dict(team_counts),
            "teams_below_minimum": teams_below_min,
            "missing_app_alias": missing_app_alias,
            "low_confidence_players": low_conf,
        },
        "actual_match_events": {
            "completed_matches": len(match_details),
            "goal_events": len(actual_match_events),
            "mapped_scorers": sum(
                1 for event in actual_match_events
                if event.get("player_mapping_status") == "matched_team_player"
            ),
            "source_only_scorers": [
                event["player_source_name"] for event in actual_match_events
                if event.get("player_mapping_status") != "matched_team_player"
            ],
        },
        "data_quality_notes": [],
    }

    # Add quality notes
    if coverage_report["team_power"]["estimated_power_score"]:
        coverage_report["data_quality_notes"].append(
            f"{len(coverage_report['team_power']['estimated_power_score'])} teams have estimated Elo (from FIFA rank regression)"
        )
    if len(threats) > 200:
        coverage_report["data_quality_notes"].append(
            f"Player count ({len(threats)}) exceeds 200 target; all non-GK simulation roster players included for better simulation coverage"
        )

    # --- Run validation ---
    validation_errors = []

    # Check teams count
    if len(teams) != 48:
        validation_errors.append(f"Expected 48 teams, got {len(teams)}")

    # Check team names
    for t in teams:
        if t["team_cn"] not in TEAMS_48:
            validation_errors.append(f"Unexpected team: {t['team_cn']}")

    # Check Elo range
    for t in teams:
        if t["elo"] is not None and not (1400 <= t["elo"] <= 2200):
            validation_errors.append(f"{t['team_cn']}: Elo {t['elo']} out of range [1400, 2200]")

    # Check power score range
    for t in teams:
        if not (0 <= t["power_score_0_100"] <= 100):
            validation_errors.append(f"{t['team_cn']}: power_score {t['power_score_0_100']} out of range [0, 100]")

    # Check player threats
    for p in threats:
        gt = p["goal_threat"]["multiplier"]
        at = p["assist_threat"]["multiplier"]
        if not (0.0 <= gt <= 6.0):
            validation_errors.append(f"{p['player_name_app_alias']}: goal_threat {gt} out of range")
        if not (0.0 <= at <= 6.0):
            validation_errors.append(f"{p['player_name_app_alias']}: assist_threat {at} out of range")
        if p["goal_threat"]["confidence"] not in ("high", "medium", "low"):
            validation_errors.append(f"{p['player_name_app_alias']}: bad goal confidence")
        if p["assist_threat"]["confidence"] not in ("high", "medium", "low"):
            validation_errors.append(f"{p['player_name_app_alias']}: bad assist confidence")
        if p["confidence"] not in ("high", "medium", "low"):
            validation_errors.append(f"{p['player_name_app_alias']}: bad overall confidence")

    # Check odds
    for m in matches:
        if m["odds"]:
            o = m["odds"]
            for side in ("home_decimal", "draw_decimal", "away_decimal"):
                val = o.get(side)
                if val is not None and val <= 1.0:
                    validation_errors.append(f"{m['match_id']}: {side} = {val} <= 1.0")

    for event in actual_match_events:
        if not event.get("team_cn"):
            validation_errors.append(f"{event['event_id']}: missing team")
        if not event.get("player_source_name"):
            validation_errors.append(f"{event['event_id']}: missing ESPN scorer name")
        if event.get("player_mapping_status") not in ("matched_team_player", "source_only"):
            validation_errors.append(f"{event['event_id']}: invalid player mapping status")

    # --- Assemble final JSON ---
    output = {
        "schema_version": 1,
        "generated_at": today,
        "data_scope": {
            "tournament": "FIFA World Cup 2026",
            "team_count": 48,
            "teams_locked": True,
        },
        "teams": teams,
        "matches": matches,
        "player_threats": threats,
        "actual_match_events": actual_match_events,
        "coverage_report": coverage_report,
        "validation_errors": validation_errors,
    }

    # Summary
    print(f"\n[build] === SUMMARY ===")
    print(f"  Teams: {len(teams)}")
    print(f"  Matches: {len(matches)}")
    print(f"  Player threats: {len(threats)}")
    print(f"  Power scores: {len([t for t in teams if t['power_score_0_100']])}")
    print(f"  Odds with all 3 outcomes: {matches_with_complete}")
    print(f"  Validation errors: {len(validation_errors)}")

    if validation_errors:
        print(f"\n  Errors:")
        for e in validation_errors[:10]:
            print(f"    {e}")
    else:
        print(f"  All validation checks passed!")

    # Power score ranking
    ranked = sorted(teams, key=lambda t: -t["power_score_0_100"])
    print(f"\n[build] Top 10 power scores:")
    for i, t in enumerate(ranked[:10], 1):
        print(f"  {i}. {t['team_cn']}: {t['power_score_0_100']} (Elo {t['elo']}, rank {t['fifa_rank']})")

    # Write output
    output_path = BASE / "data" / "prediction" / "prediction_data_v1.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Written to {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
