import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function loadPredictionEngine() {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const match = html.match(/var PredictionEngine=\(function\(\)\{([\s\S]*?)\n\}\)\(\);/);
  assert.ok(match, "PredictionEngine IIFE must be present in index.html");
  return Function(`${match[0]}\nreturn PredictionEngine;`)();
}

function fixedRng(values) {
  let index = 0;
  return () => {
    const value = values[index % values.length];
    index += 1;
    return value;
  };
}

function seededRng(seed = 123456789) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

const strengths = {
  "强队": 5,
  "中队": 3,
  "弱队": 1,
};

test("defines the architecture contracts for entities and prediction modes", () => {
  const engine = loadPredictionEngine();

  assert.equal(engine.ENGINE_SCHEMA_VERSION, 3);
  assert.deepEqual(engine.PREDICTION_MODES.map((mode) => mode.id), [
    "random",
    "strength",
    "ensemble",
  ]);
  assert.deepEqual(engine.GAMEPLAY_MODES.map((mode) => mode.id), [
    "normal",
    "clone",
    "chaos",
  ]);

  const team = engine.createTeamEntity({
    id: "arg",
    name: "阿根廷",
    strengthTier: 5,
    worldRanking: 1,
    coach: { name: "Scaloni" },
    players: [{ id: "messi", name: "梅西", position: "前腰" }],
  });
  assert.equal(team.kind, "Team");
  assert.equal(team.coach.kind, "Coach");
  assert.equal(team.players[0].kind, "Player");

  const match = engine.createMatchEntity({
    id: "m1",
    homeTeam: team,
    awayTeam: engine.createTeamEntity({ id: "mex", name: "墨西哥" }),
    stage: "group",
  });
  assert.equal(match.kind, "Match");
  assert.equal(match.homeTeam.id, "arg");
});

test("normalizes decimal odds into implied probabilities", () => {
  const engine = loadPredictionEngine();
  const probabilities = engine.normalizeOddsMarket({
    home: 2,
    draw: 4,
    away: 4,
  });

  assert.equal(Math.round(probabilities.home * 100), 50);
  assert.equal(Math.round(probabilities.draw * 100), 25);
  assert.equal(Math.round(probabilities.away * 100), 25);
});

test("strength mode gives the stronger team a higher no-draw win probability", () => {
  const engine = loadPredictionEngine();
  const probabilities = engine.estimateOutcomeProbabilities({
    predictionMode: "strength",
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
  });

  assert.ok(probabilities.home > probabilities.away);
  assert.equal(probabilities.draw, 0);
  assert.equal(Math.round((probabilities.home + probabilities.away) * 1000), 1000);
  // Calibrated against the tuned strengthPrior coefficient (0.85): diff=4 → home≈0.999.
  assert.ok(probabilities.home > 0.99 && probabilities.home < 1);
});

test("strength calibration follows the documented knockout curve", () => {
  const engine = loadPredictionEngine();
  // Curve recalibrated to the tuned strengthPrior coefficient (0.85).
  const expected = [0.5, 0.846, 0.968, 0.994, 0.999];

  for (let diff = 0; diff <= 4; diff += 1) {
    const probabilities = engine.estimateOutcomeProbabilities({
      predictionMode: "strength",
      allowDraw: false,
      homeTeam: { strengthTier: 3 + diff },
      awayTeam: { strengthTier: 3 },
    });
    assert.ok(
      Math.abs(probabilities.home - expected[diff]) < 0.006,
      `strength difference ${diff} should stay calibrated`,
    );
  }
});

test("strength mode blends market, strength, and ranking inputs", () => {
  const engine = loadPredictionEngine();
  const probabilities = engine.estimateOutcomeProbabilities({
    predictionMode: "strength",
    allowDraw: true,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
    rankings: { 强队: 1, 弱队: 80 },
    oddsMarket: { home: 8, draw: 5, away: 1.5 },
  });

  const marketOnly = engine.normalizeOddsMarket({ home: 8, draw: 5, away: 1.5 });
  assert.ok(probabilities.away > probabilities.home, "market signal should remain meaningful");
  assert.ok(
    probabilities.away < marketOnly.away,
    "team strength and ranking should temper an extreme market signal",
  );
  assert.equal(Math.round((probabilities.home + probabilities.draw + probabilities.away) * 1000), 1000);
});

test("chaos gameplay shifts strength-mode probability toward the underdog", () => {
  const engine = loadPredictionEngine();
  const normal = engine.estimateOutcomeProbabilities({
    predictionMode: "strength",
    gameplayMode: "normal",
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
  });
  const chaos = engine.estimateOutcomeProbabilities({
    predictionMode: "strength",
    gameplayMode: "chaos",
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
  });

  assert.ok(chaos.away > normal.away);
});

test("winner-only match simulations never draw and match the sampled outcome", () => {
  const engine = loadPredictionEngine();
  const result = engine.simulateMatch({
    predictionMode: "strength",
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
    rng: fixedRng([0.01, 0.20, 0.10, 0.70, 0.30, 0.90]),
  });

  assert.notEqual(result.homeGoals, result.awayGoals);
  assert.equal(result.outcome, result.homeGoals > result.awayGoals ? "home" : "away");
  assert.ok(result.probabilities.home > result.probabilities.away);
  assert.equal(result.kind, "Prediction");
  assert.deepEqual(result.scoreline, {
    home: result.homeGoals,
    away: result.awayGoals,
  });
  assert.ok(result.halfTimeScore.home <= result.homeGoals);
  assert.ok(result.halfTimeScore.away <= result.awayGoals);
  assert.ok(Array.isArray(result.events));
  assert.ok(Array.isArray(result.explain));
});

test("goal events are the score source of truth and support own goals", () => {
  const engine = loadPredictionEngine();
  const events = engine.buildScoreEvents(1, 0, fixedRng([0.1, 0.01, 0.8]), {
    ownGoalShare: 1,
    penaltyGoalShare: 0,
  });

  assert.equal(events.length, 1);
  assert.equal(events[0].type, "own_goal");
  assert.equal(events[0].team, "home");
  assert.equal(events[0].scoringTeam, "home");
  assert.equal(events[0].playerTeam, "away");
  assert.equal(events[0].period, "regular");
  assert.deepEqual(engine.deriveScorelineFromEvents(events), { home: 1, away: 0 });
});

test("penalty goals are explicit match events, not plain goals", () => {
  const engine = loadPredictionEngine();
  const events = engine.buildScoreEvents(1, 0, fixedRng([0.2, 0.6, 0.01]), {
    ownGoalShare: 0,
    penaltyGoalShare: 1,
  });

  assert.equal(events.length, 1);
  assert.equal(events[0].type, "penalty_goal");
  assert.equal(events[0].team, "home");
  assert.equal(events[0].assist, null);
  assert.deepEqual(engine.deriveScorelineFromEvents(events), { home: 1, away: 0 });
});

test("knockout simulation models regulation, extra time, and shootout resolution", () => {
  const engine = loadPredictionEngine();
  const extraTimeWin = engine.simulateKnockoutMatch({
    homeTeam: "强队",
    awayTeam: "中队",
    regulationScoreline: { home: 0, away: 0 },
    extraTimeScoreline: { home: 1, away: 0 },
    rng: fixedRng([0.2, 0.7, 0.4, 0.9]),
  });

  assert.equal(extraTimeWin.decidedBy, "extraTime");
  assert.deepEqual(extraTimeWin.regulation, { home: 0, away: 0 });
  assert.deepEqual(extraTimeWin.extraTime, { home: 1, away: 0 });
  assert.deepEqual(extraTimeWin.scoreline, { home: 1, away: 0 });
  assert.equal(extraTimeWin.winnerSide, "home");

  const result = engine.simulateKnockoutMatch({
    homeTeam: "强队",
    awayTeam: "中队",
    regulationScoreline: { home: 1, away: 1 },
    extraTimeScoreline: { home: 0, away: 0 },
    shootoutResult: { home: 4, away: 3 },
    rng: fixedRng([0.2, 0.7, 0.4, 0.9]),
  });

  assert.equal(result.kind, "KnockoutPrediction");
  assert.equal(result.decidedBy, "shootout");
  assert.equal(result.homeGoals, result.awayGoals);
  assert.deepEqual(result.regulation, { home: 1, away: 1 });
  assert.deepEqual(result.extraTime, { home: 0, away: 0 });
  assert.deepEqual(result.scoreline, { home: 1, away: 1 });
  assert.deepEqual(result.shootout.scoreline, { home: 4, away: 3 });
  assert.equal(result.winnerSide, "home");
  assert.equal(result.outcome, "home");
  assert.ok(result.events.every((event) => event.period !== "shootout"));
});

test("all prediction modes are implemented with a shared output contract", () => {
  const engine = loadPredictionEngine();
  for (const mode of engine.PREDICTION_MODES) {
    assert.deepEqual(mode.capabilities, [
      "winner",
      "scoreline",
      "goals",
      "assists",
      "cards",
      "halfTimeScore",
    ]);
    assert.equal(mode.status, "implemented");
  }
});

test("random mode is strength-neutral and strength mode uses supplied ranks", () => {
  const engine = loadPredictionEngine();
  const random = engine.estimateOutcomeProbabilities({
    predictionMode: "random",
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
  });
  assert.equal(random.home, 0.5);
  assert.equal(random.away, 0.5);

  const ranked = engine.estimateOutcomeProbabilities({
    predictionMode: "strength",
    allowDraw: false,
    homeTeam: "同级甲",
    awayTeam: "同级乙",
    strengths: { 同级甲: 3, 同级乙: 3 },
    rankings: { 同级甲: 80, 同级乙: 1 },
  });
  assert.ok(ranked.away > ranked.home);
});

test("ensemble mode accepts structured provider probabilities", () => {
  const engine = loadPredictionEngine();
  const probabilities = engine.estimateOutcomeProbabilities({
    predictionMode: "ensemble",
    allowDraw: true,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
    aiProbabilities: { home: 0.1, draw: 0.2, away: 0.7 },
  });
  assert.equal(Math.round(probabilities.home * 10), 1);
  assert.equal(Math.round(probabilities.draw * 10), 2);
  assert.equal(Math.round(probabilities.away * 10), 7);
});

test("ensemble provider probabilities drive simulated score outcomes", () => {
  const engine = loadPredictionEngine();
  assert.equal(engine.POISSON_BASE_TOTAL, 2.4);
  const rng = seededRng(20260616);
  const counts = { home: 0, draw: 0, away: 0 };
  const simulations = 2000;
  for (let i = 0; i < simulations; i += 1) {
    const result = engine.simulateMatch({
      predictionMode: "ensemble",
      allowDraw: true,
      homeTeam: "强队",
      awayTeam: "弱队",
      strengths,
      aiProbabilities: { home: 0.05, draw: 0.1, away: 0.85 },
      rng,
    });
    counts[result.outcome] += 1;
    assert.equal(
      result.outcome,
      result.homeGoals > result.awayGoals
        ? "home"
        : result.awayGoals > result.homeGoals
          ? "away"
          : "draw",
    );
  }
  assert.ok(counts.away / simulations > 0.8, JSON.stringify(counts));
  assert.ok(counts.home / simulations < 0.1, JSON.stringify(counts));
});

test("ensemble calibration is distinct from the strength model", () => {
  const engine = loadPredictionEngine();
  const options = {
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
    rankings: { 强队: 1, 弱队: 80 },
  };
  const strength = engine.estimateOutcomeProbabilities({
    ...options,
    predictionMode: "strength",
  });
  const ensemble = engine.estimateOutcomeProbabilities({
    ...options,
    predictionMode: "ensemble",
  });

  assert.ok(ensemble.home < strength.home);
  assert.ok(ensemble.home > 0.5);
});

test("legacy prediction mode ids migrate to the consolidated strategies", () => {
  const engine = loadPredictionEngine();
  const options = {
    allowDraw: false,
    homeTeam: "强队",
    awayTeam: "弱队",
    strengths,
    rankings: { 强队: 1, 弱队: 80 },
  };
  assert.deepEqual(
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "odds" }),
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "strength" }),
  );
  assert.deepEqual(
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "worldRanking" }),
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "strength" }),
  );
  assert.deepEqual(
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "aiReasoning" }),
    engine.estimateOutcomeProbabilities({ ...options, predictionMode: "ensemble" }),
  );
});
