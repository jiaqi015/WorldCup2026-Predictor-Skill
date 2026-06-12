#!/usr/bin/env python3
"""Validate prediction snapshots, provenance, and generated app bindings."""

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEAMS = {
    "墨西哥", "南非", "韩国", "捷克", "加拿大", "波黑", "卡塔尔", "瑞士",
    "巴西", "摩洛哥", "海地", "苏格兰", "美国", "巴拉圭", "澳大利亚", "土耳其",
    "德国", "库拉索", "科特迪瓦", "厄瓜多尔", "荷兰", "日本", "瑞典", "突尼斯",
    "比利时", "埃及", "伊朗", "新西兰", "西班牙", "佛得角", "沙特", "乌拉圭",
    "法国", "伊拉克", "塞内加尔", "挪威", "阿根廷", "阿尔及利亚", "奥地利", "约旦",
    "葡萄牙", "刚果金", "乌兹别克", "哥伦比亚", "英格兰", "克罗地亚", "加纳", "巴拿马",
}


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def main():
    errors = []
    schedule = load("data/matches/match_schedule.json")
    manifest = load("data/matches/manifest.json")
    odds = load("data/matches/complete_odds.json")
    elo = load("data/rankings/elo_ratings_full.json")
    tiers = load("data/rankings/team_strength_tiers.json")
    threats = load("data/prediction/player_threats.json")
    prediction = load("data/prediction/prediction_data_v1.json")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    group_matches = [match for match in schedule.values() if match.get("stage") == "group"]
    schedule_teams = {
        team for match in group_matches for team in (match["home"], match["away"])
    }
    require(len(schedule) == 104, f"schedule has {len(schedule)} matches, expected 104", errors)
    require(len(group_matches) == 72, f"group schedule has {len(group_matches)} matches", errors)
    require(schedule_teams == TEAMS, "schedule team set differs from tournament teams", errors)
    require(manifest.get("match_count") == 104, "match manifest count is stale", errors)
    require(manifest.get("source") == "ESPN public scoreboard API", "unexpected match source", errors)

    tier_teams = [team for values in tiers.values() for team in values]
    require(len(tier_teams) == 48, f"strength tiers contain {len(tier_teams)} entries", errors)
    require(set(tier_teams) == TEAMS, "strength tiers do not match tournament teams", errors)
    require(len(tier_teams) == len(set(tier_teams)), "strength tiers contain duplicates", errors)
    require("丹麦" not in tier_teams, "Denmark remains in strength tiers", errors)

    require(set(elo) == TEAMS, "Elo snapshot does not cover exactly 48 teams", errors)
    for team, entry in elo.items():
        if entry.get("source") == "fifa_rank_regression":
            require(entry.get("confidence") == "low", f"{team} estimated Elo must be low confidence", errors)

    require(len(odds) == 72, f"odds snapshot has {len(odds)} matches", errors)
    for match_id, entry in odds.items():
        source_type = entry.get("source_type")
        require(source_type in {"derived", "missing", "unavailable"}, f"{match_id} lacks source_type", errors)
        if entry.get("odds"):
            market = entry["odds"]
            require(market.get("method") == "derived_from_partial", f"{match_id} method is ambiguous", errors)
            require(market.get("source_type") == "derived", f"{match_id} market lacks derived label", errors)

    threat_counts = Counter(item["team_cn"] for item in threats)
    require(set(threat_counts) == TEAMS, "player threats do not cover exactly 48 teams", errors)
    require(all(count >= 2 for count in threat_counts.values()), "a team has fewer than two threat players", errors)

    require(len(prediction.get("teams", [])) == 48, "prediction output team count is not 48", errors)
    require(len(prediction.get("matches", [])) == 72, "prediction output match count is not 72", errors)
    require(not prediction.get("validation_errors"), "prediction output contains validation errors", errors)

    for name in (
        "FIFA_RANKINGS", "MATCH_SCHEDULE", "MATCH_DETAILS", "MATCH_DATA_META",
        "ELO_RATINGS", "TEAM_STRENGTH_TIERS", "POWER_SCORES",
        "PLAYER_THREATS_MAP", "COMPLETE_ODDS",
    ):
        count = len(re.findall(rf"var\s+{name}=", html))
        require(count == 1, f"{name} appears {count} times in index.html", errors)
    require("var COACHES=" not in html, "unused coach snapshot remains embedded", errors)
    require('"JAM":"约旦"' not in html, "invalid Jamaica-to-Jordan mapping remains", errors)

    if errors:
        print("Prediction data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    derived = sum(1 for entry in odds.values() if entry.get("source_type") == "derived")
    estimated_elo = sum(1 for entry in elo.values() if entry.get("source") == "fifa_rank_regression")
    print("Prediction data validation passed.")
    print(f"- schedule: 104 matches / 72 group matches / 48 teams")
    print(f"- odds: {derived} explicitly model-derived markets")
    print(f"- Elo: {estimated_elo} low-confidence rank-regression estimates")
    print(f"- player threats: {len(threats)} players across 48 teams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
