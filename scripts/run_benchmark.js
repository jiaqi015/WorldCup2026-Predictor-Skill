#!/usr/bin/env node
/**
 * Prediction Engine Benchmark
 * 15 matches × 100 simulations, 4 calibration dimensions
 *
 * Ground truth: COMPLETE_ODDS implied probabilities + Over/Under lines
 * Metrics: Brier Score, KL Divergence, Goal Rate Alignment, Completed Match Accuracy
 * Extra: Player threat Spearman correlation, Strength gradient consistency
 */

const fs = require('fs');
const path = require('path');

// ═══════════════════════════════════════════════════════
// 1. DATA EXTRACTION
// ═══════════════════════════════════════════════════════

const INDEX = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(INDEX, 'utf-8');

function extractVar(name) {
  const ml = new RegExp(`var\\s+${name}\\s*=\\s*(\\{[^;]*\\});`, 's');
  const m = html.match(ml);
  if (!m) return null;
  try { return JSON.parse(m[1]); }
  catch { try { return eval('(' + m[1] + ')'); } catch { return null; } }
}

const STRENGTH     = extractVar('STRENGTH') || {};
const PTM          = extractVar('PLAYER_THREATS_MAP') || {};
const CO           = extractVar('COMPLETE_ODDS') || {};
const GOAL_W       = extractVar('GOAL_W') || {};
const ASSIST_W     = extractVar('ASSIST_W') || {};
const PL           = extractVar('PL') || {};
const POS          = extractVar('POS') || {};
const ELO          = extractVar('ELO_RATINGS') || {};
const POWER        = extractVar('POWER_SCORES') || {};

// Load match schedule for over/under and completed match data
const SCHEDULE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'matches', 'match_schedule.json'), 'utf-8'));
const DETAILS  = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'matches', 'match_details.json'), 'utf-8'));

// ═══════════════════════════════════════════════════════
// 2. ENGINE FUNCTIONS (extracted from index.html)
// ═══════════════════════════════════════════════════════

function normalize(obj) {
  const t = Object.values(obj).reduce((a, b) => a + b, 0);
  if (t <= 0) return obj;
  const o = {};
  for (const k in obj) o[k] = obj[k] / t;
  return o;
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

function strengthPrior(hs, as, draw) {
  const d = hs - as;
  const h = Math.exp(d * 0.22), a = Math.exp(-d * 0.22);
  const dr = draw ? Math.max(0.38, 0.60 - Math.abs(d) * 0.06) : 0;
  return { home: h, draw: dr, away: a };
}

function normalizeOddsMarket(market, matchId) {
  const co = matchId && CO[matchId] ? CO[matchId] : null;
  if (co) return normalize({ home: 1/co.h, draw: 1/co.d, away: 1/co.a });
  if (!market) return null;
  const imp = {};
  if (Number(market.home) > 1) imp.home = 1 / Number(market.home);
  if (Number(market.draw) > 1) imp.draw = 1 / Number(market.draw);
  if (Number(market.away) > 1) imp.away = 1 / Number(market.away);
  if (!imp.home || !imp.away) return null;
  return normalize(imp);
}

function estimateProb(home, away, matchId, mode) {
  const hs = STRENGTH[home] || 3, as = STRENGTH[away] || 3;
  const draw = true;
  let p;
  if (mode === 'random') {
    p = { home: 1, draw: 1, away: 1 };
  } else {
    p = normalizeOddsMarket(null, matchId) || strengthPrior(hs, as, draw);
  }
  return normalize(p);
}

function sampleOutcome(probs, rng) {
  const r = rng();
  if (r < probs.home) return 'home';
  if (r < probs.home + (probs.draw || 0)) return 'draw';
  return 'away';
}

// Goal sampling using the updated distribution
function sampleGoals(rng) {
  const dist = [0,0,0,0,0,1,1,1,1,1,1,2,2,2,3,3,4];
  return dist[Math.floor(rng() * dist.length)];
}

function weightedPick(players, team, weights, fallback, type) {
  if (!players || !players.length) return null;
  const pool = [];
  for (const p of players) {
    const pos = (POS[team] && POS[team][p]) || '中前卫';
    let w = weights[pos] !== undefined ? weights[pos] : fallback;
    if (PTM[p]) {
      const mult = type === 'assist' ? PTM[p].a : PTM[p].g;
      if (mult > 0) w = Math.max(1, Math.round(w * mult));
    }
    for (let j = 0; j < w; j++) pool.push(p);
  }
  if (!pool.length) return players[Math.floor(Math.random() * players.length)];
  return pool[Math.floor(Math.random() * pool.length)];
}

function simulateMatch(home, away, matchId) {
  const rng = Math.random;
  const probs = estimateProb(home, away, matchId, 'odds');
  const outcome = sampleOutcome(probs, rng);
  let h = sampleGoals(rng), a = sampleGoals(rng);
  const hs = STRENGTH[home] || 3, as = STRENGTH[away] || 3, diff = hs - as;
  if (diff > 0 && rng() < Math.min(0.55, diff * 0.12)) h++;
  if (diff < 0 && rng() < Math.min(0.55, Math.abs(diff) * 0.12)) a++;
  if (outcome === 'home' && h <= a) { a = Math.floor(rng() * 2); h = a + 1; }
  else if (outcome === 'away' && a <= h) { h = Math.floor(rng() * 2); a = h + 1; }
  else if (outcome === 'draw') { const d = Math.min(3, Math.round((h + a) / 2)); h = d; a = d; }
  h = clamp(h, 0, 9); a = clamp(a, 0, 9);

  // Scorers
  const hPlayers = (PL[home] || []).filter(p => {
    const pos = (POS[home] && POS[home][p]) || '';
    return pos !== '门将';
  });
  const aPlayers = (PL[away] || []).filter(p => {
    const pos = (POS[away] && POS[away][p]) || '';
    return pos !== '门将';
  });

  const scorers = [];
  const assisters = [];
  for (let i = 0; i < h; i++) {
    const sc = weightedPick(hPlayers, home, GOAL_W, 3, 'goal');
    if (sc) scorers.push(sc);
    if (rng() > 0.35) {
      const pool = hPlayers.filter(x => x !== sc);
      const asst = weightedPick(pool, home, ASSIST_W, 3, 'assist');
      if (asst) assisters.push(asst);
    }
  }
  for (let i = 0; i < a; i++) {
    const sc = weightedPick(aPlayers, away, GOAL_W, 3, 'goal');
    if (sc) scorers.push(sc);
    if (rng() > 0.35) {
      const pool = aPlayers.filter(x => x !== sc);
      const asst = weightedPick(pool, away, ASSIST_W, 3, 'assist');
      if (asst) assisters.push(asst);
    }
  }

  return { h, a, outcome: h > a ? 'home' : a > h ? 'away' : 'draw', probs, scorers, assisters };
}

// ═══════════════════════════════════════════════════════
// 3. TEST MATRIX — 15 matches
// ═══════════════════════════════════════════════════════

const TEST_MATCHES = [
  // Completed (hard ground truth)
  { id: '760415', h: '墨西哥', a: '南非',   cat: 'completed', actual: { h: 2, a: 0 } },
  { id: '760414', h: '韩国',   a: '捷克',   cat: 'completed', actual: { h: 2, a: 1 } },
  // Big mismatches (diff ≥ 2.0)
  { id: '760443', h: '西班牙', a: '佛得角', cat: 'mismatch' },
  { id: '760440', h: '巴西',   a: '海地',   cat: 'mismatch' },
  { id: '760446', h: '法国',   a: '伊拉克', cat: 'mismatch' },
  // Medium (diff 1.0-1.5)
  { id: '760453', h: '阿根廷', a: '奥地利', cat: 'medium' },
  { id: '760435', h: '德国',   a: '科特迪瓦', cat: 'medium' },
  { id: '760460', h: '英格兰', a: '加纳',   cat: 'medium' },
  // Close (diff < 0.5)
  { id: '760417', h: '巴拉圭', a: '澳大利亚', cat: 'close' },
  { id: '760429', h: '瑞典',   a: '突尼斯', cat: 'close' },
  { id: '760436', h: '科特迪瓦', a: '厄瓜多尔', cat: 'close' },
  { id: '760462', h: '加纳',   a: '巴拿马', cat: 'close' },
  // Away favorites
  { id: '760455', h: '约旦',   a: '阿根廷', cat: 'away_fav' },
  { id: '760420', h: '卡塔尔', a: '瑞士',   cat: 'away_fav' },
  { id: '760449', h: '沙特',   a: '乌拉圭', cat: 'away_fav' },
];

// Enrich with odds ground truth
for (const m of TEST_MATCHES) {
  const oddsEntry = CO[m.id];
  const sched = SCHEDULE[m.id];
  if (oddsEntry) {
    const total = 1/oddsEntry.h + 1/oddsEntry.d + 1/oddsEntry.a;
    m.odds = {
      home: (1/oddsEntry.h) / total,
      draw: (1/oddsEntry.d) / total,
      away: (1/oddsEntry.a) / total,
    };
  }
  if (sched && sched.odds) {
    m.ou = sched.odds.overUnder;
  }
}

// ═══════════════════════════════════════════════════════
// 4. RUN BENCHMARK
// ═══════════════════════════════════════════════════════

const N = 100;
const results = [];

console.log('╔══════════════════════════════════════════════════════════════╗');
console.log('║          PREDICTION ENGINE BENCHMARK — 15 × 100             ║');
console.log('╚══════════════════════════════════════════════════════════════╝');
console.log('');
console.log(`Matches: ${TEST_MATCHES.length} | Sims per match: ${N} | Total: ${TEST_MATCHES.length * N}`);
console.log(`Ground truth: COMPLETE_ODDS implied probabilities`);
console.log('');

for (const match of TEST_MATCHES) {
  const sims = [];
  const scoreDist = {};
  const scorerFreq = {};
  const assisterFreq = {};
  let totalGoals = 0;

  for (let i = 0; i < N; i++) {
    const r = simulateMatch(match.h, match.a, match.id);
    sims.push(r);
    const key = `${r.h}-${r.a}`;
    scoreDist[key] = (scoreDist[key] || 0) + 1;
    totalGoals += r.h + r.a;
    for (const s of r.scorers) scorerFreq[s] = (scorerFreq[s] || 0) + 1;
    for (const a of r.assisters) assisterFreq[a] = (assisterFreq[a] || 0) + 1;
  }

  // Aggregate
  const homeWins = sims.filter(s => s.outcome === 'home').length;
  const draws    = sims.filter(s => s.outcome === 'draw').length;
  const awayWins = sims.filter(s => s.outcome === 'away').length;
  const simProb = {
    home: homeWins / N,
    draw: draws / N,
    away: awayWins / N,
  };
  const avgGoals = totalGoals / N;

  // Brier Score (per-match, across 3 outcomes)
  let brier = 0;
  if (match.odds) {
    brier = ((simProb.home - match.odds.home) ** 2 +
             (simProb.draw - match.odds.draw) ** 2 +
             (simProb.away - match.odds.away) ** 2) / 3;
  }

  // KL Divergence
  let kl = 0;
  if (match.odds) {
    for (const k of ['home', 'draw', 'away']) {
      const p = match.odds[k], q = simProb[k];
      if (p > 0 && q > 0) kl += p * Math.log(p / q);
    }
  }

  // Goal rate delta
  const goalDelta = match.ou ? avgGoals - match.ou : null;

  // Completed match check
  let matchResult = null;
  if (match.actual) {
    const actualOutcome = match.actual.h > match.actual.a ? 'home' :
                          match.actual.a > match.actual.h ? 'away' : 'draw';
    const simMaxOutcome = simProb.home >= simProb.draw && simProb.home >= simProb.away ? 'home' :
                          simProb.away >= simProb.draw ? 'away' : 'draw';
    matchResult = {
      actual: actualOutcome,
      simFreq: simProb[actualOutcome],
      simMax: simMaxOutcome,
      correct: simMaxOutcome === actualOutcome,
    };
  }

  // Top scorers
  const topScorers = Object.entries(scorerFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name, count]) => ({
      name,
      count,
      goal_threat: PTM[name] ? PTM[name].g : null,
      assist_threat: PTM[name] ? PTM[name].a : null,
    }));

  const entry = {
    match_id: match.id,
    home: match.h,
    away: match.a,
    category: match.cat,
    strength_diff: Math.abs((STRENGTH[match.h] || 3) - (STRENGTH[match.a] || 3)),
    odds_ground_truth: match.odds || null,
    sim_prob: simProb,
    brier_score: brier,
    kl_divergence: kl,
    avg_goals: avgGoals,
    over_under: match.ou || null,
    goal_delta: goalDelta,
    score_distribution: scoreDist,
    top_scorers: topScorers,
    completed_match: matchResult,
  };
  results.push(entry);
}

// ═══════════════════════════════════════════════════════
// 5. AGGREGATE METRICS
// ═══════════════════════════════════════════════════════

// Dimension 1: Brier Score
const brierScores = results.filter(r => r.brier_score > 0).map(r => r.brier_score);
const avgBrier = brierScores.reduce((a, b) => a + b, 0) / brierScores.length;

// Dimension 2: KL Divergence
const klScores = results.filter(r => r.kl_divergence > 0).map(r => r.kl_divergence);
const avgKL = klScores.reduce((a, b) => a + b, 0) / klScores.length;

// Dimension 3: Goal Rate Alignment
const goalDeltas = results.filter(r => r.goal_delta !== null).map(r => Math.abs(r.goal_delta));
const avgGoalDelta = goalDeltas.reduce((a, b) => a + b, 0) / goalDeltas.length;

// Dimension 4: Completed Match Accuracy
const completedResults = results.filter(r => r.completed_match);
const completedCorrect = completedResults.filter(r => r.completed_match.correct).length;

// ═══════════════════════════════════════════════════════
// 6. PLAYER THREAT CORRELATION
// ═══════════════════════════════════════════════════════

// Aggregate scorer/assister frequencies across ALL simulations
const globalScorer = {}, globalAssist = {};
for (const r of results) {
  for (const s of (r.top_scorers || [])) {
    globalScorer[s.name] = (globalScorer[s.name] || 0) + s.count;
  }
}

// Re-count from raw sims for accuracy
for (const match of TEST_MATCHES) {
  for (let i = 0; i < N; i++) {
    const r = simulateMatch(match.h, match.a, match.id);
    for (const s of r.scorers) globalScorer[s] = (globalScorer[s] || 0) + 1;
    for (const a of r.assisters) globalAssist[a] = (globalAssist[a] || 0) + 1;
  }
}

// Spearman rank correlation for goal_threat vs goal frequency
function spearman(x, y) {
  const n = x.length;
  if (n < 3) return 0;
  function rank(arr) {
    const sorted = arr.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
    const ranks = new Array(n);
    for (let i = 0; i < n; i++) ranks[sorted[i].i] = i + 1;
    return ranks;
  }
  const rx = rank(x), ry = rank(y);
  let d2 = 0;
  for (let i = 0; i < n; i++) d2 += (rx[i] - ry[i]) ** 2;
  return 1 - (6 * d2) / (n * (n * n - 1));
}

// Build threat vs frequency arrays
const threatGoalPairs = [];
for (const [name, freq] of Object.entries(globalScorer)) {
  if (PTM[name] && freq >= 2) {
    threatGoalPairs.push({ name, threat: PTM[name].g, freq });
  }
}
threatGoalPairs.sort((a, b) => b.threat - a.threat);
const goalThreatVals = threatGoalPairs.map(p => p.threat);
const goalFreqVals   = threatGoalPairs.map(p => p.freq);
const goalSpearman   = spearman(goalThreatVals, goalFreqVals);

const threatAssistPairs = [];
for (const [name, freq] of Object.entries(globalAssist)) {
  if (PTM[name] && freq >= 2) {
    threatAssistPairs.push({ name, threat: PTM[name].a, freq });
  }
}
threatAssistPairs.sort((a, b) => b.threat - a.threat);
const assistThreatVals = threatAssistPairs.map(p => p.threat);
const assistFreqVals   = threatAssistPairs.map(p => p.freq);
const assistSpearman   = spearman(assistThreatVals, assistFreqVals);

// ═══════════════════════════════════════════════════════
// 7. STRENGTH GRADIENT ANALYSIS
// ═══════════════════════════════════════════════════════

const gradientBuckets = {};
for (const r of results) {
  const diff = Math.round(r.strength_diff);
  const bucket = `diff=${diff}`;
  if (!gradientBuckets[bucket]) gradientBuckets[bucket] = { home: 0, draw: 0, away: 0, n: 0 };
  gradientBuckets[bucket].home += r.sim_prob.home;
  gradientBuckets[bucket].draw += r.sim_prob.draw;
  gradientBuckets[bucket].away += r.sim_prob.away;
  gradientBuckets[bucket].n++;
}
for (const k in gradientBuckets) {
  const b = gradientBuckets[k];
  b.home /= b.n; b.draw /= b.n; b.away /= b.n;
}

// ═══════════════════════════════════════════════════════
// 7b. KNOCKOUT STAGE TEST
// ═══════════════════════════════════════════════════════

function simulateKnockoutMatch(home, away) {
  const rng = Math.random;
  const hs = STRENGTH[home] || 3, as = STRENGTH[away] || 3;
  // Use strengthPrior with allowDraw=false for knockout
  const raw = strengthPrior(hs, as, false);
  const p = normalize(raw);
  const outcome = sampleOutcome(p, rng);
  let h = sampleGoals(rng), a = sampleGoals(rng);
  const diff = hs - as;
  if (diff > 0 && rng() < Math.min(0.55, diff * 0.12)) h++;
  if (diff < 0 && rng() < Math.min(0.55, Math.abs(diff) * 0.12)) a++;
  // Force decisive result (no draw in knockout)
  if (outcome === 'home' && h <= a) { a = Math.floor(rng() * 2); h = a + 1; }
  else if (outcome === 'away' && a <= h) { h = Math.floor(rng() * 2); a = h + 1; }
  else if (h === a) { if (rng() < 0.5) h++; else a++; }
  h = clamp(h, 0, 9); a = clamp(a, 0, 9);
  return { h, a, winner: h > a ? home : away, probs: p };
}

const KO_TEST = [
  // Favorites should win most of the time
  { h: '阿根廷', a: '奥地利',  expect: '阿根廷', label: 'ARG vs AUT (diff=2.3)' },
  { h: '西班牙', a: '佛得角',  expect: '西班牙', label: 'ESP vs CPV (diff=3.2)' },
  { h: '法国',   a: '伊拉克',  expect: '法国',   label: 'FRA vs IRQ (diff=2.4)' },
  { h: '英格兰', a: '加纳',    expect: '英格兰', label: 'ENG vs GHA (diff=2.1)' },
  { h: '德国',   a: '科特迪瓦', expect: '德国',  label: 'GER vs CIV (diff=1.2)' },
  // Close matches — either can win, just check probability is reasonable
  { h: '荷兰',   a: '日本',    expect: null, label: 'NED vs JPN (diff=0.6)' },
  { h: '比利时', a: '德国',    expect: null, label: 'BEL vs GER (diff=0.2)' },
  { h: '巴西',   a: '阿根廷',  expect: null, label: 'BRA vs ARG (diff=0.7)' },
  { h: '墨西哥', a: '韩国',    expect: null, label: 'MEX vs KOR (diff=0.5)' },
  { h: '巴拉圭', a: '澳大利亚', expect: null, label: 'PAR vs AUS (diff=0.0)' },
];

const KO_N = 100;
const koResults = [];

for (const m of KO_TEST) {
  let favWins = 0, totalGoals = 0;
  const winnerFreq = {};
  for (let i = 0; i < KO_N; i++) {
    const r = simulateKnockoutMatch(m.h, m.a);
    if (m.expect && r.winner === m.expect) favWins++;
    winnerFreq[r.winner] = (winnerFreq[r.winner] || 0) + 1;
    totalGoals += r.h + r.a;
  }
  koResults.push({
    ...m,
    favWinRate: m.expect ? favWins / KO_N : null,
    avgGoals: totalGoals / KO_N,
    winnerFreq,
  });
}

// Knockout metrics
const koFavTests = koResults.filter(r => r.expect);
const koFavAvg = koFavTests.length > 0
  ? koFavTests.reduce((a, b) => a + b.favWinRate, 0) / koFavTests.length : 0;
const koAvgGoals = koResults.reduce((a, b) => a + b.avgGoals, 0) / koResults.length;

// Check consistency: stronger team should win more often in close matches too
const koCloseTests = koResults.filter(r => !r.expect);
let koCloseConsistent = 0;
for (const r of koCloseTests) {
  const hs = STRENGTH[r.h] || 3, as = STRENGTH[r.a] || 3;
  const stronger = hs >= as ? r.h : r.a;
  const strongerRate = (r.winnerFreq[stronger] || 0) / KO_N;
  if (strongerRate >= 0.45) koCloseConsistent++;
}

// ═══════════════════════════════════════════════════════
// 8. OUTPUT
// ═══════════════════════════════════════════════════════

// --- Per-match table ---
console.log('┌─────────────────────────────────────────────────────────────────────────────────────────────────┐');
console.log('│ MATCH                    │ STRENGTH │  ODDS (H/D/A)         │ SIM (H/D/A)         │ Brier  KL    │');
console.log('├─────────────────────────────────────────────────────────────────────────────────────────────────┤');

for (const r of results) {
  const label = `${r.home} vs ${r.away}`.padEnd(22);
  const diff = r.strength_diff.toFixed(1).padStart(5);
  const odds = r.odds_ground_truth
    ? `${(r.odds_ground_truth.home*100).toFixed(0)}/${(r.odds_ground_truth.draw*100).toFixed(0)}/${(r.odds_ground_truth.away*100).toFixed(0)}%`.padEnd(21)
    : 'N/A'.padEnd(21);
  const sim = `${(r.sim_prob.home*100).toFixed(0)}/${(r.sim_prob.draw*100).toFixed(0)}/${(r.sim_prob.away*100).toFixed(0)}%`.padEnd(19);
  const brier = r.brier_score > 0 ? r.brier_score.toFixed(4).padStart(6) : '  N/A ';
  const kl = r.kl_divergence > 0 ? r.kl_divergence.toFixed(4).padStart(6) : '  N/A ';
  const flag = r.brier_score > 0.05 ? ' ⚠' : (r.brier_score < 0.01 ? ' ✓' : '');
  console.log(`│ ${label} │ ${diff}  │ ${odds} │ ${sim} │ ${brier} ${kl} │${flag}`);
}

console.log('└─────────────────────────────────────────────────────────────────────────────────────────────────┘');
console.log('');

// --- Goal rate ---
console.log('┌──────────────────────────────────────────────────────────┐');
console.log('│ GOAL RATE: Sim avg vs O/U line                          │');
console.log('├──────────────────────────────────────────────────────────┤');
for (const r of results) {
  if (r.over_under) {
    const label = `${r.home} vs ${r.away}`.padEnd(22);
    const flag = Math.abs(r.goal_delta) < 0.3 ? '✓' : (Math.abs(r.goal_delta) > 0.8 ? '⚠' : '~');
    console.log(`│ ${label}  sim=${r.avg_goals.toFixed(2)}  O/U=${r.over_under}  Δ=${r.goal_delta >= 0 ? '+' : ''}${r.goal_delta.toFixed(2)} ${flag} │`);
  }
}
console.log('└──────────────────────────────────────────────────────────┘');
console.log('');

// --- Completed matches ---
if (completedResults.length > 0) {
  console.log('┌──────────────────────────────────────────────────────────┐');
console.log('│ COMPLETED MATCH VALIDATION (sim max = actual?)          │');
  console.log('├──────────────────────────────────────────────────────────┤');
  for (const r of completedResults) {
    const actual = r.completed_match.actual;
    const simMax = r.completed_match.simMax;
    const freq = r.completed_match.simFreq;
    const status = r.completed_match.correct ? '✓ PASS' : '✗ FAIL';
    console.log(`│ ${r.home} vs ${r.away}: actual=${actual}, sim_max=${simMax} (${(freq*100).toFixed(0)}%) [${status}] │`);
  }
  console.log('└──────────────────────────────────────────────────────────┘');
  console.log('');
}

// --- Summary metrics ---
console.log('═══════════════════════════════════════════════════════════════');
console.log('  BENCHMARK SUMMARY');
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

function gradeBrier(v) { return v < 0.01 ? 'EXCELLENT' : v < 0.03 ? 'GOOD' : v < 0.05 ? 'ACCEPTABLE' : 'POOR'; }
function gradeKL(v)    { return v < 0.05 ? 'EXCELLENT' : v < 0.15 ? 'ACCEPTABLE' : 'POOR'; }
function gradeGoals(v) { return v < 0.3 ? 'EXCELLENT' : v < 0.5 ? 'GOOD' : v < 0.8 ? 'ACCEPTABLE' : 'POOR'; }

console.log(`  D1  Brier Score (prob calibration):  ${avgBrier.toFixed(4)}  [${gradeBrier(avgBrier)}]`);
console.log(`      (avg squared diff sim vs odds, <0.01 excellent, 0.01-0.03 good, >0.05 poor)`);
console.log('');
console.log(`  D2  KL Divergence (dist divergence): ${avgKL.toFixed(4)}  [${gradeKL(avgKL)}]`);
console.log(`      (info loss from odds→sim, <0.05 excellent, 0.05-0.15 ok, >0.15 poor)`);
console.log('');
console.log(`  D3  Goal Rate Δ (vs O/U line):      ${avgGoalDelta.toFixed(2)} goals  [${gradeGoals(avgGoalDelta)}]`);
console.log(`      (avg |sim_goals - over_under|, <0.3 excellent, 0.3-0.5 good, >0.8 poor)`);
console.log('');
console.log(`  D4  Completed Match Hit:             ${completedCorrect}/${completedResults.length}`);
console.log(`      (sim's most probable outcome matches actual result)`);
console.log('');
console.log(`  Player Threat Spearman (goal):       ρ=${goalSpearman.toFixed(3)}  [${goalSpearman > 0.6 ? 'STRONG' : goalSpearman > 0.3 ? 'MODERATE' : 'WEAK'}]`);
console.log(`  Player Threat Spearman (assist):     ρ=${assistSpearman.toFixed(3)}  [${assistSpearman > 0.6 ? 'STRONG' : assistSpearman > 0.3 ? 'MODERATE' : 'WEAK'}]`);
console.log('');

// Knockout stage results
console.log('  D5  Knockout Stage (10 matchups × 100 sims):');
console.log(`      Favorite win rate (avg): ${koFavAvg >= 0.7 ? '✓' : '✗'} ${(koFavAvg*100).toFixed(1)}%  (target ≥70%)`);
console.log(`      Close match stronger team ≥45%: ${koCloseConsistent}/${koCloseTests.length}  ${koCloseConsistent >= koCloseTests.length * 0.6 ? '✓' : '✗'}`);
console.log(`      Avg goals per KO match: ${koAvgGoals.toFixed(2)}`);
console.log('');
console.log('  ┌─────────────────────────────┬───────────┬──────────┬─────────────────────┐');
console.log('  │ Match                       │ Fav Win % │ Avg Goals│ Winner Distribution  │');
console.log('  ├─────────────────────────────┼───────────┼──────────┼─────────────────────┤');
for (const r of koResults) {
  const label = r.label.padEnd(27);
  const fav = r.favWinRate !== null ? `${(r.favWinRate*100).toFixed(0)}%`.padStart(7) : '  n/a  ';
  const goals = r.avgGoals.toFixed(2).padStart(6);
  const dist = Object.entries(r.winnerFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([t, c]) => `${t.slice(0,4)}=${c}`)
    .join(' ');
  console.log(`  │ ${label}│ ${fav} │ ${goals}  │ ${dist.padEnd(19)} │`);
}
console.log('  └─────────────────────────────┴───────────┴──────────┴─────────────────────┘');
console.log('');

// Strength gradient
console.log('  Strength Gradient (avg outcome probs by STRENGTH diff):');
console.log('  ┌────────┬──────────┬──────────┬──────────┐');
console.log('  │  Diff  │  Home %  │  Draw %  │  Away %  │');
console.log('  ├────────┼──────────┼──────────┼──────────┤');
for (const [k, v] of Object.entries(gradientBuckets).sort()) {
  console.log(`  │ ${k.padEnd(6)} │ ${(v.home*100).toFixed(1).padStart(7)}% │ ${(v.draw*100).toFixed(1).padStart(7)}% │ ${(v.away*100).toFixed(1).padStart(7)}% │`);
}
console.log('  └────────┴──────────┴──────────┴──────────┘');
console.log('');

// Top threat players across all sims
console.log('  Top Scorers (across all 1500 sims):');
const allScorers = Object.entries(globalScorer).sort((a, b) => b[1] - a[1]).slice(0, 10);
for (const [name, count] of allScorers) {
  const t = PTM[name];
  const threatStr = t ? `goal=${t.g} assist=${t.a}` : 'no threat data';
  console.log(`    ${name.padEnd(12)} ${String(count).padStart(4)} goals  (${threatStr})`);
}
console.log('');

// Final verdict
const passCriteria = [
  { name: 'Brier < 0.05', pass: avgBrier < 0.05 },
  { name: 'KL < 0.15', pass: avgKL < 0.15 },
  { name: 'Goal Δ < 0.8', pass: avgGoalDelta < 0.8 },
  { name: 'Completed ≥ 1/2', pass: completedCorrect >= 1 },
  { name: 'KO Fav ≥ 70%', pass: koFavAvg >= 0.70 },
  { name: 'Goal Spearman > 0.3', pass: goalSpearman > 0.3 },
];
const allPass = passCriteria.every(c => c.pass);

console.log('═══════════════════════════════════════════════════════════════');
console.log(`  VERDICT: ${allPass ? '✓ PASS — Engine is well-calibrated' : '✗ NEEDS_CALIBRATION — Some metrics out of range'}`);
console.log('═══════════════════════════════════════════════════════════════');
console.log('');
for (const c of passCriteria) {
  console.log(`  [${c.pass ? '✓' : '✗'}] ${c.name}`);
}

// ═══════════════════════════════════════════════════════
// 9. SAVE JSON REPORT
// ═══════════════════════════════════════════════════════

const report = {
  benchmark_version: 2,
  run_at: new Date().toISOString(),
  config: { matches: TEST_MATCHES.length, sims_per_match: N, total_sims: TEST_MATCHES.length * N },
  summary: {
    brier_score: { value: avgBrier, grade: gradeBrier(avgBrier) },
    kl_divergence: { value: avgKL, grade: gradeKL(avgKL) },
    goal_rate_delta: { value: avgGoalDelta, grade: gradeGoals(avgGoalDelta) },
    completed_match_hit: { correct: completedCorrect, total: completedResults.length },
    player_threat_spearman: { goal: goalSpearman, assist: assistSpearman },
    verdict: allPass ? 'PASS' : 'NEEDS_CALIBRATION',
    criteria: passCriteria,
  },
  strength_gradient: gradientBuckets,
  knockout_stage: {
    n_sims: KO_N,
    favorite_win_rate_avg: koFavAvg,
    close_match_consistent: koCloseConsistent,
    close_match_total: koCloseTests.length,
    avg_goals: koAvgGoals,
    matches: koResults.map(r => ({
      home: r.h, away: r.a, label: r.label,
      expect: r.expect, fav_win_rate: r.favWinRate,
      avg_goals: r.avgGoals, winner_freq: r.winnerFreq,
    })),
  },
  per_match: results.map(r => ({
    match_id: r.match_id, home: r.home, away: r.away, category: r.category,
    strength_diff: r.strength_diff, odds: r.odds_ground_truth, sim_prob: r.sim_prob,
    brier: r.brier_score, kl: r.kl_divergence, avg_goals: r.avg_goals,
    over_under: r.over_under, goal_delta: r.goal_delta,
    completed: r.completed_match, top_scorers: r.top_scorers,
  })),
  top_scorers_global: allScorers.map(([name, count]) => ({
    name, count, goal_threat: PTM[name]?.g || null, assist_threat: PTM[name]?.a || null,
  })),
};

const outPath = path.join(__dirname, '..', 'data', 'prediction', 'benchmark_results.json');
fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
console.log(`\n  Report saved to ${outPath}`);
