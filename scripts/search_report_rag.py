#!/usr/bin/env python3
"""Search the generated report corpus with a lightweight lexical scorer."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data" / "rag" / "kimi-world-cup-report" / "chunks.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Chinese or English search terms")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def tokenize(value: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9.+-]*|[\u4e00-\u9fff]{2,}", value)
    ]


def score_record(record: dict, terms: list[str]) -> int:
    text = record.get("text", "").lower()
    heading = " ".join(
        [
            record.get("chapter", ""),
            record.get("section", ""),
            " ".join(record.get("keywords", [])),
        ]
    ).lower()
    return sum(text.count(term) + 4 * heading.count(term) for term in terms)


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    terms = tokenize(args.query)
    if not terms:
        raise SystemExit("Query must contain searchable Chinese or English terms")

    corpus = args.corpus.expanduser().resolve()
    if not corpus.is_file():
        raise SystemExit(f"RAG corpus not found: {corpus}")

    ranked = []
    with corpus.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            score = score_record(record, terms)
            if score:
                ranked.append((score, record))
    ranked.sort(key=lambda item: (-item[0], item[1]["page_start"], item[1]["id"]))
    results = [
        {
            "score": score,
            "id": record["id"],
            "chapter": record["chapter"],
            "section": record["section"],
            "page": record["page_start"],
            "citation": record["citation"],
            "keywords": record["keywords"],
            "text": record["text"],
        }
        for score, record in ranked[: args.limit]
    ]

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for index, result in enumerate(results, start=1):
            preview = re.sub(r"\s+", " ", result["text"])[:280]
            print(f"{index}. [{result['score']}] {result['citation']}")
            print(f"   {result['chapter']} / {result['section']}")
            print(f"   {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
