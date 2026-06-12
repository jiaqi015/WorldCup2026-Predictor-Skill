#!/usr/bin/env python3
"""Validate the generated Kimi report RAG corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "data" / "rag" / "kimi-world-cup-report"


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_number}: invalid JSON: {exc}") from exc
    return records


def main() -> int:
    errors = []
    required = ["manifest.json", "pages.jsonl", "chunks.jsonl", "sections.json", "corpus.md"]
    for filename in required:
        if not (CORPUS_ROOT / filename).is_file():
            errors.append(f"missing {filename}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    pages = load_jsonl(CORPUS_ROOT / "pages.jsonl")
    chunks = load_jsonl(CORPUS_ROOT / "chunks.jsonl")
    source_hash = manifest.get("source", {}).get("sha256")

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("source", {}).get("page_count") != 205:
        errors.append("expected a 205-page source report")
    if len(pages) != 205:
        errors.append(f"expected 205 page records, found {len(pages)}")
    if [page.get("page") for page in pages] != list(range(1, 206)):
        errors.append("page records must be complete and sequential")
    if len(chunks) < 205:
        errors.append("expected at least one chunk per page")
    if len({chunk.get("id") for chunk in chunks}) != len(chunks):
        errors.append("chunk IDs must be unique")
    if not source_hash or len(source_hash) != 64:
        errors.append("manifest must contain a SHA-256 source hash")

    required_chunk_fields = {
        "id",
        "source_id",
        "page_start",
        "page_end",
        "chapter",
        "section",
        "text",
        "citation",
        "source_sha256",
    }
    for chunk in chunks:
        missing = required_chunk_fields - chunk.keys()
        if missing:
            errors.append(f"{chunk.get('id', '<unknown>')}: missing {sorted(missing)}")
            break
        if not chunk["text"].strip():
            errors.append(f"{chunk['id']}: empty text")
            break
        if chunk["page_start"] != chunk["page_end"]:
            errors.append(f"{chunk['id']}: chunks must remain page-bounded")
            break
        if chunk["source_sha256"] != source_hash:
            errors.append(f"{chunk['id']}: source hash does not match manifest")
            break
        expected_citation = f"{manifest.get('title')}, p.{chunk['page_start']}"
        if chunk["citation"] != expected_citation:
            errors.append(f"{chunk['id']}: citation does not match its page")
            break

    manifest_chunks = manifest.get("chunking", {}).get("chunk_count")
    if manifest_chunks != len(chunks):
        errors.append(
            f"manifest chunk_count {manifest_chunks} does not match {len(chunks)}"
        )
    corpus_text = (CORPUS_ROOT / "corpus.md").read_text(encoding="utf-8")
    if corpus_text.count("\n### Page ") != 205:
        errors.append("corpus.md must contain one heading for each of the 205 pages")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print("RAG corpus validation passed.")
    print(f"- pages: {len(pages)}")
    print(f"- chunks: {len(chunks)}")
    print("- page citations and source hashes present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
