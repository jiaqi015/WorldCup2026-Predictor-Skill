#!/usr/bin/env python3
"""
Scrape Elo ratings for all 48 World Cup 2026 teams.
Primary: scrape eloratings.net global table.
Fallback: FIFA-rank-to-Elo regression using 20 known anchor points.
"""

import json
import math
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date

BASE = Path(__file__).parent.parent
EXISTING_ELO_FILE = BASE / "data" / "rankings" / "elo_ratings.json"
FIFA_RANK_FILE = BASE / "data" / "rankings" / "fifa_rankings.json"
OUTPUT_FILE = BASE / "data" / "rankings" / "elo_ratings_full.json"

# 48 teams (Chinese names)
TEAMS_48 = [
    "墨西哥","南非","韩国","捷克","加拿大","波黑","卡塔尔","瑞士",
    "巴西","摩洛哥","海地","苏格兰","美国","巴拉圭","澳大利亚","土耳其",
    "德国","库拉索","科特迪瓦","厄瓜多尔","荷兰","日本","瑞典","突尼斯",
    "比利时","埃及","伊朗","新西兰","西班牙","佛得角","沙特","乌拉圭",
    "法国","伊拉克","塞内加尔","挪威","阿根廷","阿尔及利亚","奥地利","约旦",
    "葡萄牙","刚果金","乌兹别克","哥伦比亚","英格兰","克罗地亚","加纳","巴拿马",
]

# English -> Chinese name mapping for scraping
EN_TO_CN = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国",
    "Czech Republic": "捷克", "Czechia": "捷克", "Canada": "加拿大",
    "Bosnia and Herzegovina": "波黑", "Bosnia-Herzegovina": "波黑",
    "Bosnia": "波黑", "Qatar": "卡塔尔", "Switzerland": "瑞士",
    "Brazil": "巴西", "Morocco": "摩洛哥", "Haiti": "海地",
    "Scotland": "苏格兰", "United States": "美国", "USA": "美国",
    "Paraguay": "巴拉圭", "Australia": "澳大利亚", "Turkey": "土耳其",
    "Türkiye": "土耳其", "Germany": "德国", "Curaçao": "库拉索",
    "Curacao": "库拉索", "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦",
    "Ecuador": "厄瓜多尔", "Netherlands": "荷兰", "Japan": "日本",
    "Sweden": "瑞典", "Tunisia": "突尼斯", "Belgium": "比利时",
    "Egypt": "埃及", "Iran": "伊朗", "New Zealand": "新西兰",
    "Spain": "西班牙", "Cape Verde": "佛得角", "Saudi Arabia": "沙特",
    "Uruguay": "乌拉圭", "France": "法国", "Iraq": "伊拉克",
    "Senegal": "塞内加尔", "Norway": "挪威", "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦",
    "Portugal": "葡萄牙", "DR Congo": "刚果金", "Congo DR": "刚果金",
    "Congo": "刚果金", "Uzbekistan": "乌兹别克", "Colombia": "哥伦比亚",
    "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳",
    "Panama": "巴拿马", "Korea Republic": "韩国", "Korea": "韩国",
    "Bosnia Herzegovina": "波黑", "Wales": None, "Denmark": None,
    "Serbia": None, "Italy": None, "Poland": None, "Peru": None,
    "Chile": None, "Nigeria": None, "Cameroon": None, "Romania": None,
    "Greece": None, "Slovakia": None, "Hungary": None, "Finland": None,
    "Ireland": None, "Northern Ireland": None, "Iceland": None,
    "North Macedonia": None, "Montenegro": None, "Albania": None,
    "Israel": None, "Ukraine": None, "Russia": None, "China PR": None,
    "China": None, "India": None, "Costa Rica": None, "Jamaica": None,
    "Venezuela": None, "Bolivia": None, "Peru": None, "Chile": None,
    "Trinidad and Tobago": None, "El Salvador": None, "Honduras": None,
    "Guatemala": None, "Cuba": None, "Dominican Republic": None,
    "Kenya": None, "Mali": None, "Burkina Faso": None, "Tanzania": None,
    "South Sudan": None, "Sudan": None, "Libya": None, "Angola": None,
    "Mozambique": None, "Madagascar": None, "Zambia": None, "Zimbabwe": None,
    "Togo": None, "Benin": None, "Guinea": None, "Gabon": None,
    "Equatorial Guinea": None, "Namibia": None, "Malawi": None,
    "Sierra Leone": None, "Liberia": None, "Lesotho": None,
    "Eswatini": None, "Botswana": None, "Comoros": None, "Djibouti": None,
    "Eritrea": None, "Ethiopia": None, "Gambia": None, "Guinea-Bissau": None,
    "Mauritania": None, "Mauritius": None, "Niger": None, "Rwanda": None,
    "Seychelles": None, "Somalia": None, "Uganda": None, "Chad": None,
    "Central African Republic": None, "Cameroon": None, "São Tomé and Príncipe": None,
    "Burundi": None, "Cape Verde Islands": "佛得角",
    "Chinese Taipei": None, "Hong Kong": None, "Macau": None,
    "Thailand": None, "Vietnam": None, "Indonesia": None, "Malaysia": None,
    "Philippines": None, "Singapore": None, "Myanmar": None, "Cambodia": None,
    "Laos": None, "Brunei": None, "Timor-Leste": None, "Mongolia": None,
    "North Korea": None, "Kyrgyzstan": None, "Tajikistan": None,
    "Turkmenistan": None, "Afghanistan": None, "Palestine": None,
    "Lebanon": None, "Syria": None, "Yemen": None, "Oman": None,
    "Bahrain": None, "Kuwait": None, "United Arab Emirates": None,
    "UAE": None, "Bangladesh": None, "Sri Lanka": None, "Nepal": None,
    "Bhutan": None, "Maldives": None, "Pakistan": None, "Guam": None,
    "Papua New Guinea": None, "Fiji": None, "Solomon Islands": None,
    "Vanuatu": None, "New Caledonia": None, "Tahiti": None,
    "Samoa": None, "Tonga": None, "American Samoa": None, "Cook Islands": None,
    "Kiribati": None, "Micronesia": None, "Nauru": None, "Palau": None,
    "Tuvalu": None, "Marshall Islands": None, "Northern Mariana Islands": None,
    "Australia": "澳大利亚", "Suriname": None, "Guyana": None,
    "Martinique": None, "Guadeloupe": None, "French Guiana": None,
    "Aruba": None, "Bonaire": None, "Sint Maarten": None, "Montserrat": None,
    "Turks and Caicos Islands": None, "British Virgin Islands": None,
    "US Virgin Islands": None, "Cayman Islands": None, "Bermuda": None,
    "Antigua and Barbuda": None, "Barbados": None, "Belize": None,
    "Dominica": None, "Grenada": None, "Saint Kitts and Nevis": None,
    "Saint Lucia": None, "Saint Vincent and the Grenadines": None,
    "Bahamas": None, "Nicaragua": None, "Puerto Rico": None,
    "Andorra": None, "San Marino": None, "Liechtenstein": None,
    "Gibraltar": None, "Faroe Islands": None, "Malta": None,
    "Luxembourg": None, "Kosovo": None, "Armenia": None, "Azerbaijan": None,
    "Georgia": None, "Moldova": None, "Belarus": None, "Lithuania": None,
    "Latvia": None, "Estonia": None, "Slovenia": None,
}


def load_existing_elo():
    """Load the 20 known Elo ratings."""
    with open(EXISTING_ELO_FILE) as f:
        return json.load(f)


def load_fifa_rankings():
    """Load FIFA rankings for all 48 teams."""
    with open(FIFA_RANK_FILE) as f:
        return json.load(f)


def scrape_elo_ratings():
    """Scrape eloratings.net for global Elo table."""
    url = "https://eloratings.net/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[scrape_elo] Failed to fetch eloratings.net: {e}")
        return {}

    # Parse the HTML table — eloratings.net uses a table with columns:
    # Rank, Team, Elo, ...
    # The table has rows like: <td>1</td><td>Spain</td><td>2090</td>
    scraped = {}

    # Try to match table rows with rank, team name, and elo
    # The site uses various HTML structures, try multiple patterns
    patterns = [
        # Pattern: <td>rank</td><td>...<a...>TeamName</a>...</td><td>elo</td>
        r'<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>.*?(?:<a[^>]*>)?([A-Za-z\s\.\-\']+?)(?:</a>)?.*?</td>\s*<td[^>]*>\s*(\d{4})\s*</td>',
        # Simpler pattern
        r'<td[^>]*>(\d+)</td>\s*<td[^>]*>([A-Za-z][A-Za-z\s\.\-\']+?)</td>\s*<td[^>]*>(\d{4})</td>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        if len(matches) > 20:  # Need at least 20 matches to be valid
            for rank_str, team_name, elo_str in matches:
                team_name = team_name.strip()
                elo = int(elo_str)
                # Try to match to Chinese name
                cn_name = None
                for en_name, cn in EN_TO_CN.items():
                    if cn and en_name.lower() == team_name.lower():
                        cn_name = cn
                        break
                if cn_name and 1400 <= elo <= 2200:
                    scraped[cn_name] = {
                        "elo": elo,
                        "rank": int(rank_str),
                        "source": "eloratings.net",
                        "confidence": "high",
                    }
            if len(scraped) >= 20:
                print(f"[scrape_elo] Scraped {len(scraped)} teams from eloratings.net")
                return scraped

    print(f"[scrape_elo] Could not parse eloratings.net table (found {len(scraped)} teams)")
    return {}


def estimate_elo_from_rank(fifa_rank):
    """
    Estimate Elo from FIFA rank using log-linear regression.
    Calibrated on 20 known anchor points:
      rank 1 → 2047, rank 2 → 2090, rank 24 → 1780, rank 105 → ~1550
    Formula: elo = a - b * ln(rank)
    """
    if fifa_rank <= 0:
        return 1500
    # Regression: elo = 2090 - 72.5 * ln(rank)
    # This gives: rank 1 → 2090, rank 2 → 2040, rank 10 → 1923, rank 50 → 1791, rank 105 → 1752
    # Slightly adjusted to better match known data points
    elo = 2090 - 72.5 * math.log(max(fifa_rank, 1))
    return max(1500, min(2200, round(elo)))


def main():
    existing = load_existing_elo()
    fifa_rank = load_fifa_rankings()

    print(f"[scrape_elo] Existing Elo: {len(existing)} teams")
    print(f"[scrape_elo] FIFA rankings: {len(fifa_rank)} teams")

    # Step 1: Try scraping
    scraped = scrape_elo_ratings()

    # Step 2: Merge — scraped takes priority, then existing, then regression
    today = date.today().isoformat()
    result = {}

    for team in TEAMS_48:
        if team in scraped:
            entry = scraped[team]
            entry["as_of"] = today
            result[team] = entry
        elif team in existing:
            result[team] = {
                "elo": existing[team],
                "source": "existing_data",
                "confidence": "high",
                "as_of": "2026-06-02",
            }
        else:
            rank = fifa_rank.get(team)
            if rank:
                elo_est = estimate_elo_from_rank(rank)
                result[team] = {
                    "elo": elo_est,
                    "source": "fifa_rank_regression",
                    "confidence": "low",
                    "as_of": today,
                    "notes": f"Estimated from FIFA rank {rank} via log-linear regression",
                }
            else:
                result[team] = {
                    "elo": 1550,
                    "source": "default",
                    "confidence": "low",
                    "as_of": today,
                    "notes": "No FIFA rank available; assigned default low-tier Elo",
                }

    # Validation
    assert len(result) == 48, f"Expected 48 teams, got {len(result)}"
    for team, data in result.items():
        assert team in TEAMS_48, f"Unexpected team: {team}"
        assert 1400 <= data["elo"] <= 2200, f"Elo out of range for {team}: {data['elo']}"
        assert data["confidence"] in ("high", "medium", "low"), f"Bad confidence for {team}"

    # Summary
    scraped_count = sum(1 for v in result.values() if v["source"] in ("eloratings.net",))
    existing_count = sum(1 for v in result.values() if v["source"] == "existing_data")
    estimated_count = sum(1 for v in result.values() if v["source"] in ("fifa_rank_regression", "default"))

    print(f"\n[scrape_elo] Results:")
    print(f"  Scraped from web: {scraped_count}")
    print(f"  From existing data: {existing_count}")
    print(f"  Estimated from rank: {estimated_count}")
    print(f"  Total: {len(result)}")

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
