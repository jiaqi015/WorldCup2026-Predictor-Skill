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
  assert.match(html, /function actualEventTeamBadge\(team\)/);
  assert.match(html, /class="actual-goal-team"/);
  assert.match(html, /actualEventTeamName\(event,"scorer"\)/);
  assert.match(html, /actualEventTeamName\(event,"assist"\)/);
});

test("embedded completed results default into blank group score inputs", () => {
  assert.match(html, /md&&md\.homeScore!=null&&md\.awayScore!=null/);
  assert.match(html, /m\.actualHs=String\(md\.homeScore\)/);
  assert.match(html, /m\.actualAs=String\(md\.awayScore\)/);
  assert.match(html, /var hasLive=!!\(ACTUAL_RESULTS\.ready&&ACTUAL_RESULTS\.groups\)/);
  assert.match(html, /loadState\(\);\napplyActualResultsToBlankPredictions\(\);/);
  assert.match(html, /function rsG\(gk\)[\s\S]*applyActualResultsToBlankPredictions\(\);render\(\);/);
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
  assert.match(html, /btnCopyLink:"复制分享链接（点击可查看你预测全部赛程）"/);
  assert.match(html, /btnShare:"分享我的专属预测海报&链接"/);
});

test("shared prediction links use a shorter schedule hash while preserving old links", () => {
  assert.match(html, /var SHORT_SHARE_STATE_VERSION=3/);
  assert.match(html, /function serializeShortState\(\)/);
  assert.match(html, /function deserializeShortState\(encoded\)/);
  assert.match(html, /hash&&hash\.indexOf\("#s="\)===0/);
  assert.match(html, /hash&&hash\.indexOf\("#p="\)===0/);
  assert.match(html, /return location\.origin\+location\.pathname\+"\#s="\+encoded/);
  assert.match(html, /return encoded\?location\.origin\+location\.pathname\+"\#p="\+encoded:null/);
  assert.match(html, /var url=getSharePredictionUrl\(\)/);
  assert.ok(
    html.indexOf("function T(key,vars)") < html.indexOf("loadState();"),
    "shared-view banner needs translations before loadState runs",
  );
  assert.match(html, /if\(isViewMode\)\{showViewBanner\(\);applyViewModeLockdown\(\);\}/);
});

test("share actions guide clicks and keep long copy text readable", () => {
  assert.match(html, /\.share-cta\{[^}]*animation:shareCtaPulse/);
  assert.match(html, /@media \(prefers-reduced-motion:reduce\)\{\.share-cta\{animation:none\}\}/);
  assert.match(html, /body\.dark \.share-cta/);
  assert.match(html, /class="btn-rand share-cta" onclick="genShareCard\(\)"/);
  assert.match(html, /\.share-copy-btn\{[^}]*white-space:normal/);
  assert.match(html, /id="copyShareLinkBtn" class="share-copy-btn" onclick="copyShareLink\(\)"/);
  assert.match(html, /btnCopyLink:"Copy share link \(view full schedule\)"/);
  assert.match(html, /btnShare:"Share my poster & link"/);
});

test("share poster modal uses the larger preview layout", () => {
  assert.match(html, /\.share-result-modal\{[^}]*width:min\(980px,calc\(100vw - 32px\)\)[^}]*max-height:92vh/);
  assert.match(html, /\.share-result-body\{[^}]*grid-template-columns:minmax\(340px,1fr\) 300px/);
  assert.match(html, /\.share-preview-frame img\{[^}]*width:min\(430px,100%\)/);
  assert.match(html, /class="modal share-result-modal"/);
  assert.match(html, /class="share-preview-panel"/);
  assert.match(html, /class="share-side-panel"/);
  assert.match(html, /posterModalDesc:"保存海报发给朋友，或复制链接让对方查看你的完整赛程预测。"/);
  assert.match(html, /posterModalUrlHint:"海报已突出网址"/);
  assert.doesNotMatch(html, /style="max-width:520px;text-align:center;padding:24px"/);
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
  assert.match(html, /width:min\(620px,calc\(100% - 32px\)\)/);
  assert.match(html, /rgba\(154,205,226,0\.34\)/);
  assert.match(html, /rgba\(92,158,190,0\.24\)/);
  assert.doesNotMatch(html, /max-width:400px;margin:0 auto 16px;text-align:center/);
});

test("group match panel title keeps completed-result guidance readable", () => {
  assert.match(html, /groupMatchesTitle:"\{g\}组 · 比赛 & 比分",groupMatchesHint:"（ 完赛结果已带入，可模拟后手动修改结果 ）"/);
  assert.match(html, /groupMatchesTitle:"Group \{g\} · Matches & Scores",groupMatchesHint:"\(completed results are filled; simulate or edit manually\)"/);
  assert.match(html, /<h3 class="group-match-title"><span>'\+T\("groupMatchesTitle",\{g:expG\}\)\+'<\/span><span class="group-match-title-note">'\+T\("groupMatchesHint"\)/);
  assert.match(html, /\.group-match-title-note\{[^}]*display:block/);
  assert.match(html, /\.group-match-title-note\{[^}]*font-size:12px/);
});

test("group simulation toolbar prioritizes remaining matches before full re-simulation", () => {
  assert.match(html, /btnRandAll:"⚡ 重新模拟全部",btnFillRemaining:"✨ 模拟补全剩余"/);
  assert.match(html, /btnRandAll:"⚡ Re-simulate All",btnFillRemaining:"✨ Simulate Remaining"/);
  assert.match(html, /var h='<div class="topbar">'\+fillBtn\+'<button class="btn-rand btn-rand-secondary" onclick="raG\(\)">'\+T\("btnRandAll"\)/);
  assert.match(html, /\.btn-rand-secondary\{background:linear-gradient\(180deg,#2A2D32,#1A1D21\)/);
});

test("play mode labels and selected entertainment color stay intentional", () => {
  assert.match(html, /\{k:"normal",zh:"标准模式",en:"Standard"\}/);
  assert.doesNotMatch(html, /\{k:"normal",zh:"普通模式"/);
  assert.match(html, /\.play-mode\.clone::before\{[^}]*rgba\(124,207,255,0\.82\)[^}]*rgba\(172,136,255,0\.68\)/);
});

test("entire group cards are selectable without hijacking nested controls", () => {
  assert.match(html, /\.card\{[^}]*cursor:pointer/);
  assert.match(html, /\.card:focus-visible\{outline:2px solid var\(--ink-dark\)/);
  assert.match(html, /role="button" tabindex="0" aria-pressed="/);
  assert.match(html, /onclick="toggleGroupCard\(event,/);
  assert.match(html, /onkeydown="keyGroupCard\(event,/);
  assert.match(html, /function targetIsCardControl\(target\)/);
  assert.match(html, /closest\("button,input,select,textarea,a,label"\)/);
  assert.match(html, /function keyGroupCard\(ev,gk\)/);
});

test("champion route stays on one horizontal line", () => {
  assert.match(html, /\.cp-route\{[^}]*max-width:min\(1040px,calc\(100vw - 96px\)\)/);
  assert.match(html, /\.cp-route \.cr-s\{[^}]*flex-wrap:nowrap/);
  assert.match(html, /\.cp-route \.cr-s\{[^}]*overflow-x:auto/);
  assert.match(html, /\.cp-route \.cr-step\{[^}]*white-space:nowrap/);
  assert.match(html, /\.cp-route \.cr-arrow\{[^}]*flex:0 0 auto/);
});

test("knockout toolbar can simulate the bracket one round at a time", () => {
  assert.match(html, /btnSimR32:"模拟32强",btnSimR16:"模拟16强",btnSimQF:"模拟8强",btnSimSF:"模拟半决赛"/);
  assert.match(html, /btnSimFinals:"模拟决赛及季军赛",btnKODone:"淘汰赛已完成"/);
  assert.match(html, /function getNextKOSimulationLabel\(\)/);
  assert.match(html, /keys=\["btnSimR32","btnSimR16","btnSimQF","btnSimSF","btnSimFinals"\]/);
  assert.match(html, /class="btn-next-round" onclick="raKONext\(\)"/);
  assert.match(html, /onclick="raKONext\(\)"/);
  assert.match(html, /function getKORounds\(\)/);
  assert.match(html, /function raKONext\(\)/);
  assert.match(html, /\{id:"3RD",ht:ko\["S1"\]\?ko\["S1"\]\.l:null/);
  assert.match(html, /\{id:"FINAL",ht:ko\["S1"\]\?ko\["S1"\]\.w:null/);
});

test("round-by-round simulation is visually prioritized", () => {
  assert.match(html, /\.btn-next-round\{background:var\(--accent-gold\)/);
  assert.match(html, /body\.dark \.btn-next-round\{background:var\(--accent-gold\)/);
});

test("knockout winners have a compact inline marker", () => {
  assert.match(html, /\.bk-row \.name\.w::after\{content:"✓"/);
  assert.match(html, /\.bk-row \.name\.w\{padding-right:13px/);
  assert.match(html, /\.bk-row\.is-cp \.name\.w::after\{color:var\(--accent-gold-dark\)\}/);
});

test("knockout round labels use a balanced scale with a larger final title", () => {
  assert.match(html, /\.bk-title\.stage-label\{font-size:1\.35rem/);
  assert.match(html, /\.bk-title\.stage-label\{font-size:1\.05rem\}/);
  assert.match(html, /\.bk-round\.final-col>\.bk-title\.final-title\{font-size:1\.7rem/);
  assert.match(html, /\.bk-round\.final-col \.bk-title\.third-title\{font-size:1\.45rem/);
  assert.match(html, /\.bk-round\.final-col>\.bk-title\.final-title\{font-size:1\.35rem\}/);
  assert.match(html, /\.bk-round\.final-col \.bk-title\.third-title\{font-size:1\.15rem\}/);
  assert.match(html, /<div class="bk-title stage-label">'\+title\+'<\/div>/);
  assert.match(html, /<div class="bk-title final-title">'\+cupIcon\(\)\+' '\+T\("finalLabel"\)/);
  assert.match(html, /<div class="bk-title third-title">'\+T\("third"\)/);
  assert.match(html, /r32:"R32",r16:"R16",qf:"QF",sf:"SF"/);
});

test("stats tab has a distinct selected state and non-recursive photo priming", () => {
  assert.match(html, /\.tabs button\.tab-scorers\.on\{background:linear-gradient/);
  assert.match(html, /class="tab-'\+ts\[i\]\+\(tab===ts\[i\]\?" on":""\)/);
  assert.match(html, /function primeLeaderboardPhotos\(items\)/);
  assert.match(html, /photoCache\[qk\]=PHOTO_MAP\[qk\]\|\|PHOTO_MAP\[item\.p\]\|\|null/);
  assert.match(html, /primeLeaderboardPhotos\(goals\.concat\(assists\)\);/);
  assert.match(html, /function resolvePhotoUrl\(path\)/);
  assert.match(html, /location\.hostname==="www\.cameraclaw\.cn"/);
  assert.match(html, /https:\/\/worldcup-origin\.cameraclaw\.cn\//);
  assert.match(html, /return resolvePhotoUrl\(path\)/);
  assert.doesNotMatch(html, /pending<=0&&tab==="scorers"\)render\(\)/);
});

test("stats leaderboard includes actual scorers and assists exactly once", () => {
  assert.match(html, /function addActual\(events\)/);
  assert.match(html, /e\.scorer_app_alias\|\|e\.scorer_cn/);
  assert.match(html, /e\.assist_app_alias\|\|e\.assist_cn/);
  assert.match(html, /match\.predictionSource==="actual"&&match\.actualEvents&&match\.actualEvents\.length/);
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
