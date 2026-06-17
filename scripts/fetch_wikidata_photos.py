#!/usr/bin/env python3
"""
Fetch player headshot photos from Wikidata SPARQL endpoint.

Phase 1 of avatar completion: covers ~47% of placeholder players.
Uses batch SPARQL queries with three-tier name matching:
  Tier 1: Exact label match
  Tier 2: NFKD-normalized match (strip accents)
  Tier 3: Surname-only match + occupation filter

Usage:
    python3 scripts/fetch_wikidata_photos.py
    python3 scripts/fetch_wikidata_photos.py --batch-size 30 --dry-run
"""

import argparse
import json
import os
import sys
import time
import random
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from photo_utils import (
    normalize_name, surname, safe_name, validate_image,
    load_mapping, save_mapping, get_placeholders,
    download_image, determine_ext, USER_AGENT, MAX_IMAGE_SIZE,
)

PHOTOS_DIR = Path(__file__).parent.parent / "data" / "photos"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
REQUEST_DELAY = 0.5  # seconds between SPARQL queries
DOWNLOAD_DELAY = 3.0  # seconds between image downloads
DOWNLOAD_JITTER = 1.0  # random jitter added to delay
BATCH_SIZE = 50


def build_sparql_batch(names, with_occupation=True):
    """Build a SPARQL query for a batch of names."""
    # L1: Escape double quotes in names to prevent SPARQL injection
    escaped = [n.replace('"', '\\"') for n in names]
    values = " ".join(f'"{name}"@en' for name in escaped)
    occ_filter = "?item wdt:P106 wd:Q937857." if with_occupation else ""
    return f"""
SELECT ?name ?pic WHERE {{
  VALUES ?name {{ {values} }}
  ?item wdt:P31 wd:Q5.
  ?item rdfs:label ?name.
  {occ_filter}
  ?item wdt:P18 ?pic.
}}
"""


def query_sparql(query, retries=3, timeout=30):
    """Execute SPARQL query and return bindings."""
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
    })
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", {}).get("bindings", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(30 * (2 ** attempt), 300)
                print(f"  [429] Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 500:
                time.sleep(5)
            else:
                print(f"  [HTTP {e.code}] {e.reason}")
                return []
        except Exception as e:
            print(f"  [Error] {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return []


def _wikidata_download(url, filepath, timeout=20):
    """Download Wikidata image, converting Special:FilePath to thumbnail URL."""
    if "Special:FilePath" in url:
        filename = url.split("Special:FilePath/")[-1]
        url = f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{filename}?width=256"
    return download_image(url, filepath, timeout=timeout)


def fetch_batch(names, with_occupation=True):
    """Query Wikidata for a batch of names, return {name: image_url}."""
    query = build_sparql_batch(names, with_occupation=with_occupation)
    bindings = query_sparql(query)
    results = {}
    for b in bindings:
        name_val = b.get("name", {}).get("value", "")
        pic_val = b.get("pic", {}).get("value", "")
        if name_val and pic_val:
            results[name_val] = pic_val
    return results


def run(args):
    """Main entry point."""
    mapping = load_mapping()
    placeholders = get_placeholders(mapping)
    total = len(placeholders)

    if total == 0:
        print("[Wikidata] No placeholder players to process.")
        return 0

    print(f"[Wikidata] {total} placeholder players to process")
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    names = list(placeholders.keys())
    found = 0
    not_found = []

    # --- Tier 1: Exact label match with occupation filter ---
    print(f"\n=== Tier 1: Exact match (batch size {args.batch_size}) ===")
    tier1_misses = []
    for i in range(0, len(names), args.batch_size):
        batch = names[i:i + args.batch_size]
        print(f"  Batch {i // args.batch_size + 1}: {len(batch)} names...", end=" ")
        results = fetch_batch(batch, with_occupation=True)
        print(f"found {len(results)}")

        for name in batch:
            if name in results:
                pic_url = results[name]
                ext = determine_ext(pic_url)
                fname = f"wikidata_{safe_name(name)}{ext}"
                fpath = PHOTOS_DIR / fname

                if fpath.exists() and fpath.stat().st_size > 2000:
                    found += 1
                elif args.dry_run:
                    found += 1
                    print(f"    [DRY] {name} -> {pic_url}")
                elif _wikidata_download(pic_url, str(fpath)):
                    found += 1
                    time.sleep(DOWNLOAD_DELAY + random.uniform(0, DOWNLOAD_JITTER))
                else:
                    tier1_misses.append(name)
                    continue

                # Update mapping
                mapping[name] = {
                    "source": "wikidata",
                    "path": f"data/photos/{fname}",
                    "athlete_id": None,
                }
            else:
                tier1_misses.append(name)

        if not args.dry_run:
            save_mapping(mapping)
        time.sleep(REQUEST_DELAY)

    print(f"  Tier 1 result: {found} found, {len(tier1_misses)} misses")

    # --- Tier 2: NFKD-normalized match ---
    if tier1_misses:
        print(f"\n=== Tier 2: NFKD-normalized match ({len(tier1_misses)} names) ===")
        tier2_misses = []
        # Build normalized->original mapping
        norm_to_orig = {}
        for name in tier1_misses:
            norm = normalize_name(name)
            if norm and norm != name.lower():
                norm_to_orig[norm] = name

        if norm_to_orig:
            norm_names = list(norm_to_orig.keys())
            for i in range(0, len(norm_names), args.batch_size):
                batch = norm_names[i:i + args.batch_size]
                print(f"  Batch: {len(batch)} normalized names...", end=" ")
                results = fetch_batch(batch, with_occupation=True)
                print(f"found {len(results)}")

                for norm_name in batch:
                    if norm_name in results:
                        orig_name = norm_to_orig[norm_name]
                        pic_url = results[norm_name]
                        ext = determine_ext(pic_url)
                        fname = f"wikidata_{safe_name(orig_name)}{ext}"
                        fpath = PHOTOS_DIR / fname

                        if args.dry_run:
                            found += 1
                            print(f"    [DRY] {orig_name} -> {pic_url}")
                        elif _wikidata_download(pic_url, str(fpath)):
                            found += 1
                            time.sleep(DOWNLOAD_DELAY + random.uniform(0, DOWNLOAD_JITTER))
                            mapping[orig_name] = {
                                "source": "wikidata",
                                "path": f"data/photos/{fname}",
                                "athlete_id": None,
                            }
                        else:
                            tier2_misses.append(orig_name)
                            continue
                    else:
                        tier2_misses.append(norm_to_orig.get(norm_name, norm_name))

                if not args.dry_run:
                    save_mapping(mapping)
                time.sleep(REQUEST_DELAY)

        # Add names that had no normalized variant
        for name in tier1_misses:
            if normalize_name(name) == name.lower():
                tier2_misses.append(name)

        not_found = tier2_misses
        print(f"  Tier 2 result: {found} total found, {len(not_found)} misses")

    # --- Tier 3: Surname match (no occupation filter, with dedup) ---
    if not_found:
        print(f"\n=== Tier 3: Surname match ({len(not_found)} names) ===")
        tier3_misses = []
        surname_to_origs = {}
        for name in not_found:
            s = surname(name)
            if s:
                surname_to_origs.setdefault(s.lower(), []).append(name)

        surnames_list = list(surname_to_origs.keys())
        for i in range(0, len(surnames_list), args.batch_size):
            batch = surnames_list[i:i + args.batch_size]
            print(f"  Batch: {len(batch)} surnames...", end=" ")
            results = fetch_batch(batch, with_occupation=True)  # M1: added occupation filter
            print(f"found {len(results)}")

            for s_name in batch:
                if s_name in results:
                    # Only assign if exactly one candidate
                    candidates = surname_to_origs[s_name]
                    if len(candidates) == 1:
                        orig_name = candidates[0]
                        pic_url = results[s_name]
                        ext = determine_ext(pic_url)
                        fname = f"wikidata_{safe_name(orig_name)}{ext}"
                        fpath = PHOTOS_DIR / fname

                        if args.dry_run:
                            found += 1
                            print(f"    [DRY] {orig_name} -> {pic_url}")
                        elif _wikidata_download(pic_url, str(fpath)):
                            found += 1
                            time.sleep(DOWNLOAD_DELAY + random.uniform(0, DOWNLOAD_JITTER))
                            mapping[orig_name] = {
                                "source": "wikidata",
                                "path": f"data/photos/{fname}",
                                "athlete_id": None,
                            }
                        else:
                            tier3_misses.append(orig_name)
                            continue
                    else:
                        # Ambiguous surname — skip
                        tier3_misses.extend(candidates)
                else:
                    tier3_misses.extend(surname_to_origs[s_name])

            if not args.dry_run:
                save_mapping(mapping)
            time.sleep(REQUEST_DELAY)

        not_found = tier3_misses
        print(f"  Tier 3 result: {found} total found, {len(not_found)} remaining")

    # --- Summary ---
    print(f"\n=== Summary ===")
    print(f"  Total placeholders: {total}")
    print(f"  Found: {found}")
    print(f"  Not found: {len(not_found)}")
    if not_found and len(not_found) <= 20:
        for name in not_found:
            print(f"    - {name}")

    return found


def main():
    parser = argparse.ArgumentParser(description="Fetch player photos from Wikidata")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="Don't download, just query")
    args = parser.parse_args()

    found = run(args)
    return 0 if found > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
