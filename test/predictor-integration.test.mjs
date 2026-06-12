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
  const rnd = html.match(/function rnd\(draw,hTeam,aTeam\)\{([\s\S]*?)\n\}/);
  assert.ok(rnd, "rnd application adapter must exist");
  assert.match(rnd[1], /predictionMode:predictionMode/);
  assert.match(rnd[1], /gameplayMode:playMode/);
  assert.match(rnd[1], /rankings:MODEL_RANKING/);
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
