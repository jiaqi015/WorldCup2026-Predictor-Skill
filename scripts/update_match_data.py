#!/usr/bin/env python3
"""Embed the current match snapshot into the canonical predictor app."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data"
END_MARKER = "// === END REAL DATA ==="


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def minified(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def upsert_var(html, name, payload):
    declaration = f"var {name}={minified(payload)};\n"
    pattern = rf"\n?var\s+{re.escape(name)}\s*=.*?;\n?"
    html = re.sub(pattern, "\n", html, flags=re.DOTALL)
    marker = html.find(END_MARKER)
    if marker < 0:
        raise RuntimeError(f"missing data marker: {END_MARKER}")
    return html[:marker] + declaration + html[marker:]


def main():
    rankings = load_json("data/rankings/fifa_rankings.json")
    schedule = load_json("data/matches/match_schedule.json")
    details = load_json("data/matches/match_details.json")
    manifest = load_json("data/matches/manifest.json")

    html = INDEX.read_text(encoding="utf-8")
    for obsolete in ("VENUES", "COACHES"):
        html = re.sub(
            rf"\n?var\s+{obsolete}\s*=.*?;\n?",
            "\n",
            html,
            flags=re.DOTALL,
        )

    html = upsert_var(html, "FIFA_RANKINGS", rankings)
    html = upsert_var(html, "MATCH_SCHEDULE", schedule)
    html = upsert_var(html, "MATCH_DETAILS", details)
    html = upsert_var(html, "MATCH_DATA_META", manifest)
    INDEX.write_text(html, encoding="utf-8")

    print(f"Embedded {len(schedule)} matches and {len(details)} completed details")
    print(f"Source: {manifest['source']} ({manifest['fetched_at']})")


if __name__ == "__main__":
    main()
