#!/usr/bin/env python3
"""Serve the bundled World Cup predictor over local HTTP."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = SKILL_ROOT / "assets" / "predictor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    index_path = APP_DIR / "index.html"
    if not index_path.is_file():
        parser.error(f"bundled predictor not found: {index_path}")

    handler = partial(SimpleHTTPRequestHandler, directory=str(APP_DIR))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    host, port = server.server_address[:2]
    print(f"World Cup 2026 Predictor: http://{host}:{port}/", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
