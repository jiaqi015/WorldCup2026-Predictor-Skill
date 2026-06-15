#!/usr/bin/env python3
"""
Goal Model Backtest: Poisson vs Fixed Distribution
Monte Carlo comparison of the new dual-Poisson model against the old fixed-array model.
Metrics: RPS, Log-loss, Brier score, Total goals MAE.
Grid search over POISSON_BASE_TOTAL x POISSON_SUPREMACY_K.
"""

import json
import math
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
DETAILS = ROOT / "data" / "matches" / "match_details.json"
SCHEDULE = ROOT / "data" / "matches" / "match_schedule.json"
OUT_DIR = ROOT / "data" / "prediction"
OUT_FILE = OUT_DIR / "goal_model_backtest.json"

# ─── Data Loading ─────────────────────────────────────

def extract_strength(html: str) -> dict:
    m = re.search(r'var\s+STRENGTH\s*=\s*(\{[^;]+\});', html)
    if not m:
        raise RuntimeError("STRENGTH not found in index.html")
    return json.loads(m.group(1))

def load_completed_matches() -> list:
    with open(DETAILS, "r", encoding="utf-8") as f:
        details = json.load(f)
    with open(SCHEDULE, "r", encoding="utf-8") as f:
        schedule = json.load(f)
    matches = []
    for mid, det in details.items():
        sch = schedule.get(mid, {})
        matches.append({
            "matchId": mid,
            "home": det.get("homeTeamCn", sch.get("home", "")),
            "away": det.get("awayTeamCn", sch.get("away", "")),
            "homeScore": det["homeScore"],
            "awayScore": det["awayScore"],
            "totalGoals": det["homeScore"] + det["awayScore"],
            "outcome": "home" if det["homeScore"] > det["awayScore"]
                       else "away" if det["homeScore"] < det["awayScore"]
                       else "draw"
        })
    return matches

# ─── Model Implementations ────────────────────────────

WW = [0,0,0,0,0,1,1,1,1,1,1,2,2,2,3,3,4]

def sample_goals_old(rng):
    return WW[int(rng() * len(WW))]

def sample_poisson(lam: float, rng) -> int:
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng()
        k += 1
        if p <= L:
            return k - 1

def compute_lambdas(hs: float, as_: float, base_total: float, k: float):
    diff = hs - as_
    lh = max(0.15, min(5.0, (base_total / 2) * math.exp(k * diff)))
    la = max(0.15, min(5.0, (base_total / 2) * math.exp(-k * diff)))
    return lh, la

def simulate_old(strengths, home, away, rng, N=10000):
    """Old model: fixed distribution + outcome override."""
    hs = strengths.get(home, 3.0)
    as_ = strengths.get(away, 3.0)
    diff = hs - as_
    results = []
    for _ in range(N):
        h = sample_goals_old(rng)
        a = sample_goals_old(rng)
        if diff > 0 and rng() < min(0.55, diff * 0.12):
            h += 1
        if diff < 0 and rng() < min(0.55, abs(diff) * 0.12):
            a += 1
        # outcome override (simplified: estimate strength prior outcome)
        h_prior = math.exp(diff * 0.85)
        a_prior = math.exp(-diff * 0.85)
        d_prior = max(0.22, 0.44 - abs(diff) * 0.07)
        total_p = h_prior + d_prior + a_prior
        r = rng() * total_p
        if r < h_prior:
            if h <= a:
                a = int(rng() * 2)
                h = a + 1
        elif r < h_prior + d_prior:
            d = min(3, round((h + a) / 2))
            h = d
            a = d
        else:
            if a <= h:
                h = int(rng() * 2)
                a = h + 1
        h = max(0, min(9, h))
        a = max(0, min(9, a))
        results.append((h, a))
    return results

def simulate_new(strengths, home, away, rng, base_total=2.6, k=0.45, N=10000):
    """New model: dual Poisson."""
    hs = strengths.get(home, 3.0)
    as_ = strengths.get(away, 3.0)
    lh, la = compute_lambdas(hs, as_, base_total, k)
    results = []
    for _ in range(N):
        h = max(0, min(9, sample_poisson(lh, rng)))
        a = max(0, min(9, sample_poisson(la, rng)))
        results.append((h, a))
    return results

# ─── Metrics ──────────────────────────────────────────

def compute_metrics(results: list, actual_home: int, actual_away: int, actual_outcome: str) -> dict:
    N = len(results)
    # Outcome probabilities
    home_w = draw_w = away_w = 0
    total_goals_sum = 0
    for h, a in results:
        if h > a:
            home_w += 1
        elif h == a:
            draw_w += 1
        else:
            away_w += 1
        total_goals_sum += h + a
    p_home = home_w / N
    p_draw = draw_w / N
    p_away = away_w / N
    avg_goals = total_goals_sum / N

    # Actual outcome as vector
    if actual_outcome == "home":
        y = [1, 0, 0]
    elif actual_outcome == "draw":
        y = [0, 1, 0]
    else:
        y = [0, 0, 1]
    p = [p_home, p_draw, p_away]

    # Brier score (multiclass)
    brier = sum((p[i] - y[i]) ** 2 for i in range(3))

    # Log loss
    eps = 1e-10
    log_loss = -sum(y[i] * math.log(max(p[i], eps)) for i in range(3))

    # RPS (Ranked Probability Score)
    cum_p = [p[0], p[0] + p[1], 1.0]
    cum_y = [y[0], y[0] + y[1], 1.0]
    rps = sum((cum_p[i] - cum_y[i]) ** 2 for i in range(3)) / 2

    # Total goals MAE
    goals_mae = abs(avg_goals - (actual_home + actual_away))

    return {
        "p_home": round(p_home, 4),
        "p_draw": round(p_draw, 4),
        "p_away": round(p_away, 4),
        "avg_goals": round(avg_goals, 2),
        "brier": round(brier, 4),
        "log_loss": round(log_loss, 4),
        "rps": round(rps, 4),
        "goals_mae": round(goals_mae, 2)
    }

# ─── Main ─────────────────────────────────────────────

def main():
    N = int(os.environ.get("BACKTEST_N", 10000))
    seed = 42
    rng = random.Random(seed).random

    with open(HTML, "r", encoding="utf-8") as f:
        html = f.read()
    strengths = extract_strength(html)
    matches = load_completed_matches()

    if not matches:
        print("No completed matches to backtest.")
        return

    print(f"=== Goal Model Backtest ({len(matches)} matches, N={N}) ===\n")

    # Per-match results
    match_results = []
    old_rps_sum = new_rps_sum = 0
    old_goals_mae_sum = new_goals_mae_sum = 0

    for m in matches:
        rng_old = random.Random(seed).random
        rng_new = random.Random(seed).random
        old_res = simulate_old(strengths, m["home"], m["away"], rng_old, N)
        new_res = simulate_new(strengths, m["home"], m["away"], rng_new, N=N)
        old_met = compute_metrics(old_res, m["homeScore"], m["awayScore"], m["outcome"])
        new_met = compute_metrics(new_res, m["homeScore"], m["awayScore"], m["outcome"])
        old_rps_sum += old_met["rps"]
        new_rps_sum += new_met["rps"]
        old_goals_mae_sum += old_met["goals_mae"]
        new_goals_mae_sum += new_met["goals_mae"]

        print(f"{m['home']} {m['homeScore']}-{m['awayScore']} {m['away']} (id:{m['matchId']})")
        print(f"  Old: RPS={old_met['rps']:.4f}  Brier={old_met['brier']:.4f}  "
              f"LogLoss={old_met['log_loss']:.4f}  GoalsMAE={old_met['goals_mae']:.2f}  "
              f"P={old_met['p_home']:.2f}/{old_met['p_draw']:.2f}/{old_met['p_away']:.2f}  "
              f"AvgGoals={old_met['avg_goals']:.2f}")
        print(f"  New: RPS={new_met['rps']:.4f}  Brier={new_met['brier']:.4f}  "
              f"LogLoss={new_met['log_loss']:.4f}  GoalsMAE={new_met['goals_mae']:.2f}  "
              f"P={new_met['p_home']:.2f}/{new_met['p_draw']:.2f}/{new_met['p_away']:.2f}  "
              f"AvgGoals={new_met['avg_goals']:.2f}")
        print()

        match_results.append({
            "matchId": m["matchId"],
            "home": m["home"],
            "away": m["away"],
            "actual": f"{m['homeScore']}-{m['awayScore']}",
            "old_model": old_met,
            "new_model": new_met
        })

    # Aggregate
    n = len(matches)
    agg = {
        "old_model": {
            "avg_rps": round(old_rps_sum / n, 4),
            "avg_goals_mae": round(old_goals_mae_sum / n, 2)
        },
        "new_model": {
            "avg_rps": round(new_rps_sum / n, 4),
            "avg_goals_mae": round(new_goals_mae_sum / n, 2)
        }
    }
    print(f"=== Aggregate ===")
    print(f"Old: avg RPS={agg['old_model']['avg_rps']:.4f}  avg GoalsMAE={agg['old_model']['avg_goals_mae']:.2f}")
    print(f"New: avg RPS={agg['new_model']['avg_rps']:.4f}  avg GoalsMAE={agg['new_model']['avg_goals_mae']:.2f}")
    improvement = (agg['old_model']['avg_rps'] - agg['new_model']['avg_rps']) / max(agg['old_model']['avg_rps'], 1e-10) * 100
    print(f"RPS improvement: {improvement:+.1f}%")
    print()

    # Grid search
    print("=== Grid Search ===")
    grid = []
    for base_total in [2.4, 2.6, 2.8]:
        for k in [0.35, 0.45, 0.55]:
            rps_sum = goals_mae_sum = 0
            for m in matches:
                rng_gs = random.Random(seed).random
                res = simulate_new(strengths, m["home"], m["away"], rng_gs, base_total, k, N)
                met = compute_metrics(res, m["homeScore"], m["awayScore"], m["outcome"])
                rps_sum += met["rps"]
                goals_mae_sum += met["goals_mae"]
            grid.append({
                "base_total": base_total, "k": k,
                "avg_rps": round(rps_sum / n, 4),
                "avg_goals_mae": round(goals_mae_sum / n, 2)
            })

    best = min(grid, key=lambda g: g["avg_rps"])
    for g in grid:
        marker = " <== BEST" if g is best else ""
        print(f"  BASE={g['base_total']} K={g['k']:.2f}  RPS={g['avg_rps']:.4f}  GoalsMAE={g['avg_goals_mae']:.2f}{marker}")
    print(f"\nBest params: BASE_TOTAL={best['base_total']}, K={best['k']}")

    # Write output
    output = {
        "run_date": "2026-06-15",
        "matches_tested": len(matches),
        "simulations_per_match": N,
        "seed": seed,
        "matches": match_results,
        "aggregate": agg,
        "grid_search": grid,
        "best_params": {
            "POISSON_BASE_TOTAL": best["base_total"],
            "POISSON_SUPREMACY_K": best["k"]
        }
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nResults written to {OUT_FILE}")

if __name__ == "__main__":
    main()
