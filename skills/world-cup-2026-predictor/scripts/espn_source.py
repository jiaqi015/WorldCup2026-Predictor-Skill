#!/usr/bin/env python3
"""Normalize ESPN's World Cup scoreboard feed into the skill contract."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None


RESULTS_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    "fifa.world/scoreboard?dates=20260611-20260719&limit=200"
)
USER_AGENT = "world-cup-2026-predictor-skill/1.1"
CONTRACT_VERSION = 1

STAGES = {
    13802: "Group",
    13801: "Round of 32",
    13800: "Round of 16",
    13799: "Quarterfinal",
    13798: "Semifinal",
    13797: "Third place",
    13803: "Final",
}

TEAM_ALIASES = {
    "USA": "美国",
    "United States": "美国",
    "Bosnia-Herzegovina": "波黑",
    "Bosnia and Herzegovina": "波黑",
    "Czechia": "捷克",
    "Czech Republic": "捷克",
    "Turkey": "土耳其",
    "Türkiye": "土耳其",
    "Curacao": "库拉索",
    "Curaçao": "库拉索",
    "Ivory Coast": "科特迪瓦",
    "Côte d'Ivoire": "科特迪瓦",
    "Cape Verde": "佛得角",
    "DR Congo": "刚果金",
    "Congo DR": "刚果金",
}


def fetch_payload(timeout: float = 15, url: str = RESULTS_API) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def resolve_timezone(name: str | None):
    if not name:
        return datetime.now().astimezone().tzinfo or timezone.utc
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def extract_js_value(source: str, name: str) -> str:
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


def default_app_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "predictor" / "index.html"


def load_team_aliases(app_path: Path | None = None) -> dict[str, str]:
    aliases = dict(TEAM_ALIASES)
    path = app_path or default_app_path()
    if not path.is_file():
        return aliases
    source = path.read_text(encoding="utf-8")
    try:
        team_en = json.loads(extract_js_value(source, "TEAM_EN"))
    except (ValueError, json.JSONDecodeError):
        return aliases
    for cn_name, en_name in team_en.items():
        aliases[str(cn_name)] = str(cn_name)
        aliases[str(en_name)] = str(cn_name)
    return aliases


def _first_competition(event: dict) -> dict | None:
    competitions = event.get("competitions") or []
    return competitions[0] if competitions else None


def _team_name(competitor: dict | None) -> str | None:
    if not competitor:
        return None
    team = competitor.get("team") or {}
    return (
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or team.get("abbreviation")
    )


def _score(competitor: dict | None):
    if not competitor:
        return None
    score = competitor.get("score")
    if score is None:
        return None
    try:
        return int(score)
    except (TypeError, ValueError):
        return score


def _venue(competition: dict) -> dict | None:
    venue = competition.get("venue") or {}
    if not venue:
        return None
    address = venue.get("address") or {}
    return {
        "name": venue.get("fullName") or venue.get("name"),
        "city": address.get("city"),
        "country": address.get("country"),
    }


def normalize_event(event: dict) -> dict | None:
    competition = _first_competition(event)
    if not competition:
        return None

    competitors = competition.get("competitors") or []
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    status = ((competition.get("status") or {}).get("type") or {})
    stage_id = (event.get("season") or {}).get("type")
    event_time = parse_time(event.get("date"))
    return {
        "id": event.get("id"),
        "date": event.get("date"),
        "stage_id": stage_id,
        "stage": STAGES.get(stage_id, f"Stage {stage_id}"),
        "completed": bool(status.get("completed")),
        "status": status.get("shortDetail") or status.get("description"),
        "status_name": status.get("name"),
        "home": _team_name(home),
        "away": _team_name(away),
        "home_score": _score(home),
        "away_score": _score(away),
        "venue": _venue(competition),
        "sort_time": event_time.isoformat() if event_time else "",
    }


def event_local_date(event: dict, timezone_name: str | None = None) -> date | None:
    event_time = parse_time(event.get("date"))
    if not event_time:
        return None
    return event_time.astimezone(resolve_timezone(timezone_name)).date()


def filter_completed_on_date(
    events: list[dict],
    target_date: date,
    timezone_name: str | None = None,
) -> list[dict]:
    return [
        event
        for event in events
        if event.get("completed") and event_local_date(event, timezone_name) == target_date
    ]


def find_mapping_issues(events: list[dict], aliases: dict[str, str]) -> list[dict]:
    issues = []
    for event in events:
        for side in ("home", "away"):
            name = event.get(side)
            if name and not is_placeholder_team(name) and name not in aliases:
                issues.append(
                    {
                        "event_id": event.get("id"),
                        "side": side,
                        "team": name,
                        "date": event.get("date"),
                        "stage": event.get("stage"),
                    }
                )
    return issues


def is_placeholder_team(name: str) -> bool:
    normalized = name.strip()
    return (
        normalized.startswith("Group ")
        or normalized.startswith("Third Place Group")
        or normalized.startswith("Semifinal ")
        or normalized.endswith(" Winner")
        or normalized.endswith(" 2nd Place")
        or normalized.endswith(" Loser")
    )


def build_contract(
    payload: dict,
    *,
    now: datetime | None = None,
    upcoming_limit: int = 5,
    aliases: dict[str, str] | None = None,
) -> dict:
    fetched_at = now or datetime.now(timezone.utc)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    events = [
        item
        for raw_event in payload.get("events", [])
        if (item := normalize_event(raw_event))
    ]
    events.sort(key=lambda item: item.get("date") or "")
    completed = [event for event in events if event.get("completed")]
    upcoming = [
        event
        for event in events
        if not event.get("completed")
        and (event_time := parse_time(event.get("date")))
        and event_time >= fetched_at
    ][: max(upcoming_limit, 0)]

    known_aliases = aliases if aliases is not None else load_team_aliases()
    return {
        "contract_version": CONTRACT_VERSION,
        "source": "ESPN",
        "source_url": RESULTS_API,
        "fetched_at": fetched_at.isoformat(),
        "scheduled_count": len(events),
        "completed_count": len(completed),
        "events": events,
        "completed": completed,
        "upcoming": upcoming,
        "mapping_issues": find_mapping_issues(events, known_aliases),
    }
