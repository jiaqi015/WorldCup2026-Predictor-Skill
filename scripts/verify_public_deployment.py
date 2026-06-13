#!/usr/bin/env python3
"""Verify the public World Cup demo and representative static assets."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "https://www.cameraclaw.cn/2026"
HTML_MARKERS = (
    "2026 世界杯",
    "var GD=",
    "var PHOTO_MAP=",
)
ASSETS = (
    ("data/photos/45843.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("data/photos/sofifa_202126.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("data/photos/avatar_Neymar.svg", "image/svg+xml", b"<svg"),
)


def fetch(url: str, timeout: float) -> tuple[str, bytes]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "world-cup-2026-deploy-check/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        return content_type, response.read()


def verify(base_url: str, timeout: float) -> None:
    base_url = base_url.rstrip("/")
    content_type, body = fetch(base_url, timeout)
    if content_type != "text/html":
        raise RuntimeError(
            f"{base_url} returned {content_type!r}, expected 'text/html'"
        )

    html = body.decode("utf-8")
    for marker in HTML_MARKERS:
        if marker not in html:
            raise RuntimeError(f"{base_url} is missing marker: {marker}")
    print(f"[OK] HTML {base_url} ({len(body)} bytes)")

    for relative_path, expected_type, signature in ASSETS:
        url = f"{base_url}/{relative_path}"
        asset_type, asset_body = fetch(url, timeout)
        if asset_type != expected_type:
            raise RuntimeError(
                f"{url} returned {asset_type!r}, expected {expected_type!r}"
            )
        if signature not in asset_body[:512]:
            raise RuntimeError(f"{url} does not contain the expected file signature")
        print(f"[OK] {asset_type} {url} ({len(asset_body)} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    try:
        verify(args.base_url, args.timeout)
    except (RuntimeError, UnicodeDecodeError, urllib.error.URLError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
