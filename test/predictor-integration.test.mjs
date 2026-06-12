import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("prediction model selector is wired to persistent application state", () => {
  assert.match(html, /id="predictionModeSelect"/);
  assert.match(html, /onchange="setPredictionMode\(this\.value\)"/);
  assert.match(html, /wc26_prediction_mode/);
  assert.match(html, /function setPredictionMode\(mode\)/);
});

test("gameplay modes constrain compatible prediction strategies", () => {
  assert.match(
    html,
    /if\(play==="chaos"\)return\["random"\]/,
  );
  assert.match(
    html,
    /if\(play==="normal"\)return\["odds","worldRanking","aiReasoning"\]/,
  );
  assert.match(
    html,
    /return\["random","odds","worldRanking","aiReasoning"\]/,
  );
  assert.match(
    html,
    /var nextPredictionMode=normalizePredictionMode\(mode,predictionMode\)/,
  );
});

test("desktop mode controls are anchored in the page upper-left corner", () => {
  assert.match(
    html,
    /\.mode-dock\{[^}]*position:absolute;top:58px;left:16px;/,
  );
});

test("shared match simulation uses the selected strategy and ranking provider", () => {
  const rnd = html.match(/function rnd\(draw,hTeam,aTeam(?:,matchId)?\)\{([\s\S]*?)\n\}/);
  assert.ok(rnd, "rnd application adapter must exist");
  assert.match(rnd[1], /predictionMode:predictionMode/);
  assert.match(rnd[1], /gameplayMode:playMode/);
  assert.match(rnd[1], /rankings:MODEL_RANKING/);
});

test("shared match simulation passes match ids into complete odds lookup", () => {
  assert.match(html, /function getGroupMatchId\(hTeam,aTeam\)/);
  const rnd = html.match(/function rnd\(draw,hTeam,aTeam,matchId\)\{([\s\S]*?)\n\}/);
  assert.ok(rnd, "rnd application adapter must accept an optional match id");
  assert.match(rnd[1], /matchId:matchId\|\|getGroupMatchId\(hTeam,aTeam\)/);
});

test("scorer generation applies separate goal and assist threat multipliers", () => {
  assert.match(html, /function weightedPick\(players,team,weights,fallback,type\)/);
  assert.match(html, /weightedPick\(hp,m\.h,GOAL_W,3,"goal"\)/);
  assert.match(html, /weightedPick\(pool,m\.h,ASSIST_W,3,"assist"\)/);
  assert.match(html, /weightedPick\(hp,ht,GOAL_W,3,"goal"\)/);
  assert.match(html, /weightedPick\(pool,ht,ASSIST_W,3,"assist"\)/);
});

test("group quick actions expose draw selection", () => {
  assert.match(html, /quickDraw:"平"/);
  assert.match(html, /quickDraw:"Draw"/);
  assert.ok(html.includes("qpG(\\''+gk+'\\','+mi+',\\'d\\')"));
});

test("match odds display uses complete 1X2 odds when available", () => {
  assert.match(html, /function getCompleteOdds\(matchId\)/);
  assert.match(html, /function formatOdds\(odds,matchId\)/);
  assert.match(html, /co&&co\.h/);
  assert.match(html, /formatOdds\(m\.odds,m\.id\)/);
  assert.match(html, /模型推导 1X2/);
  assert.match(html, /co&&co\.m==="derived_from_partial"/);
});

test("offline ranking snapshot covers all 48 tournament teams", () => {
  const groupsMatch = html.match(/var GD=(\{[^\n]+\});/);
  const rankingMatch = html.match(/var MODEL_RANKING=\{\};"([^"]+)"\.split/);
  assert.ok(groupsMatch);
  assert.ok(rankingMatch);
  const groups = Function(`return ${groupsMatch[1]}`)();
  const tournamentTeams = new Set(Object.values(groups).flat());
  const rankedTeams = new Set(rankingMatch[1].split(","));
  assert.equal(tournamentTeams.size, 48);
  assert.deepEqual(rankedTeams, tournamentTeams);
});
