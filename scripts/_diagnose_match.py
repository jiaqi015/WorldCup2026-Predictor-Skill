#!/usr/bin/env python3
"""
Diagnose name matching between our squads and ESPN API.
Shows side-by-side comparison for each team and analyzes matching strategies.
"""
import json
import subprocess
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def curl_fetch(url):
    result = subprocess.run(
        ["curl", "-s", "--max-time", "10", url],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)
    return None

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def norm(s):
    """Normalize name for comparison."""
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# Load squads
with open(BASE_DIR / "data/squads/squads_partial.json") as f:
    squads = json.load(f)

# Test with a few diverse teams
test_teams = ["Algeria", "Argentina", "Belgium", "Brazil", "France", "Japan", "South Korea", "Spain"]

for team_name in test_teams:
    team_data = squads[team_name]
    team_id = team_data["team_id"]
    
    roster = curl_fetch(
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"
    )
    if not roster:
        print(f"\n=== {team_name}: API FAILED ===")
        continue
    
    our_players = [p["name"] for p in team_data["players"]]
    espn_names = {a.get("displayName", ""): a.get("id") for a in roster["athletes"]}
    
    # Build ESPN athlete lookup: normalized name -> (original name, id)
    espn_lookup = {}
    for ename, eid in espn_names.items():
        espn_lookup[norm(ename)] = (ename, eid)
    
    # Also index by last name
    espn_by_last = {}
    for ename, eid in espn_names.items():
        parts = norm(ename).split()
        if parts:
            last = parts[-1]
            if last not in espn_by_last:
                espn_by_last[last] = []
            espn_by_last[last].append((ename, eid))
    
    print(f"\n=== {team_name} ===")
    print(f"  Our players: {len(our_players)}, ESPN athletes: {len(espn_names)}")
    
    exact_matches = 0
    norm_matches = 0
    last_name_matches = 0
    no_match = 0
    
    for pname in our_players:
        pnorm = norm(pname)
        
        # Strategy 1: Exact normalized match
        if pnorm in espn_lookup:
            ename, eid = espn_lookup[pnorm]
            exact_matches += 1
            continue
        
        # Strategy 2: Parts matching
        pparts = pnorm.split()
        plast = pparts[-1] if pparts else ""
        
        if plast in espn_by_last:
            candidates = espn_by_last[plast]
            if len(candidates) == 1:
                ename, eid = candidates[0]
                last_name_matches += 1
                continue
            else:
                # Multiple candidates with same last name - check first initial
                pfirst_init = pparts[0][0] if pparts else ""
                matched = None
                for ename, eid in candidates:
                    eparts = norm(ename).split()
                    efirst_init = eparts[0][0] if eparts else ""
                    if pfirst_init == efirst_init:
                        matched = (ename, eid)
                        break
                if matched:
                    norm_matches += 1
                    continue
        
        # No match
        no_match += 1
        if no_match <= 3:  # Show first 3 unmatched
            plast_str = plast if plast else "(no parts)"
            candidates = espn_by_last.get(plast, [])
            cand_str = ", ".join([n for n, _ in candidates[:3]]) if candidates else "NONE"
            print(f"  NO MATCH: '{pname}' (norm='{pnorm}') -> last='{plast_str}' -> ESPN candidates: [{cand_str}]")
    
    print(f"  Results: exact={exact_matches}, last_name={last_name_matches}, norm={norm_matches}, no_match={no_match}")
