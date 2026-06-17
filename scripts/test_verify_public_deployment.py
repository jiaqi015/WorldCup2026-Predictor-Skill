#!/usr/bin/env python3
"""Regression tests for the public deployment verifier."""

from __future__ import annotations

from pathlib import Path

import verify_public_deployment as vpd


ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def test_public_html_markers() -> None:
    print("\n=== public HTML markers ===")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for marker in vpd.HTML_MARKERS:
        report(f"marker present: {marker}", marker in html)


def test_asset_inventory_exists() -> None:
    print("\n=== public asset inventory ===")
    for relative_path, _expected_type, signature in vpd.ASSETS:
        path = ROOT / relative_path
        exists = path.is_file()
        report(f"asset exists: {relative_path}", exists)
        if exists:
            prefix = path.read_bytes()[:512]
            report(
                f"asset signature: {relative_path}",
                signature in prefix,
                f"signature={signature!r}",
            )


def main() -> int:
    test_public_html_markers()
    test_asset_inventory_exists()
    print(f"\nPublic deployment verifier tests: {PASS} passed, {FAIL} failed.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
