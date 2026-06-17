#!/usr/bin/env python3
"""
Final push to reach 100% photo coverage for remaining placeholder players.

Strategies (in order):
  1. Transfermarkt search with country filtering
  2. Wikidata entity search -> multiple image properties
  3. TheSportsDB full-name search with fuzzy matching
  4. Wikipedia article page image extraction

Usage:
    python3 scripts/fetch_player_photos_final.py --dry-run
    python3 scripts/fetch_player_photos_final.py --write
    python3 scripts/fetch_player_photos_final.py --write --limit 5
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from photo_utils import (
    USER_AGENT, TM_USER_AGENT, PHOTO_MAPPING_FILE,
    load_mapping, save_mapping, get_placeholders,
    download_image, determine_ext, safe_name, normalize_name,
    _strip_accents,
)

PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "photos")
MAPPING_FILE = PHOTO_MAPPING_FILE

SEARCH_DELAY = 1.5
DOWNLOAD_DELAY = 2.0

# Country name mapping: Chinese team name -> English name for matching
CN_COUNTRY = {
    "沙特": "Saudi Arabia", "约旦": "Jordan", "埃及": "Egypt",
    "伊朗": "Iran", "伊拉克": "Iraq", "突尼斯": "Tunisia",
    "阿尔及利亚": "Algeria", "加纳": "Ghana", "卡塔尔": "Qatar",
    "土耳其": "Turkey", "乌兹别克": "Uzbekistan",
}

# Manual Transfermarkt name variants discovered through testing
TM_MANUAL_VARIANTS = {
    "Mostafa Shoubir": ["Shobeir", "Oufa Shobeir"],
    "Mostafa Zico": ["Mostafa Ziko", "Ziko Mostafa", "Ziko"],
    "Ahmed Maknazi": ["Ahmed Maknzi", "Maknzi"],
    "Akam Hashim": ["Akam Hashem", "Hashem"],
    "Mohammad Abughoush": ["Abu Ghoush", "Mohammad Abu Ghoush"],
    "Avazbek Ulmasaliyev": ["Avazbek Ulmasaliev", "Ulmasaliev"],
    "Nour Bani Ateyah": ["Bani Attiah", "Nour Bani Attiah", "Bani Atiyah"],
    "Mohammad Al-Daoud": ["Al Daoud", "Al-Dawood", "Al Dawood"],
    "Mohanad Lashin": ["Lasheen", "Mohanad Lasheen"],
    "Nabil Donga": ["Nabil Dong", "Donga Nabil"],
    "Danial Iri": ["Danial Eiri", "Eiri"],
}


def get_player_info(name, player_mapping):
    """Get player info from player_mapping.json."""
    info = player_mapping.get(name, {})
    team = info.get("team", "")
    country = CN_COUNTRY.get(team, team)
    return {"name": name, "team": team, "country": country}


def country_matches(actual, expected):
    """Check if actual country matches expected."""
    if not actual or not expected:
        return False
    a = actual.lower().strip()
    e = expected.lower().strip()
    if e in a or a in e:
        return True
    an = normalize_name(actual)
    en = normalize_name(expected)
    if en in an or an in en:
        return True
    # Turkey / Turkiye / Türkiye
    if "turk" in an and ("turk" in en or "turkiye" in en):
        return True
    return False


def _reverse_name(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return " ".join(parts[1:] + [parts[0]])
    return name


def _name_similar(a, b):
    """Loose name similarity check for Transfermarkt results."""
    na = normalize_name(a)
    nb = normalize_name(b)
    if na == nb:
        return True
    if na == normalize_name(_reverse_name(b)):
        return True
    # Last name match (exact or contained)
    la = na.split()[-1] if na.split() else ""
    lb = nb.split()[-1] if nb.split() else ""
    if la == lb:
        return True
    if len(la) >= 3 and len(lb) >= 3:
        if la in lb or lb in la:
            return True
        # Allow character difference for transliteration variants
        if abs(len(la) - len(lb)) <= 2:
            common = sum(1 for x, y in zip(la, lb) if x == y)
            if common >= min(len(la), len(lb)) - 2:
                return True
        # One name is the other minus a leading char (e.g., "eiri" vs "iri")
        if len(la) > len(lb) and la[1:] == lb:
            return True
        if len(lb) > len(la) and lb[1:] == la:
            return True
    return False


def generate_tm_variants(name):
    """Generate name variants for Transfermarkt search."""
    variants = []
    seen = set()
    def add(v):
        v = v.strip()
        if v and v not in seen and len(v) >= 3:
            variants.append(v)
            seen.add(v)

    # Manual variants FIRST (highest priority)
    for v in TM_MANUAL_VARIANTS.get(name, []):
        add(v)

    add(name)
    add(name.replace("-", " "))
    rev = _reverse_name(name)
    add(rev)
    parts = name.split()
    if len(parts) >= 2:
        add(parts[-1])
        add(parts[0])
    if len(parts) >= 3:
        add(f"{parts[0]} {parts[-1]}")
    for p in parts:
        if p.lower().startswith("al-") and len(p) > 3:
            add(p[3:])
    stripped = _strip_accents(name)
    if stripped != name:
        add(stripped)
    return variants


# -- Strategy 1: Transfermarkt -------------------------------------------

def strategy_transfermarkt(name, expected_country):
    """Search Transfermarkt with country filtering."""
    variants = generate_tm_variants(name)

    for variant in variants:
        url = (f"https://www.transfermarkt.com/schnellsuche/ergebnis/"
               f"schnellsuche?query={urllib.parse.quote_plus(variant)}")
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": TM_USER_AGENT,
                "Accept": "text/html",
            })
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(SEARCH_DELAY)
            continue

        results = []
        for m in re.finditer(
            r'portrait/(?:small|header)/(\d+)-([^"]+)"[^>]*title="([^"]+)"',
            html,
        ):
            pid, ver, pname = m.groups()
            if "default" in ver:
                continue
            after = html[m.end():m.end() + 2000]
            flag = re.search(r'flagge[^"]*"[^>]*title="([^"]+)"', after)
            country = flag.group(1) if flag else ""
            results.append({"pid": pid, "ver": ver, "name": pname, "country": country})

        # Filter by country, then verify name similarity
        for r in results:
            if country_matches(r["country"], expected_country):
                if _name_similar(r["name"], name):
                    return (f"https://img.a.transfermarkt.technology/portrait/header/"
                            f"{r['pid']}-{r['ver']}")

        time.sleep(SEARCH_DELAY)

    return None


# -- Strategy 2: Wikidata entity + image properties ----------------------

WD_IMAGE_PROPS = ["P18", "P948"]


def strategy_wikidata(name, expected_country=None):
    """Search Wikidata for entity, then check image properties."""
    variants = [name, name.replace("-", " "), _reverse_name(name), name.split()[-1]]

    for variant in variants:
        if len(variant) < 3:
            continue
        url = (
            "https://www.wikidata.org/w/api.php?"
            "action=wbsearchentities"
            f"&search={urllib.parse.quote_plus(variant)}"
            "&language=en&limit=5&format=json"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(SEARCH_DELAY)
            continue

        for result in data.get("search", []):
            entity_id = result.get("id", "")
            desc = result.get("description", "").lower()
            label = result.get("label", "")

            is_football = any(kw in desc for kw in [
                "football", "soccer", "footballer", "defender",
                "midfielder", "forward", "goalkeeper",
            ])
            if not is_football and desc:
                if not any(kw in desc for kw in ["sport", "athlete", "player"]):
                    continue

            for prop in WD_IMAGE_PROPS:
                if not re.fullmatch(r'Q\d+', entity_id):
                    continue
                spql = f"SELECT ?img WHERE {{ wd:{entity_id} wdt:{prop} ?img }}"
                sp_url = (
                    "https://query.wikidata.org/sparql?"
                    f"query={urllib.parse.quote(spql)}&format=json"
                )
                try:
                    req2 = urllib.request.Request(sp_url, headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/sparql-results+json",
                    })
                    resp2 = urllib.request.urlopen(req2, timeout=15)
                    data2 = json.loads(resp2.read().decode("utf-8"))
                    bindings = data2.get("results", {}).get("bindings", [])
                    if bindings:
                        return bindings[0]["img"]["value"]
                except (urllib.error.URLError, OSError, ValueError):
                    pass

        time.sleep(SEARCH_DELAY)

    return None


# -- Strategy 3: TheSportsDB --------------------------------------------

def strategy_sportsdb(name):
    """Search TheSportsDB with full name and variants."""
    variants = [name, name.replace("-", " "), _reverse_name(name)]

    for variant in variants:
        url = (
            "https://www.thesportsdb.com/api/v1/json/3/"
            f"searchplayers.php?p={urllib.parse.quote_plus(variant)}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(SEARCH_DELAY)
            continue

        for p in (data.get("player") or []):
            p_name = p.get("strPlayer", "")
            if not p_name:
                continue
            if _name_similar(p_name, name):
                for img_key in ["strCutout", "strThumb", "strRender"]:
                    img_url = p.get(img_key, "")
                    if img_url:
                        return img_url

        time.sleep(SEARCH_DELAY)

    return None


# -- Strategy 4: Wikipedia article page image ----------------------------

def strategy_wikipedia_page_image(name):
    """Search Wikipedia for article and extract page image."""
    variants = [name, name.replace("-", " "), _reverse_name(name)]

    for variant in variants:
        url = (
            "https://en.wikipedia.org/w/api.php?"
            "action=query&list=search"
            f"&srsearch={urllib.parse.quote_plus(variant + ' footballer')}"
            "&srlimit=3&format=json"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(SEARCH_DELAY)
            continue

        results = data.get("query", {}).get("search", [])
        if not results:
            continue

        page_title = results[0]["title"]
        img_url = _get_wiki_page_image(page_title)
        if img_url:
            return img_url
        time.sleep(SEARCH_DELAY)

    return None


def _get_wiki_page_image(page_title):
    """Get the main image of a Wikipedia page."""
    url = (
        "https://en.wikipedia.org/w/api.php?"
        f"action=query&titles={urllib.parse.quote(page_title)}"
        "&prop=pageimages&pithumbsize=500&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        for page in data.get("query", {}).get("pages", {}).values():
            thumb = page.get("thumbnail", {})
            if thumb:
                return thumb.get("source")
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return None


# -- Main orchestrator ---------------------------------------------------

def deep_search_single(name, player_mapping):
    """Try all strategies for a single player."""
    info = get_player_info(name, player_mapping)
    country = info["country"]

    strategies = [
        ("transfermarkt", lambda: strategy_transfermarkt(name, country)),
        ("wikidata", lambda: strategy_wikidata(name, country)),
        ("sportsdb", lambda: strategy_sportsdb(name)),
        ("wikipedia_pageimg", lambda: strategy_wikipedia_page_image(name)),
    ]

    for strategy_name, strategy_fn in strategies:
        try:
            img_url = strategy_fn()
            if img_url and not img_url.startswith(("https://", "http://")):
                img_url = None
            if img_url:
                return img_url, strategy_name
        except Exception as e:
            sys.stderr.write(f"    [WARN] {strategy_name} error for {name}: {e}\n")

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Final photo push")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    dry_run = not args.write

    mapping = load_mapping()
    pm_path = os.path.join(os.path.dirname(MAPPING_FILE), "player_mapping.json")
    if os.path.exists(pm_path):
        with open(pm_path, "r", encoding="utf-8") as f:
            player_mapping = json.load(f)
    else:
        player_mapping = {}

    placeholders = sorted(get_placeholders(mapping))
    if not placeholders:
        print("[Final] No placeholder players remaining.")
        return

    if args.limit > 0:
        placeholders = placeholders[:args.limit]

    mode = "DRY-RUN" if dry_run else "WRITE"
    print(f"[Final] {len(placeholders)} placeholder players to process ({mode})")
    print()

    found = 0
    missing = []
    strategy_counts = {}
    errors = []

    for i, name in enumerate(placeholders, 1):
        sys.stdout.write(f"  [{i}/{len(placeholders)}] {name}... ")
        sys.stdout.flush()

        img_url, strategy_name = deep_search_single(name, player_mapping)

        if img_url:
            found += 1
            strategy_counts[strategy_name] = strategy_counts.get(strategy_name, 0) + 1
            print(f"OK [{strategy_name}]")

            if not dry_run:
                time.sleep(DOWNLOAD_DELAY)
                ext = determine_ext(img_url)
                filename = f"{strategy_name}_{safe_name(name)}{ext}"
                filepath = os.path.join(PHOTO_DIR, filename)

                if download_image(img_url, filepath):
                    mapping[name]["source"] = strategy_name
                    mapping[name]["path"] = f"data/photos/{filename}"
                    if i % 5 == 0:
                        save_mapping(mapping)
                else:
                    errors.append(f"Download failed: {name}")
                    print(f"    [ERR] Download failed")
        else:
            missing.append(name)
            print("MISS")

    if not dry_run and found > 0:
        save_mapping(mapping)

    real_count = sum(1 for v in mapping.values() if v.get("source") != "placeholder")
    total = len(mapping)
    print()
    print("=" * 60)
    print("FINAL SEARCH SUMMARY")
    print("=" * 60)
    print(f"Processed: {len(placeholders)}")
    print(f"Found:     {found}")
    print(f"Missing:   {len(missing)}")
    print(f"\nStrategy breakdown:")
    for s, c in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")
    print(f"\nTotal coverage: {real_count}/{total} ({real_count/total*100:.1f}%)")

    if missing:
        print(f"\nStill missing ({len(missing)}):")
        for n in missing:
            print(f"  - {n}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
