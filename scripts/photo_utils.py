#!/usr/bin/env python3
"""
Shared utilities for photo completion scripts.

Provides: name normalization, image validation, atomic file I/O.
Used by: fetch_wikidata_photos.py, fetch_wikipedia_photos.py,
         fetch_sportsdb_photos.py, fetch_tm_photos.py
"""

import json
import os
import re
import tempfile
import unicodedata
import urllib.error
import urllib.request


PHOTO_MAPPING_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "squads", "photo_mapping.json"
)

# Unicode chars that NFKD does NOT decompose (need manual mapping)
_NON_DECOMPOSING = {
    "\u0131": "i",  # ı (Turkish dotless i)
    "\u0111": "d",  # đ
    "\u00f8": "o",  # ø
    "\u0142": "l",  # ł
    "\u0127": "h",  # ħ
}


def _strip_accents(text):
    """NFKD decomposition + mapping table for non-decomposing chars."""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    for orig, repl in _NON_DECOMPOSING.items():
        stripped = stripped.replace(orig, repl)
    return stripped


def normalize_name(name):
    """NFKD normalization: strip accents, lowercase, collapse whitespace."""
    if not name:
        return ""
    return " ".join(_strip_accents(name).lower().split())


def surname(name):
    """Extract last word as surname."""
    return name.strip().split()[-1] if name and name.strip() else ""


def safe_name(name):
    """Convert player name to safe filename.

    Strips accents, replaces spaces with underscore, and filters out
    characters unsafe for file paths (/ \\ .. : etc).
    Only allows alphanumeric, underscore, hyphen, and dot.
    """
    if not name:
        return ""
    clean = _strip_accents(name).replace(" ", "_")
    clean = re.sub(r"[^a-zA-Z0-9._-]", "", clean)
    clean = clean.replace("..", "")
    return clean or "unknown"


def validate_image(filepath):
    """Check that a downloaded file is a real image (PNG/JPEG/WEBP).

    Returns True if valid. If invalid, deletes the file and returns False.
    """
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)
    except OSError:
        return False

    # PNG: \x89PNG
    if header[:4] == b'\x89PNG':
        return True
    # JPEG: \xFF\xD8
    if header[:2] == b'\xFF\xD8':
        return True
    # WEBP: RIFF....WEBP
    if header[:4] == b'RIFF' and len(header) >= 12 and header[8:12] == b'WEBP':
        return True

    # Not a recognized image format — delete
    try:
        os.unlink(filepath)
    except OSError:
        pass
    return False


def load_mapping(path=None):
    """Load photo_mapping.json. Returns empty dict on missing/corrupt file."""
    path = path or PHOTO_MAPPING_FILE
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_mapping(mapping, path=None):
    """Atomically write photo_mapping.json (tempfile + os.replace)."""
    path = path or PHOTO_MAPPING_FILE
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_placeholders(mapping):
    """Return dict of players with source='placeholder'."""
    return {k: v for k, v in mapping.items() if v.get("source") == "placeholder"}


# ---------------------------------------------------------------------------
# Shared download utilities (M3: deduplicated from fetch_*.py)
# ---------------------------------------------------------------------------

USER_AGENT = "FIFA26PhotoFetcher/1.0"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB (H3)


def determine_ext(url):
    """Guess file extension from URL path."""
    lower = url.lower().split("?")[0]  # strip query params
    if lower.endswith(".png"):
        return ".png"
    if lower.endswith(".webp"):
        return ".webp"
    if lower.endswith(".gif"):
        return ".gif"
    return ".jpg"


def download_image(url, filepath, timeout=20):
    """Download image from URL, validate, and save.

    Returns True on success. Handles 429 retry with exponential backoff.
    Enforces MAX_IMAGE_SIZE limit (H3).
    """
    import time
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read(MAX_IMAGE_SIZE + 1)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 2)  # 4s, 8s, 16s
                time.sleep(wait)
                continue
            return False
        except Exception:
            return False
        else:
            break
    else:
        return False

    if len(data) > MAX_IMAGE_SIZE:
        return False
    if len(data) < 2000:
        return False

    with open(filepath, "wb") as f:
        f.write(data)

    return validate_image(filepath)
