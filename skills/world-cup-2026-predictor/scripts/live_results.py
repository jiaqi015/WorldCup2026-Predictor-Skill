#!/usr/bin/env python3
"""Query ESPN-backed 2026 World Cup live-result views for the skill."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError

from espn_source import (
    build_contract,
    fetch_payload,
    filter_completed_on_date,
    parse_date,
    resolve_timezone,
)


def format_event(event: dict, *, completed: bool = False) -> str:
    if completed:
        return (
            f"- {event['date']} | {event['stage']} | "
            f"{event['home']} {event['home_score']}-{event['away_score']} "
            f"{event['away']}"
        )
    return f"- {event['date']} | {event['stage']} | {event['home']} vs {event['away']}"


def selected_payload(contract: dict, args: argparse.Namespace) -> dict:
    result = {
        "contract_version": contract["contract_version"],
        "source": contract["source"],
        "source_url": contract["source_url"],
        "fetched_at": contract["fetched_at"],
        "scheduled_count": contract["scheduled_count"],
        "completed_count": contract["completed_count"],
        "mode": args.mode,
    }
    if args.mode == "today":
        target = parse_date(args.date) if args.date else datetime.now(resolve_timezone(args.timezone)).date()
        result["date"] = target.isoformat()
        result["timezone"] = args.timezone
        result["today_completed"] = filter_completed_on_date(
            contract["events"],
            target,
            args.timezone,
        )
    elif args.mode == "upcoming":
        result["selected"] = contract["upcoming"]
    elif args.mode == "mapping":
        result["selected"] = contract["mapping_issues"]
    elif args.mode == "all":
        result["selected"] = contract["events"]
    else:
        result["completed"] = contract["completed"]
        result["upcoming"] = contract["upcoming"]
    return result


def print_text_view(contract: dict, args: argparse.Namespace) -> None:
    print(
        f"ESPN World Cup feed: {contract['completed_count']} completed / "
        f"{contract['scheduled_count']} scheduled matches"
    )
    print(f"Fetched at: {contract['fetched_at']}")

    if args.mode == "today":
        target = parse_date(args.date) if args.date else datetime.now(resolve_timezone(args.timezone)).date()
        events = filter_completed_on_date(contract["events"], target, args.timezone)
        print(f"Completed on {target.isoformat()} ({args.timezone}): {len(events)}")
        for event in events:
            print(format_event(event, completed=True))
        return

    if args.mode == "upcoming":
        print("Upcoming:")
        for event in contract["upcoming"]:
            print(format_event(event))
        return

    if args.mode == "mapping":
        issues = contract["mapping_issues"]
        if not issues:
            print("No ESPN team mapping issues found.")
            return
        print(f"ESPN team mapping issues: {len(issues)}")
        for issue in issues:
            print(
                f"- {issue['event_id']} | {issue['stage']} | "
                f"{issue['side']} team {issue['team']}"
            )
        return

    events = contract["events"] if args.mode == "all" else contract["completed"]
    for event in events:
        print(format_event(event, completed=bool(event.get("completed"))))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--mode",
        choices=("latest", "today", "upcoming", "mapping", "all"),
        default="latest",
        help="Live-result view to return.",
    )
    parser.add_argument("--date", help="YYYY-MM-DD date for --mode today.")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--upcoming", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    try:
        payload = fetch_payload(args.timeout)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Unable to fetch ESPN results: {exc}", file=sys.stderr)
        return 1

    contract = build_contract(payload, upcoming_limit=args.upcoming)

    if args.as_json:
        print(json.dumps(selected_payload(contract, args), ensure_ascii=False, indent=2))
        return 0

    print_text_view(contract, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
