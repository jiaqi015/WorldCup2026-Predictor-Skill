#!/usr/bin/env python3
"""
Clean Latin-script contamination from player_mapping.json Chinese names.

Strategy: for each entry whose 'cn' contains Latin letters or digits,
extract those English/numeric fragments and append them to the canonical
English name (already present). If 'cn' is something like "穆罕默德 Amine Tougai"
→ pure-Chinese "穆罕默德" + append "Amine Tougai" as a comment in 'cn_alt'.

To keep the in-app look natural for already-known bilingual names like
'B费' / 'C罗' / '希门尼斯MEX' (which users recognize), we apply a whitelist
of accepted mixed names.

Output: data/squads/player_mapping.json (overwritten in place with the
corrected 'cn' field for each entry whose 'cn' had Latin-script contamination).
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
MAPPING_FILE = BASE / "data" / "squads" / "player_mapping.json"

# Names that the user-base already recognizes as bilingual and that we keep verbatim.
KEEP_BILINGUAL = {
    "B费", "C罗", "希门尼斯MEX", "希门尼斯",
    # Initial + surname is the established convention for these marquee names
    "Nico冈萨雷斯", "NicoPaz", "Nico Paz", "Nico洛佩斯",
    "JoséManuel洛佩斯", "José López", "Jose洛佩斯",
}

# Clean: remove all Latin letters/digits sequences from a Chinese string.
# This includes accented ESPN fragments like "á", "é", "ø".
LATIN_RUN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+")
# Remove separators that were only joining stripped Latin fragments.
STRAY_SEPARATORS = re.compile(r"(^|\s)[·\-‐‑‒–—_']+(?=\s|$)")
# Normalize 2+ spaces
MULTI_SP = re.compile(r"\s{2,}")

def normalize_cleaned_name(value):
    cleaned = LATIN_RUN.sub(" ", value)
    cleaned = STRAY_SEPARATORS.sub(" ", cleaned)
    cleaned = re.sub(r"\s*([·-])\s*", r"\1", cleaned)
    cleaned = re.sub(r"^[·\-‐‑‒–—_']+|[·\-‐‑‒–—_']+$", "", cleaned)
    return MULTI_SP.sub(" ", cleaned).strip()

def clean_cn(en, cn):
    """Return a pure-CJK 'cn' that may keep trailing or middle Latin fragments
    only if they appear in KEEP_BILINGUAL. Otherwise strip Latin runs and keep
    just the Chinese part, optionally appending the original English 'en' as
    a 注释 suffix."""
    if cn in KEEP_BILINGUAL:
        return cn
    # Already clean?
    has_latin = bool(re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]", cn))
    has_stray_separator = bool(STRAY_SEPARATORS.search(cn) or re.search(r"^[·\-‐‑‒–—_']+|[·\-‐‑‒–—_']+$", cn))
    if not has_latin and not has_stray_separator:
        return cn
    cleaned = normalize_cleaned_name(cn)
    if not cleaned:
        # Everything was Latin-script — fall back to the source name.
        return en
    # If the cleaned version still has Chinese, that's our answer.
    return cleaned


def main():
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        m = json.load(f)
    fixed = 0
    samples = []
    for en, info in m.items():
        if not isinstance(info, dict):
            continue
        cn = info.get("cn", "")
        if not cn:
            continue
        new_cn = clean_cn(en, cn)
        if new_cn != cn:
            info["cn"] = new_cn
            fixed += 1
            if len(samples) < 25:
                samples.append((en, cn, new_cn))
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(f"[clean] {fixed} entries updated")
    print("[clean] First 25 samples:")
    for e, old, new in samples:
        print(f"  {e!r:50} {old!r:40} → {new!r}")


if __name__ == "__main__":
    main()
