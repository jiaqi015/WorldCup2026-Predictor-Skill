import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const matchDetails = JSON.parse(
  readFileSync(new URL("../data/matches/match_details.json", import.meta.url), "utf8"),
);
const predictionData = JSON.parse(
  readFileSync(new URL("../data/prediction/prediction_data_v1.json", import.meta.url), "utf8"),
);

test("prediction model selector is wired to persistent application state", () => {
  assert.match(html, /id="predictionModeSelect"/);
  assert.match(html, /onchange="setPredictionMode\(this\.value\)"/);
  assert.match(html, /wc26_prediction_mode/);
  assert.match(html, /function setPredictionMode\(mode\)/);
});

test("prediction model selector follows the active theme", () => {
  assert.match(html, /\.predict-mode select\{[^}]*appearance:none/);
  assert.match(html, /\.predict-mode select\{[^}]*-webkit-appearance:none/);
  assert.match(html, /\.predict-mode select\{[^}]*color-scheme:light/);
  assert.match(html, /\.predict-mode select\{[^}]*background-image:linear-gradient/);
  assert.match(html, /body\.dark \.predict-mode select\{[^}]*color-scheme:dark/);
  assert.match(html, /body\.dark \.predict-mode option\{background:#0C1A12;color:#ECEFE8\}/);
});

test("gameplay modes constrain compatible prediction strategies", () => {
  assert.match(
    html,
    /if\(play==="chaos"\)return\["random"\]/,
  );
  assert.match(
    html,
    /if\(play==="normal"\)return\["strength","ensemble"\]/,
  );
  assert.match(
    html,
    /return\["random","strength","ensemble"\]/,
  );
  assert.match(html, /if\(mode==="odds"\|\|mode==="worldRanking"\)mode="strength"/);
  assert.match(html, /if\(mode==="aiReasoning"\)mode="ensemble"/);
  assert.match(html, /\{k:"strength",zh:"实力模型",en:"Strength model"\}/);
  assert.match(html, /\{k:"ensemble",zh:"综合模型",en:"Ensemble model"\}/);
  assert.doesNotMatch(html, /\{k:"worldRanking",zh:"综合排名"/);
  assert.doesNotMatch(html, /\{k:"aiReasoning",zh:"AI 综合"/);
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

test("group outcome buttons mount complete 1X2 odds when available", () => {
  assert.match(html, /function getCompleteOdds\(matchId\)/);
  assert.match(html, /function getOutcomeOdds\(odds,matchId\)/);
  assert.match(html, /function outcomeButtonHTML\(label,odd\)/);
  assert.match(html, /co&&co\.h/);
  assert.match(html, /outcomeButtonHTML\(T\("quickHome"\),outcomeOdds&&outcomeOdds\.h\)/);
  assert.match(html, /outcomeButtonHTML\(T\("quickDraw"\),outcomeOdds&&outcomeOdds\.d\)/);
  assert.match(html, /outcomeButtonHTML\(T\("quickAway"\),outcomeOdds&&outcomeOdds\.a\)/);
  assert.match(html, /class="outcome-odds"/);
  assert.doesNotMatch(html, /模型推导赔率/);
  assert.doesNotMatch(html, /Model-derived odds/);
  assert.match(html, /co&&co\.m==="derived_from_partial"/);
});

test("history panel title stays plain", () => {
  assert.match(html, /histTitle:"历史预测"/);
  assert.match(html, /<span class="history-title">\'\+T\("histTitle"\)\+\'<\/span>/);
  assert.doesNotMatch(html, /📅 \'\+T\("histTitle"\)/);
  assert.doesNotMatch(html, /📅 我的历史预测/);
});

test("completed match goal events are team-scoped and enter prediction data", () => {
  const goals = Object.values(matchDetails)
    .flatMap((detail) => detail.events || [])
    .filter((event) => event.type === "goal");
  assert.ok(goals.length > 0);
  assert.ok(goals.every((event) => event.scorer_mapping_status));
  assert.ok(goals.every((event) => event.scorer_source_name));
  assert.ok(Array.isArray(predictionData.actual_match_events));
  assert.equal(
    predictionData.actual_match_events.filter((event) => event.event_type === "goal").length,
    goals.length,
  );
  assert.match(html, /function renderActualGoalEvents\(matchId\)/);
  assert.match(html, /actualGoalsTitle/);
});

test("poster sharing emphasizes URL and keeps modal actions plain", () => {
  assert.match(html, /function championPosterTier\(team\)/);
  assert.match(html, /Math\.round\(raw\)/);
  assert.match(html, /var tier=championPosterTier\(champ\)/);
  assert.match(html, /<div class="footer-url-label">/);
  assert.match(html, /www\.cameraclaw\.cn\/2026/);
  assert.doesNotMatch(html, /<div class="footer-right">\+qrHTML/);
  assert.doesNotMatch(html, /btnDownloadPoster:"💾/);
  assert.doesNotMatch(html, /btnCopyLink:"🔗/);
  assert.match(html, /btnDownloadPoster:"保存海报"/);
  assert.match(html, /btnCopyLink:"复制分享链接"/);
});

test("group matches render chronologically without changing fixture identity", () => {
  assert.match(html, /function chronologicalGroupMatches\(gk\)/);
  assert.match(html, /return Date\.parse\(left\.m\.date\|\|""\)-Date\.parse\(right\.m\.date\|\|""\)/);
  assert.match(html, /var mi=ordered\[oi\]\.mi,m=ordered\[oi\]\.m/);
});

test("group progress uses the liquid glass progress component", () => {
  assert.match(html, /class="group-progress/);
  assert.match(html, /class="group-progress-liquid"/);
  assert.match(html, /role="progressbar"/);
  assert.match(html, /aria-valuenow="'\+doneM\+'"/);
  assert.doesNotMatch(html, /max-width:400px;margin:0 auto 16px;text-align:center/);
});

test("venue metadata follows the active language", () => {
  assert.match(html, /LANG==="zh"\?\(venue\.name_cn\|\|venue\.fullName\|\|venue\.name\)/);
  assert.match(html, /LANG==="zh"\?\(venue\.city_cn\|\|\(venue\.address&&venue\.address\.city\)\|\|venue\.city\)/);
  assert.match(html, /if\(actual\.venue&&!m\.venue\)m\.venue=actual\.venue/);
  assert.match(html, /"name_cn"/);
  assert.match(html, /"city_cn"/);
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
