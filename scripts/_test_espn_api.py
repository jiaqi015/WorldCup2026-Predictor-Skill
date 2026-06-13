#!/usr/bin/env python3
"""Test ESPN API with SSL context workaround."""
import urllib.request, json, time, ssl

def fetch_team(team_id, team_name):
    url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster'
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read().decode('utf-8'))
        athletes = data.get('athletes', [])
        with_hs = sum(1 for a in athletes if a.get('headshot', {}).get('href'))
        no_hs = sum(1 for a in athletes if not a.get('headshot', {}).get('href'))
        print(f'  {team_name}: {len(athletes)} athletes, {with_hs} with headshot, {no_hs} without')
        
        # Print first few athlete names
        for a in athletes[:3]:
            name = a.get('displayName', '')
            hs = a.get('headshot', {})
            hs_url = hs.get('href', 'NONE') if hs else 'NONE'
            print(f'    {name!r} -> {hs_url[:80] if hs_url else "NONE"}')
        return athletes
    except Exception as e:
        print(f'  {team_name}: ERROR - {e}')
        return None

teams = [
    ("624", "Algeria"),
    ("202", "Argentina"),
    ("1566", "Australia"),
    ("478", "Austria"),
    ("174", "Belgium"),
    ("205", "Brazil"),
]

for tid, tname in teams:
    fetch_team(tid, tname)
    time.sleep(1)
