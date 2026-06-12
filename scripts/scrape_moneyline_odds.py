#!/usr/bin/env python3
"""
Compute complete 3-way moneyline odds for all 72 group-stage matches.

Strategy:
1. Use the partial market fields already present in the ESPN schedule snapshot
2. Derive the missing side from an explicitly documented strength prior
3. Mark completed matches as unavailable rather than inventing historical odds

Output: data/matches/complete_odds.json
"""

import json
import math
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date

BASE = Path(__file__).parent.parent
MATCH_FILE = BASE / "data" / "matches" / "match_schedule.json"
STRENGTH_FILE = BASE / "data" / "rankings" / "team_strength_tiers.json"
OUTPUT_FILE = BASE / "data" / "matches" / "complete_odds.json"

TEAM_ABBR = {
    "墨西哥": "MEX", "南非": "RSA", "韩国": "KOR", "捷克": "CZE",
    "加拿大": "CAN", "波黑": "BIH", "卡塔尔": "QAT", "瑞士": "SUI",
    "巴西": "BRA", "摩洛哥": "MAR", "海地": "HAI", "苏格兰": "SCO",
    "美国": "USA", "巴拉圭": "PAR", "澳大利亚": "AUS", "土耳其": "TUR",
    "德国": "GER", "库拉索": "CUW", "科特迪瓦": "CIV", "厄瓜多尔": "ECU",
    "荷兰": "NED", "日本": "JPN", "瑞典": "SWE", "突尼斯": "TUN",
    "比利时": "BEL", "埃及": "EGY", "伊朗": "IRN", "新西兰": "NZL",
    "西班牙": "ESP", "佛得角": "CPV", "沙特": "KSA", "乌拉圭": "URU",
    "法国": "FRA", "伊拉克": "IRQ", "塞内加尔": "SEN", "挪威": "NOR",
    "阿根廷": "ARG", "阿尔及利亚": "ALG", "奥地利": "AUT", "约旦": "JOR",
    "葡萄牙": "POR", "刚果金": "COD", "乌兹别克": "UZB", "哥伦比亚": "COL",
    "英格兰": "ENG", "克罗地亚": "CRO", "加纳": "GHA", "巴拿马": "PAN",
}

# Reverse mapping: abbreviation -> Chinese name
ABBR_TO_CN = {v: k for k, v in TEAM_ABBR.items()}

# Additional abbreviation variants
ABBR_VARIANTS = {
    "BIH": "波黑", "BOS": "波黑", "CUW": "库拉索", "CUR": "库拉索",
    "CIV": "科特迪瓦", "CRI": "科特迪瓦", "CPV": "佛得角", "CV": "佛得角",
    "COD": "刚果金", "DRC": "刚果金", "CGO": "刚果金",
    "NZL": "新西兰", "NZ": "新西兰", "KSA": "沙特", "SAU": "沙特",
    "JOR": "约旦",
    "UZB": "乌兹别克", "ENG": "英格兰", "SCO": "苏格兰",
    "RSA": "南非", "SA": "南非", "KOR": "韩国", "KR": "韩国",
    "IRN": "伊朗", "IRI": "伊朗", "TUN": "突尼斯",
}


def american_to_decimal(american):
    """Convert American moneyline to decimal odds."""
    if american > 0:
        return 1 + american / 100
    else:
        return 1 + 100 / abs(american)


def decimal_to_american(decimal_odds):
    """Convert decimal odds to American moneyline."""
    if decimal_odds <= 1:
        return None
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1) * 100)
    else:
        return round(-100 / (decimal_odds - 1))


def implied_from_american(american):
    """Convert American odds to implied probability."""
    if american > 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)


def normalize_probs(probs):
    """Normalize probabilities to sum to 1.0 (remove vig)."""
    total = sum(probs.values())
    if total <= 0:
        return probs
    return {k: v / total for k, v in probs.items()}


def get_strength_tiers():
    """Load team strength tiers."""
    with open(STRENGTH_FILE) as f:
        tiers = json.load(f)
    team_tier = {}
    for tier_name, teams in tiers.items():
        tier_num = int(tier_name.replace("tier", ""))
        for t in teams:
            team_tier[t] = tier_num
    return team_tier


def strength_prior_prob(home_tier, away_tier):
    """Calculate outcome probabilities from strength tier difference (same as index.html)."""
    diff = home_tier - away_tier
    h = math.exp(diff * 0.16)
    a = math.exp(-diff * 0.16)
    d = max(0.42, 0.64 - abs(diff) * 0.04)
    total = h + a + d
    return {"home": h / total, "draw": d / total, "away": a / total}


def resolve_team_abbr(abbr):
    """Resolve team abbreviation to Chinese name."""
    abbr = abbr.upper().strip()
    if abbr in ABBR_TO_CN:
        return ABBR_TO_CN[abbr]
    if abbr in ABBR_VARIANTS:
        return ABBR_VARIANTS[abbr]
    return None


def derive_odds_from_details(match, team_tiers):
    """
    Derive complete 3-way moneyline from partial data.
    We have: details (one team's American ML), drawML, overUnder.
    We need: homeML, drawML, awayML (all three American MLs).
    """
    odds = match.get("odds")
    if not odds:
        return None

    home_team = match["home"]
    away_team = match["away"]
    home_tier = team_tiers.get(home_team, 3)
    away_tier = team_tiers.get(away_team, 3)

    draw_ml = odds.get("drawML")
    details = odds.get("details", "")

    if draw_ml is None:
        return None

    # Parse details text: "CAN -120" or "USA +110" or "BRA -155"
    details_abbr = None
    details_american = None
    m = re.match(r'^([A-Z]{2,3})\s+([+-]\d+)', str(details))
    if m:
        details_abbr = m.group(1)
        details_american = int(m.group(2))

    if details_abbr is None or details_american is None:
        return None

    # Determine if the details team is home or away
    details_team_cn = resolve_team_abbr(details_abbr)
    details_side = None
    if details_team_cn == home_team:
        details_side = "home"
    elif details_team_cn == away_team:
        details_side = "away"
    else:
        # Try matching by common name fragments
        if details_abbr in ("USA", "US"):
            details_side = "home" if home_team == "美国" else "away"
        elif details_abbr in ("KOR", "KR"):
            details_side = "home" if home_team == "韩国" else "away"
        elif details_abbr in ("BIH", "BOS"):
            details_side = "home" if home_team == "波黑" else "away"
        elif details_abbr in ("CUW", "CUR"):
            details_side = "home" if home_team == "库拉索" else "away"
        else:
            # Default: assume details team is the favorite
            # If details_american is negative (favorite), assign to the stronger team
            if details_american < 0:
                if home_tier >= away_tier:
                    details_side = "home"
                else:
                    details_side = "away"
            else:
                if home_tier >= away_tier:
                    details_side = "away"
                else:
                    details_side = "home"

    if details_side is None:
        return None

    # Calculate probabilities
    details_prob = implied_from_american(details_american)
    draw_prob = implied_from_american(draw_ml)

    # Use strength prior to estimate the ratio between the two sides
    prior = strength_prior_prob(home_tier, away_tier)

    if details_side == "home":
        known_prob = details_prob
        known_prior = prior["home"]
        other_prior = prior["away"]
    else:
        known_prob = details_prob
        known_prior = prior["away"]
        other_prior = prior["home"]

    # Estimate the other side's probability proportional to the strength ratio
    if known_prior > 0:
        ratio = other_prior / known_prior
        other_prob = known_prob * ratio
    else:
        other_prob = (1 - details_prob - draw_prob) if (1 - details_prob - draw_prob) > 0 else 0.15

    # Ensure all probabilities are positive
    other_prob = max(0.05, other_prob)

    if details_side == "home":
        raw_probs = {"home": known_prob, "draw": draw_prob, "away": other_prob}
    else:
        raw_probs = {"home": other_prob, "draw": draw_prob, "away": known_prob}

    # Normalize to remove vig
    normalized = normalize_probs(raw_probs)

    # Convert back to decimal odds
    home_decimal = round(1 / normalized["home"], 3)
    draw_decimal = round(1 / normalized["draw"], 3)
    away_decimal = round(1 / normalized["away"], 3)

    # Convert to American
    home_american = decimal_to_american(home_decimal)
    draw_american = decimal_to_american(draw_decimal)
    away_american = decimal_to_american(away_decimal)

    return {
        "provider": odds.get("provider", "DraftKings"),
        "method": "derived_from_partial",
        "home_decimal": home_decimal,
        "draw_decimal": draw_decimal,
        "away_decimal": away_decimal,
        "home_moneyline_american": home_american,
        "draw_moneyline_american": draw_american,
        "away_moneyline_american": away_american,
        "home_raw_implied_probability": round(normalized["home"], 4),
        "draw_raw_implied_probability": round(normalized["draw"], 4),
        "away_raw_implied_probability": round(normalized["away"], 4),
        "over_under_goals": odds.get("overUnder"),
        "original_details": details,
        "confidence": "medium",
        "source_type": "derived",
    }


def main():
    with open(MATCH_FILE) as f:
        matches = json.load(f)

    team_tiers = get_strength_tiers()

    # Only process group stage
    group_matches = {mid: m for mid, m in matches.items() if m.get("stage") == "group"}
    print(f"[odds] Processing {len(group_matches)} group matches")

    result = {}
    stats = {"complete": 0, "derived": 0, "completed_match": 0, "no_data": 0, "failed": 0}

    for mid, match in sorted(group_matches.items(), key=lambda x: x[1].get("date", "")):
        home = match["home"]
        away = match["away"]

        # Skip completed matches
        if match.get("completed"):
            result[mid] = {
                "match_id": mid,
                "home_team_cn": home,
                "away_team_cn": away,
                "odds": None,
                "confidence": "high",
                "source_type": "unavailable",
                "notes": "Match already completed",
            }
            stats["completed_match"] += 1
            continue

        # Try to derive complete odds
        derived = derive_odds_from_details(match, team_tiers)
        if derived:
            result[mid] = {
                "match_id": mid,
                "home_team_cn": home,
                "away_team_cn": away,
                "odds": derived,
                "as_of": date.today().isoformat(),
                "confidence": "medium",
                "source_type": "derived",
                "notes": (
                    "Model-derived 1X2 completion from ESPN/DraftKings partial "
                    f"market data: {derived['original_details']}"
                ),
            }
            stats["derived"] += 1
        else:
            result[mid] = {
                "match_id": mid,
                "home_team_cn": home,
                "away_team_cn": away,
                "odds": None,
                "confidence": "low",
                "source_type": "missing",
                "notes": "No usable odds data",
            }
            stats["no_data"] += 1

    print(f"\n[odds] Results:")
    print(f"  Completed matches (no odds needed): {stats['completed_match']}")
    print(f"  Derived from partial data: {stats['derived']}")
    print(f"  No data available: {stats['no_data']}")
    print(f"  Total: {len(result)}")

    # Validation
    for mid, entry in result.items():
        if entry["odds"]:
            o = entry["odds"]
            # Check decimal odds > 1
            for side in ("home_decimal", "draw_decimal", "away_decimal"):
                val = o.get(side)
                if val is not None:
                    assert val > 1.0, f"{mid} {side} = {val} <= 1.0"
            # Check probabilities sum ≈ 1
            prob_sum = sum(filter(None, [
                o.get("home_raw_implied_probability"),
                o.get("draw_raw_implied_probability"),
                o.get("away_raw_implied_probability"),
            ]))
            if prob_sum > 0:
                assert 0.90 <= prob_sum <= 1.10, f"{mid} prob sum = {prob_sum}"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
