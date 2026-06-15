#!/usr/bin/env python3
"""
Collect post-match analysis data from ESPN Core API for all completed matches.

Reads:  data/matches/match_schedule.json, data/matches/match_details.json
Outputs: data/analysis/match_xg.json
         data/analysis/match_momentum.json
         data/analysis/match_team_stats.json
         data/analysis/xg_aggregates.json   (cross-match player/team xG leaderboards)

Each data type is collected independently — failure of one type does not block others.

Usage:
    python3 scripts/fetch_analysis_data.py                 # All completed matches
    python3 scripts/fetch_analysis_data.py --match-id 760415  # Single match (debug)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

# ─── Constants ────────────────────────────────────────────────────────

CORE_ROOT = (
    "https://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world"
)
PLAYS_URL_TPL = (
    CORE_ROOT + "/events/{EV}/competitions/{EV}/plays?limit=1000&page={PAGE}"
)
MOMENTUM_URL_TPL = (
    CORE_ROOT + "/events/{EV}/competitions/{EV}/momentum?limit=300"
)
COMPETITORS_URL_TPL = (
    CORE_ROOT + "/events/{EV}/competitions/{EV}/competitors?limit=2"
)

SHOT_TYPES = {
    "shot-on-target",
    "shot-off-target",
    "shot-blocked",
    "shot-hit-woodwork",
    "goal",
    "goal---header",
    "own-goal",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")

# ─── Team CN mapping (replicated from fetch_match_details.py) ─────────

TEAM_CN = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国",
    "Czech Republic": "捷克", "Czechia": "捷克", "Canada": "加拿大",
    "Bosnia and Herzegovina": "波黑", "Bosnia-Herzegovina": "波黑",
    "Qatar": "卡塔尔", "Switzerland": "瑞士", "Brazil": "巴西",
    "Morocco": "摩洛哥", "Haiti": "海地", "Scotland": "苏格兰",
    "United States": "美国", "USA": "美国", "Paraguay": "巴拉圭",
    "Australia": "澳大利亚", "Türkiye": "土耳其", "Turkey": "土耳其",
    "Germany": "德国", "Curaçao": "库拉索", "Curacao": "库拉索",
    "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦",
    "Ecuador": "厄瓜多尔", "Netherlands": "荷兰", "Japan": "日本",
    "Sweden": "瑞典", "Tunisia": "突尼斯", "Belgium": "比利时",
    "Egypt": "埃及", "Iran": "伊朗", "New Zealand": "新西兰",
    "Spain": "西班牙", "Cape Verde": "佛得角", "Saudi Arabia": "沙特",
    "Uruguay": "乌拉圭", "France": "法国", "Iraq": "伊拉克",
    "Senegal": "塞内加尔", "Norway": "挪威", "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦",
    "Portugal": "葡萄牙", "DR Congo": "刚果金", "Congo DR": "刚果金",
    "Uzbekistan": "乌兹别克", "Colombia": "哥伦比亚", "England": "英格兰",
    "Croatia": "克罗地亚", "Ghana": "加纳", "Panama": "巴拿马",
}

# ─── Player resolution (replicated from fetch_match_details.py) ───────

PLAYER_DATA = {}
PLAYER_DATA_NORMALIZED = {}

PLAYER_DISPLAY_CN = {
    "Julián Quiñones": "胡利安·基尼奥内斯",
    "Érik Lira": "埃里克·利拉",
    "Raúl Jiménez": "劳尔·希门尼斯",
    "Roberto Alvarado": "罗伯托·阿尔瓦拉多",
    "Ladislav Krejcí": "拉迪斯拉夫·克雷伊奇",
    "Ladislav Krejčí": "拉迪斯拉夫·克雷伊奇",
    "Vladimír Coufal": "弗拉迪米尔·曹法尔",
    "Hwang In-Beom": "黄仁范",
    "Lee Kang-In": "李刚仁",
    "Oh Hyeon-Gyu": "吴贤揆",
}


def normalize_name(value):
    """Normalize accents and punctuation for conservative alias matching."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char.lower() for char in value if char.isalnum())


def load_player_mapping():
    """Load player name mapping from JSON file."""
    global PLAYER_DATA, PLAYER_DATA_NORMALIZED
    mapping_path = os.path.join(DATA_DIR, "squads", "player_mapping.json")
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for eng_name, info in data.items():
                if isinstance(info, str):
                    info = {"cn": info}
                if not isinstance(info, dict):
                    continue
                PLAYER_DATA[eng_name] = info
                PLAYER_DATA_NORMALIZED.setdefault(
                    normalize_name(eng_name), []
                ).append((eng_name, info))


def resolve_player(source_name, expected_team):
    """Resolve an ESPN player name against the project mapping within one team."""
    display_cn = PLAYER_DISPLAY_CN.get(source_name)
    candidates = []
    if source_name in PLAYER_DATA:
        candidates.append((source_name, PLAYER_DATA[source_name]))
    candidates.extend(
        PLAYER_DATA_NORMALIZED.get(normalize_name(source_name), [])
    )

    seen = set()
    for mapped_name, info in candidates:
        candidate_key = (mapped_name, info.get("team"))
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        if info.get("team") != expected_team:
            continue
        alias = info.get("cn") or source_name
        return {
            "source_name": source_name,
            "display_name_cn": display_cn or alias,
            "app_alias": alias,
            "team_cn": expected_team,
        }

    return {
        "source_name": source_name,
        "display_name_cn": display_cn or source_name,
        "app_alias": None,
        "team_cn": expected_team,
    }


# ─── Utilities ────────────────────────────────────────────────────────


def fetch_json(url):
    """Fetch JSON from URL with retry logic (3 attempts, 2s backoff)."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
                return None
    return None


def extract_id_from_ref(ref_url, entity):
    """Extract numeric ID from an ESPN $ref URL.

    entity: e.g. "teams", "competitors", "athletes"
    Returns the numeric ID string, or None.
    """
    if not ref_url:
        return None
    m = re.search(rf"/{entity}/(\d+)", ref_url)
    return m.group(1) if m else None


_ACTION_KEYWORDS = (" Shot", " Own", " Goal")


def parse_player_name_from_short_text(play):
    """Extract player name from ESPN play's shortText field.

    ESPN shortText format: "{Player Name} {Action}"
    e.g. "Brian Gutiérrez Shot Blocked", "Julián Quiñones Goal",
         "Damián Bobadilla Own Goal", "Raúl Jiménez Goal - Header"
    Note: ESPN truncates shortText at 32 chars, so long action suffixes
    may be incomplete. We split at the first action keyword instead of
    matching exact suffixes.
    Returns the player name, or None.
    """
    short_text = play.get("shortText", "")
    if not short_text:
        return None
    for keyword in _ACTION_KEYWORDS:
        idx = short_text.find(keyword)
        if idx > 0:
            name = short_text[:idx].strip()
            if name:
                return name
    return None


def load_existing(path):
    """Load existing JSON file, return empty dict if missing."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    """Write JSON file atomically (write-to-tmp then replace)."""
    import tempfile
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)  # atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─── Competitor resolution ────────────────────────────────────────────


def resolve_competitor_ids(match_id):
    """Fetch competitors for a match. Return shared map or None on failure.

    Returns:
        {
            "home_team_id": str,
            "away_team_id": str,
            "home_stats_ref": str (URL),
            "away_stats_ref": str (URL),
        }
    """
    url = COMPETITORS_URL_TPL.format(EV=match_id)
    data = fetch_json(url)
    if not isinstance(data, dict) or "items" not in data:
        return None

    result = {}
    for comp in data["items"]:
        side = comp.get("homeAway", "")
        team_ref = (comp.get("team") or {}).get("$ref", "")
        stats_ref = (comp.get("statistics") or {}).get("$ref", "")
        team_id = extract_id_from_ref(team_ref, "teams")
        if not team_id:
            continue

        if side == "home":
            result["home_team_id"] = team_id
            result["home_stats_ref"] = stats_ref
        elif side == "away":
            result["away_team_id"] = team_id
            result["away_stats_ref"] = stats_ref

    if "home_team_id" not in result or "away_team_id" not in result:
        return None
    return result


# ─── Collector: xG (plays endpoint) ───────────────────────────────────


def collect_xg(match_id, home_cn, away_cn, home_team_id, away_team_id):
    """Collect xG/shot data from plays endpoint. Returns dict or None."""
    all_plays = []
    page = 1
    while True:
        url = PLAYS_URL_TPL.format(EV=match_id, PAGE=page)
        data = fetch_json(url)
        if not isinstance(data, dict) or "items" not in data:
            if page == 1:
                return None
            break
        all_plays.extend(data["items"])
        page_count = data.get("pageCount", 1)
        if page >= page_count:
            break
        page += 1

    shots = []
    for play in all_plays:
        play_type = (play.get("type") or {}).get("type", "")
        has_xg = "expectedGoals" in play
        if play_type not in SHOT_TYPES and not has_xg:
            continue

        # Determine side from team $ref
        team_ref = (play.get("team") or {}).get("$ref", "")
        team_id = extract_id_from_ref(team_ref, "teams")
        if team_id == home_team_id:
            side, side_cn = "home", home_cn
        elif team_id == away_team_id:
            side, side_cn = "away", away_cn
        else:
            continue

        # Player name: extract from shortText ("{Name} {Action}" format)
        shooter_name = parse_player_name_from_short_text(play)

        shooter_info = None
        if shooter_name:
            shooter_info = resolve_player(shooter_name, side_cn)

        entry = {
            "play_id": play.get("id", ""),
            "type": play_type,
            "team": side,
            "team_cn": side_cn,
            "minute": (play.get("clock") or {}).get("displayValue", ""),
            "period": (play.get("period") or {}).get("number", 0),
            "xg": play.get("expectedGoals"),
            "xgot": play.get("expectedGoalsOnTarget"),
            "result": "goal" if play.get("scoringPlay") else play_type,
            "text": play.get("text", ""),
            "distance": play.get("statYardage"),
            "body_part": (play.get("contactType") or {}).get("text"),
            "penalty_kick": play.get("penaltyKick", False),
            "own_goal": play.get("ownGoal", False),
            "shooter_source_name": (
                shooter_info["source_name"] if shooter_info else None
            ),
            "shooter_cn": (
                shooter_info["display_name_cn"] if shooter_info else None
            ),
            "shooter_team_cn": shooter_info["team_cn"] if shooter_info else None,
        }
        shots.append(entry)

    # Aggregate xG
    home_xg = sum(
        s["xg"] for s in shots if s["team"] == "home" and s["xg"] is not None
    )
    away_xg = sum(
        s["xg"] for s in shots if s["team"] == "away" and s["xg"] is not None
    )
    home_count = sum(1 for s in shots if s["team"] == "home")
    away_count = sum(1 for s in shots if s["team"] == "away")
    scoring_count = sum(1 for s in shots if s["result"] == "goal")

    return {
        "matchId": match_id,
        "homeTeamCn": home_cn,
        "awayTeamCn": away_cn,
        "team_xg": {"home": round(home_xg, 3), "away": round(away_xg, 3)},
        "total_shots": {"home": home_count, "away": away_count},
        "scoring_plays_count": scoring_count,
        "shots": shots,
    }


# ─── Collector: momentum ──────────────────────────────────────────────


def collect_momentum(match_id, home_cn, away_cn, home_team_id, away_team_id):
    """Collect scoring-threat timeline from momentum endpoint. Returns dict or None."""
    url = MOMENTUM_URL_TPL.format(EV=match_id)
    data = fetch_json(url)
    if not isinstance(data, dict) or "items" not in data:
        return None

    timeline = []
    for item in data["items"]:
        comp_ref = (item.get("competitor") or {}).get("$ref", "")
        comp_id = extract_id_from_ref(comp_ref, "competitors")
        if comp_id == home_team_id:
            side = "home"
        elif comp_id == away_team_id:
            side = "away"
        else:
            continue

        timeline.append({
            "clock": item.get("displayClock", ""),
            "period": item.get("period", 0),
            "threat": item.get("probability", 0),
            "team": side,
        })

    if len(timeline) >= 300:
        print(
            f"  WARNING: momentum data may be truncated at {len(timeline)} items",
            file=sys.stderr,
        )

    return {
        "matchId": match_id,
        "homeTeamCn": home_cn,
        "awayTeamCn": away_cn,
        "item_count": len(timeline),
        "timeline": timeline,
    }


# ─── Collector: team stats ────────────────────────────────────────────


def _parse_stats_categories(data):
    """Parse splits.categories[] into a structured dict."""
    result = {}
    categories = (data.get("splits") or {}).get("categories", [])
    for cat in categories:
        cat_name = cat.get("name", "unknown")
        stats_list = []
        for stat in cat.get("stats", []):
            stats_list.append({
                "name": stat.get("name", ""),
                "displayName": stat.get("displayName", ""),
                "value": stat.get("value"),
                "displayValue": stat.get("displayValue", ""),
                "description": stat.get("description", ""),
            })
        result[cat_name] = stats_list
    return result


def collect_stats(match_id, home_cn, away_cn, home_stats_ref, away_stats_ref):
    """Collect per-team statistics via $ref chain. Returns dict or None."""
    home_data = fetch_json(home_stats_ref) if home_stats_ref else None
    away_data = fetch_json(away_stats_ref) if away_stats_ref else None

    if not home_data and not away_data:
        return None

    home_stats = _parse_stats_categories(home_data) if home_data else {}
    away_stats = _parse_stats_categories(away_data) if away_data else {}

    return {
        "matchId": match_id,
        "homeTeamCn": home_cn,
        "awayTeamCn": away_cn,
        "stats": {
            "home": home_stats,
            "away": away_stats,
        },
    }


# ─── Cross-match aggregation ──────────────────────────────────────────


def build_xg_aggregates(xg_by_match, match_details):
    """Build cross-match player and team xG leaderboards from per-match data.

    Returns {"player_xg": [...], "team_aggregate": [...]}.
    - player_xg: per shooter (source_name + team), sorted by xg_total desc.
      Own goals are excluded from a player's personal goal count.
    - team_aggregate: per team, xg for/against and goals for/against,
      sorted by xg_for desc. Goals come from match_details scorelines.
    """
    players = {}
    teams = {}

    for match_id, m in xg_by_match.items():
        # Skip non-match entries defensively.
        if not isinstance(m, dict) or "shots" not in m:
            continue

        # Player aggregation
        for shot in m.get("shots", []):
            name = shot.get("shooter_source_name")
            if not name:
                continue
            team_cn = shot.get("shooter_team_cn") or shot.get("team_cn")
            key = (name, team_cn)
            p = players.setdefault(key, {
                "player_source": name,
                "player_app_alias": shot.get("shooter_cn"),
                "team_cn": team_cn,
                "shots": 0,
                "xg_total": 0.0,
                "xgot_total": 0.0,
                "goals": 0,
            })
            p["shots"] += 1
            if shot.get("xg") is not None:
                p["xg_total"] += shot["xg"]
            if shot.get("xgot") is not None:
                p["xgot_total"] += shot["xgot"]
            if shot.get("result") == "goal" and not shot.get("own_goal"):
                p["goals"] += 1

        # Team aggregation (goals from authoritative scoreline)
        detail = match_details.get(match_id, {})
        home_cn = m.get("homeTeamCn")
        away_cn = m.get("awayTeamCn")
        team_xg = m.get("team_xg", {})
        home_score = detail.get("homeScore", 0)
        away_score = detail.get("awayScore", 0)

        for side, opp in (("home", "away"), ("away", "home")):
            team_cn = home_cn if side == "home" else away_cn
            if not team_cn:
                continue
            t = teams.setdefault(team_cn, {
                "team_cn": team_cn,
                "matches": 0,
                "xg_for": 0.0,
                "xg_against": 0.0,
                "goals_for": 0,
                "goals_against": 0,
            })
            t["matches"] += 1
            t["xg_for"] += team_xg.get(side, 0) or 0
            t["xg_against"] += team_xg.get(opp, 0) or 0
            if side == "home":
                t["goals_for"] += home_score
                t["goals_against"] += away_score
            else:
                t["goals_for"] += away_score
                t["goals_against"] += home_score

    player_xg = []
    for p in players.values():
        p["xg_total"] = round(p["xg_total"], 3)
        p["xgot_total"] = round(p["xgot_total"], 3)
        p["xg_overperformance"] = round(p["goals"] - p["xg_total"], 2)
        player_xg.append(p)
    player_xg.sort(key=lambda x: x["xg_total"], reverse=True)

    team_aggregate = []
    for t in teams.values():
        t["xg_for"] = round(t["xg_for"], 3)
        t["xg_against"] = round(t["xg_against"], 3)
        team_aggregate.append(t)
    team_aggregate.sort(key=lambda x: x["xg_for"], reverse=True)

    return {"player_xg": player_xg, "team_aggregate": team_aggregate}


# ─── Validation ───────────────────────────────────────────────────────


def validate_xg_reconciliation(xg_data, match_detail):
    """Compare scoring_plays_count against known score. Warning only."""
    if not xg_data or not match_detail:
        return True, ""
    expected = match_detail.get("homeScore", 0) + match_detail.get("awayScore", 0)
    actual = xg_data.get("scoring_plays_count", 0)
    if actual != expected:
        msg = (
            f"xG reconciliation: {actual} scoring plays vs "
            f"{expected} expected goals "
            f"({match_detail.get('homeTeamCn')} {match_detail.get('homeScore')}-"
            f"{match_detail.get('awayScore')} {match_detail.get('awayTeamCn')})"
        )
        return False, msg
    return True, ""


# ─── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Collect post-match analysis data from ESPN Core API."
    )
    parser.add_argument(
        "--match-id",
        help="Process a single match by ESPN event ID (e.g. 760415).",
    )
    args = parser.parse_args()

    # Load player mapping
    load_player_mapping()
    if PLAYER_DATA:
        print(f"Loaded {len(PLAYER_DATA)} player name mappings")

    # Load match schedule
    schedule_path = os.path.join(DATA_DIR, "matches", "match_schedule.json")
    if not os.path.exists(schedule_path):
        print(
            "match_schedule.json not found. Run fetch_match_data.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(schedule_path, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    # Load match_details for xG reconciliation
    details_path = os.path.join(DATA_DIR, "matches", "match_details.json")
    match_details = load_existing(details_path)

    # Determine target matches
    if args.match_id:
        entry = schedule.get(args.match_id)
        if not entry:
            print(f"Match {args.match_id} not found in schedule.", file=sys.stderr)
            sys.exit(1)
        if not entry.get("completed"):
            print(f"Match {args.match_id} is not completed yet.", file=sys.stderr)
            sys.exit(1)
        targets = [entry]
    else:
        targets = [m for m in schedule.values() if m.get("completed")]

    print(f"Collecting analysis data for {len(targets)} completed matches...")

    # Ensure output directory
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Load existing outputs (incremental)
    xg_path = os.path.join(ANALYSIS_DIR, "match_xg.json")
    momentum_path = os.path.join(ANALYSIS_DIR, "match_momentum.json")
    stats_path = os.path.join(ANALYSIS_DIR, "match_team_stats.json")
    existing_xg = load_existing(xg_path)
    existing_momentum = load_existing(momentum_path)
    existing_stats = load_existing(stats_path)

    new_xg = dict(existing_xg)
    new_momentum = dict(existing_momentum)
    new_stats = dict(existing_stats)

    fetched = 0
    skipped = 0
    for i, match in enumerate(targets, 1):
        match_id = match["id"]
        home_cn = match["home"]
        away_cn = match["away"]

        # Incremental skip: if all three exist, skip
        if (
            match_id in existing_xg
            and match_id in existing_momentum
            and match_id in existing_stats
        ):
            skipped += 1
            print(
                f"[{i}/{len(targets)}] {home_cn} vs {away_cn} ({match_id}) "
                f"- already collected, skipping"
            )
            continue

        print(f"\n[{i}/{len(targets)}] {home_cn} vs {away_cn} ({match_id})")

        # Resolve competitors (shared)
        comp_ids = resolve_competitor_ids(match_id)
        if not comp_ids:
            print("  Failed to resolve competitors, skipping match")
            continue

        home_team_id = comp_ids["home_team_id"]
        away_team_id = comp_ids["away_team_id"]

        # Collector 1: xG
        xg_data = None
        try:
            xg_data = collect_xg(
                match_id, home_cn, away_cn, home_team_id, away_team_id
            )
            if xg_data:
                new_xg[match_id] = xg_data
                hx = xg_data["team_xg"]["home"]
                ax = xg_data["team_xg"]["away"]
                ts = xg_data["total_shots"]
                print(
                    f"  xG: home={hx:.3f}, away={ax:.3f} "
                    f"({ts['home']}+{ts['away']} shots)"
                )
        except Exception as e:
            print(f"  xG collection failed: {e}", file=sys.stderr)

        # Collector 2: momentum
        momentum_data = None
        try:
            momentum_data = collect_momentum(
                match_id, home_cn, away_cn, home_team_id, away_team_id
            )
            if momentum_data:
                new_momentum[match_id] = momentum_data
                print(f"  Momentum: {momentum_data['item_count']} data points")
        except Exception as e:
            print(f"  Momentum collection failed: {e}", file=sys.stderr)

        # Collector 3: stats
        try:
            stats_data = collect_stats(
                match_id,
                home_cn,
                away_cn,
                comp_ids.get("home_stats_ref"),
                comp_ids.get("away_stats_ref"),
            )
            if stats_data:
                new_stats[match_id] = stats_data
                home_cats = len(stats_data["stats"].get("home", {}))
                away_cats = len(stats_data["stats"].get("away", {}))
                print(f"  Stats: {home_cats}+{away_cats} categories")
        except Exception as e:
            print(f"  Stats collection failed: {e}", file=sys.stderr)

        # xG reconciliation (warning only)
        detail = match_details.get(match_id)
        if xg_data and detail:
            ok, msg = validate_xg_reconciliation(xg_data, detail)
            if not ok:
                print(f"  WARNING: {msg}", file=sys.stderr)

        fetched += 1
        time.sleep(1)

    # Save outputs
    save_json(xg_path, new_xg)
    save_json(momentum_path, new_momentum)
    save_json(stats_path, new_stats)

    # Cross-match aggregates (recomputed from full per-match set every run)
    aggregates_path = os.path.join(ANALYSIS_DIR, "xg_aggregates.json")
    aggregates = build_xg_aggregates(new_xg, match_details)
    aggregates_out = {
        "generated_at": time.strftime("%Y-%m-%d"),
        "source": "Aggregated from data/analysis/match_xg.json + match scorelines",
        "matches_aggregated": len(new_xg),
        "player_xg": aggregates["player_xg"],
        "team_aggregate": aggregates["team_aggregate"],
    }
    save_json(aggregates_path, aggregates_out)

    print(f"\nSaved match_xg.json ({len(new_xg)} matches)")
    print(f"Saved match_momentum.json ({len(new_momentum)} matches)")
    print(f"Saved match_team_stats.json ({len(new_stats)} matches)")
    print(
        f"Saved xg_aggregates.json "
        f"({len(aggregates['player_xg'])} players, "
        f"{len(aggregates['team_aggregate'])} teams)"
    )
    if skipped:
        print(f"Skipped {skipped} already-collected matches")
    print("Done.")


if __name__ == "__main__":
    main()
