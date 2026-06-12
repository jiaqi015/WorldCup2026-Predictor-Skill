#!/usr/bin/env python3
"""Fetch current 2026 World Cup results from ESPN's public scoreboard feed."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RESULTS_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    "fifa.world/scoreboard?dates=20260611-20260719&limit=200"
)
STAGES = {
    13802: "Group",
    13801: "Round of 32",
    13800: "Round of 16",
    13799: "Quarterfinal",
    13798: "Semifinal",
    13797: "Third place",
    13803: "Final",
}


def fetch_payload(timeout: float) -> dict:
    request = Request(
        RESULTS_API,
        headers={"User-Agent": "world-cup-2026-predictor-skill/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_event(event: dict) -> dict | None:
    competition = (event.get("competitions") or [None])[0]
    if not competition:
        return None

    competitors = competition.get("competitors") or []
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    status = ((competition.get("status") or {}).get("type") or {})
    season_type = (event.get("season") or {}).get("type")
    return {
        "id": event.get("id"),
        "date": event.get("date"),
        "stage": STAGES.get(season_type, f"Stage {season_type}"),
        "completed": bool(status.get("completed")),
        "status": status.get("shortDetail") or status.get("description"),
        "home": (home.get("team") or {}).get("displayName"),
        "away": (away.get("team") or {}).get("displayName"),
        "home_score": home.get("score"),
        "away_score": away.get("score"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--upcoming", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    try:
        payload = fetch_payload(args.timeout)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Unable to fetch ESPN results: {exc}", file=sys.stderr)
        return 1

    events = [item for event in payload.get("events", []) if (item := normalize_event(event))]
    events.sort(key=lambda item: item.get("date") or "")
    completed = [event for event in events if event["completed"]]
    now = datetime.now(timezone.utc)
    upcoming = [
        event
        for event in events
        if not event["completed"]
        and (event_time := parse_time(event["date"]))
        and event_time >= now
    ][: max(args.upcoming, 0)]

    result = {
        "source": "ESPN",
        "fetched_at": now.isoformat(),
        "scheduled_count": len(events),
        "completed_count": len(completed),
        "completed": completed,
        "upcoming": upcoming,
    }

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(
        f"ESPN World Cup feed: {len(completed)} completed / "
        f"{len(events)} scheduled matches"
    )
    for event in completed:
        print(
            f"- {event['date']} | {event['stage']} | "
            f"{event['home']} {event['home_score']}-{event['away_score']} "
            f"{event['away']}"
        )
    if upcoming:
        print("Upcoming:")
        for event in upcoming:
            print(
                f"- {event['date']} | {event['stage']} | "
                f"{event['home']} vs {event['away']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
