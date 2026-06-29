import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const matchDetails = JSON.parse(
  readFileSync(new URL("../data/matches/match_details.json", import.meta.url), "utf8"),
);
const predictionData = JSON.parse(
  readFileSync(new URL("../data/prediction/prediction_data_v1.json", import.meta.url), "utf8"),
);

function extractVarExpression(name) {
  const match = html.match(new RegExp(`var ${name}=([\\s\\S]*?);\\nvar `));
  assert.ok(match, `${name} must be declared`);
  return Function(`return (${match[1]});`)();
}

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
  assert.match(html, /var sampledOutcome=sampleOutcome\(probabilities,rng\)/);
  assert.match(
    html,
    /sampleConditionalScoreline\(lambdas,sampledOutcome,rng\)/,
  );
});

test("shared match simulation passes match ids into complete odds lookup", () => {
  assert.match(html, /function getGroupMatchId\(hTeam,aTeam\)/);
  const rnd = html.match(/function rnd\(draw,hTeam,aTeam,matchId\)\{([\s\S]*?)\n\}/);
  assert.ok(rnd, "rnd application adapter must accept an optional match id");
  assert.match(rnd[1], /matchId:matchId\|\|getGroupMatchId\(hTeam,aTeam\)/);
});

test("scorer generation applies separate goal and assist threat multipliers", () => {
  assert.match(html, /function weightedPick\(players,team,weights,fallback,type\)/);
  assert.match(html, /threatMap\[team\+"\|"\+p\]/);
  assert.match(html, /var entry=tEntry\|\|threatMap\[p\]/);
  assert.match(html, /weightedPick\(pool,playerTeam,GOAL_W,3,"goal"\)/);
  assert.match(html, /weightedPick\(assistPool,playerTeam,ASSIST_W,3,"assist"\)/);
});

test("simulation stores event-aware goal logs and knockout decisions", () => {
  assert.match(html, /PredictionEngine\.buildMatchEvents\(\{homeGoals:hs,awayGoals:as/);
  assert.match(html, /event\.type==="own_goal"/);
  assert.match(html, /ownGoal:isOwn/);
  assert.match(html, /event\.type==="penalty_goal"/);
  assert.match(html, /if\(s\.ownGoal\)continue/);
  assert.match(html, /function pushAutoGoalFromEvent\(target,event,scoringTeam,opponentTeam,mid\)\{/);
  assert.match(html, /if\(!isTimelineScoringEvent\(event\)\)return/);
  assert.match(html, /if\(!isTimelineScoringEvent\(event\)\)continue/);
  assert.match(html, /PredictionEngine\.simulateKnockoutMatch\(/);
  assert.match(html, /ht:ht,at:at/);
  assert.match(html, /decidedBy:sim\.decidedBy/);
  assert.match(html, /shootout:sim\.shootout/);
  assert.match(html, /function koWinScoreText\(rec,champ\)/);
  assert.match(html, /function koDecisionText\(rec\)/);
  assert.match(html, /class="bk-decision"/);
  assert.match(html, /decidedBy==="shootout"/);
  assert.match(html, /period:event\.period/);
  assert.match(html, /var SHARE_STATE_VERSION=3/);
  assert.match(html, /data\.v===SHARE_STATE_VERSION\|\|data\.v===2/);
  assert.match(html, /meta=\{ht:tIdx\(ks\.ht\),at:tIdx\(ks\.at\),decidedBy:ks\.decidedBy\|\|"regulation"/);
  assert.match(html, /r\.decidedBy&&r\.decidedBy!=="regulation"/);
});

test("simulated group and knockout matches open a unified timeline detail modal", () => {
  assert.match(html, /detailButton:"比赛详情"/);
  assert.match(html, /detailButtonSimulation:"模拟详情"/);
  assert.match(html, /function detailButtonLabel\(isSimulation\)/);
  assert.match(html, /detailButtonLabel\(!\(m&&m\.predictionSource==="actual"\)\)/);
  assert.match(html, /var detailLabel=detailButtonLabel\(\!\!r\);/);
  assert.match(html, /detailSourceSimulation:"模拟生成"/);
  assert.match(html, /detailSourceActual:"真实赛况 · ESPN"/);
  assert.match(html, /function renderMatchDetailModal\(model\)/);
  assert.match(html, /class="modal match-detail-modal"/);
  assert.match(html, /class="match-detail-shell"/);
  assert.match(html, /function detailSummaryHTML\(model\)/);
  assert.match(html, /\.modal\.match-detail-modal\{[^}]*max-width:none/);
  assert.match(html, /\.modal\.match-detail-modal\{[^}]*width:min\(860px,calc\(100vw - 28px\)\)/);
  assert.match(html, /\.match-detail-shell\{[^}]*grid-template-columns:260px minmax\(0,1fr\)/);
  assert.match(html, /\.detail-timeline\{[^}]*max-height:min\(58vh,560px\)/);
  assert.match(html, /function timelineFromActual\(matchId,actual,home,away\)/);
  assert.match(html, /function timelineFromGoalLog\(log,scoringTeam,sourceLabel\)/);
  assert.match(html, /goalLogPairs\(log\|\|\[\]\)/);
  assert.match(html, /function openGroupMatchDetail\(gk,mi\)/);
  assert.match(html, /mergeTimelineEvents\(timelineFromGoalLog\(m\.hg,m\.h,source\),timelineFromGoalLog\(m\.ag,m\.a,source\),timelineFromRawEvents/);
  assert.match(html, /function openKOMatchDetail\(id,ht,at,hSeed,aSeed,seedRole\)/);
  assert.match(html, /actual=!r\?getActualKOMatchResult\(id,ht,at\):null/);
  assert.match(html, /timelineFromActual\(actual\.id,actual,home,away\)/);
  assert.match(html, /homeScore:rec\?String\(rec\.h\):"-"/);
  assert.match(html, /var detailClick='openKOMatchDetail/);
  assert.ok(html.includes('<button class="bk-detail" onclick="\'+detailClick+\'">'));
  assert.match(html, /renderShootoutDetail\(model\)/);
  assert.match(html, /shootout\.kicks\.length/);
  assert.match(html, /detailPenalty:"点球"/);
  assert.match(html, /detailExtraTime:"加时"/);
  assert.match(html, /detailShootout:"点球大战"/);
});

test("match detail timelines render non-scoring events from the unified event stream", () => {
  assert.match(html, /detailYellowCard:"黄牌"/);
  assert.match(html, /detailRedCard:"红牌"/);
  assert.match(html, /detailSubstitution:"换人"/);
  assert.match(html, /detailPlayerTbd:"球员待确认"/);
  assert.match(html, /detailBenchTbd:"替补待确认"/);
  assert.match(html, /function safePlayerName\(player\)/);
  assert.doesNotMatch(html, /return LANG==="en"\?"Unknown":"未记录"/);
  assert.match(html, /function detailPlayerName\(player,team,fallback\)/);
  assert.match(html, /detailPlayerName\(e\.player,team,T\("detailPlayerTbd"\)\)/);
  assert.match(html, /detailPlayerName\(e\.outPlayer,team,T\("detailPlayerTbd"\)\)/);
  assert.match(html, /detailPlayerName\(e\.inPlayer,team,T\("detailBenchTbd"\)\)/);
  assert.match(html, /function detailEventPeriodText\(event\)/);
  assert.match(html, /sub=detailEventPeriodText\(e\);/);
  assert.doesNotMatch(html, /badges\.push\(\{text:T\("detailYellowCard"\)/);
  assert.doesNotMatch(html, /badges\.push\(\{text:T\("detailSubstitution"\)/);
  assert.match(html, /function isTimelineScoringEvent\(event\)/);
  const rawTimeline = html.match(/function timelineFromRawEvents\(events,home,away,sourceLabel\)\{([\s\S]*?)\n\}/);
  assert.ok(rawTimeline, "raw event timeline adapter must exist");
  assert.doesNotMatch(rawTimeline[1], /if\(!isScoringEvent\(e\)\)continue/);
  assert.match(rawTimeline[1], /isTimelineCardEvent\(e\)/);
  assert.match(rawTimeline[1], /isTimelineSubstitutionEvent\(e\)/);
  assert.match(html, /mergeTimelineEvents\(timelineFromGoalLog/);
});

test("stats and share poster expose tournament awards derived from match events", () => {
  assert.match(html, /function collectAwardMatches\(\)/);
  assert.match(html, /function computeTournamentAwards\(\)/);
  assert.match(html, /PredictionEngine\.deriveTournamentAwards/);
  assert.match(html, /function renderAwardsPanel\(awards\)/);
  assert.match(html, /awardPanelTitle:"奖项"/);
  assert.doesNotMatch(html, /awardPanelTitle:"模拟奖项"/);
  assert.match(html, /awardGoldenBoot:"金靴"/);
  assert.match(html, /awardGoldenGlove:"金手套"/);
  assert.match(html, /awardGoldenBall:"金球"/);
  assert.match(html, /awardFairPlay:"公平竞赛"/);
  assert.match(html, /function awardIconHTML\(kind\)/);
  assert.match(html, /function awardAvatarHTML\(name,team\)/);
  assert.match(html, /function awardCountryHTML\(team\)/);
  assert.match(html, /class="award-panel"/);
  assert.match(html, /class="award-logo /);
  assert.match(html, /award-panel-grid\{display:grid;grid-template-columns:minmax\(184px,1\.18fr\)/);
  assert.match(html, /var cardClass='award-card award-'\+\(kind\|\|"goldenBall"\)/);
  assert.match(html, /\.award-card\.award-goldenBoot/);
  assert.match(html, /\.award-card\.award-goldenBall/);
  assert.match(html, /\.award-card\.award-goldenGlove/);
  assert.match(html, /\.award-logo::before/);
  assert.match(html, /class="award-fill"/);
  assert.match(html, /class="award-avatar"/);
  assert.match(html, /class="award-country"/);
  assert.match(html, /class="poster-awards"/);
  assert.match(html, /buildPosterAwardsHTML\(computeTournamentAwards\(\)\)/);
});

test("group quick actions expose draw selection", () => {
  assert.match(html, /quickDraw:"平"/);
  assert.match(html, /quickDraw:"Draw"/);
  assert.ok(html.includes("qpG(\\''+gk+'\\','+mi+',\\'d\\')"));
});

test("group outcome buttons mount complete 1X2 odds when available", () => {
  assert.match(html, /function getCompleteOdds\(matchId\)/);
  assert.match(html, /function getOutcomeOdds\(odds,matchId,flip\)/);
  assert.match(html, /orientCompleteOddsToFixture\(getCompleteOdds\(matchId\),flip\)/);
  assert.match(html, /function outcomeButtonHTML\(label,odd\)/);
  assert.match(html, /co&&co\.h/);
  assert.match(html, /getOutcomeOdds\(m\.odds,m\.id,m\.scheduleFlip\)/);
  assert.match(html, /outcomeButtonHTML\(T\("quickHome"\),outcomeOdds&&outcomeOdds\.h\)/);
  assert.match(html, /outcomeButtonHTML\(T\("quickDraw"\),outcomeOdds&&outcomeOdds\.d\)/);
  assert.match(html, /outcomeButtonHTML\(T\("quickAway"\),outcomeOdds&&outcomeOdds\.a\)/);
  assert.match(html, /class="outcome-odds"/);
  assert.doesNotMatch(html, /模型推导赔率/);
  assert.doesNotMatch(html, /Model-derived odds/);
  assert.match(html, /co&&co\.m==="derived_from_partial"/);
});

test("group quick actions preserve scroll and focus after re-render", () => {
  assert.match(html, /function rememberFocus\(key\)/);
  assert.match(html, /window\.__lastFocusKey=key/);
  assert.match(html, /function getSplitRightScrollTop\(\)/);
  assert.match(html, /function restoreSplitRightScrollTop\(scrollTop\)/);
  assert.match(html, /window\.__lastPanelScrollTop=getSplitRightScrollTop\(\)/);
  assert.match(html, /function restoreRenderFocus\(focusKey,scrollX,scrollY,panelScrollTop\)/);
  assert.match(html, /var scrollX=window\.__lastScrollX!=null\?window\.__lastScrollX/);
  assert.match(html, /window\.__lastScrollY=window\.pageYOffset/);
  assert.match(html, /var panelScrollTop=window\.__lastPanelScrollTop!=null\?window\.__lastPanelScrollTop:getSplitRightScrollTop\(\)/);
  assert.match(html, /\|\|window\.__lastFocusKey\|\|null/);
  assert.ok(html.includes('var preferred=document.querySelector(\'.split-right [data-focus-key="\'+focusKey+\'"]\')'));
  assert.ok(html.includes('if(preferred&&visible(preferred))nextFocus=preferred'));
  assert.match(html, /nextFocus\.focus\(\{preventScroll:true\}\)/);
  assert.match(html, /restoreSplitRightScrollTop\(panelScrollTop\)/);
  assert.match(html, /window\.scrollTo\(scrollX\|\|0,scrollY\|\|0\)/);
  assert.match(html, /function scheduleRenderRestore\(focusKey,scrollX,scrollY,panelScrollTop\)/);
  assert.match(html, /window\.requestAnimationFrame\(function\(\)\{restoreRenderFocus\(focusKey,scrollX,scrollY,panelScrollTop\);\}\)/);
  assert.match(html, /window\.setTimeout\(function\(\)\{restoreRenderFocus\(focusKey,scrollX,scrollY,panelScrollTop\);\},80\)/);
  assert.match(html, /window\.__lastFocusKey=null;window\.__lastScrollX=null;window\.__lastScrollY=null;window\.__lastPanelScrollTop=null/);
  assert.match(html, /data-focus-key="group-'\+gk\+'-'\+mi\+'-d"/);
  assert.ok(html.includes("rememberFocus(\\'group-'+gk+'-'+mi+'-d\\');qpG"));
});

test("group match team names show FIFA ranking badges", () => {
  assert.match(html, /function rankBadge\(team\)/);
  assert.match(html, /var r=FIFA_RANKINGS&&FIFA_RANKINGS\[team\]/);
  assert.match(html, /fifaRankTitle:"FIFA 世界排名 #\{rank\}"/);
  assert.match(html, /fifaRankTitle:"FIFA rank #\{rank\}"/);
  assert.match(html, /function teamNameHTML\(team\)/);
  assert.match(html, /function teamNameHTML\(team\)\{return teamProfileInline\(team,"match-team-chip"\)/);
  assert.match(html, /class="team-rank"/);
  assert.match(html, /teamNameHTML\(m\.h\)/);
  assert.match(html, /teamNameHTML\(m\.a\)/);
  assert.match(html, /\.team-rank\{[^}]*white-space:nowrap/);
});

test("team profile opens from team surfaces and keeps facts source-aware", () => {
  assert.match(html, /var TEAM_TACTICAL_PROFILES=\{/);
  assert.match(html, /var TEAM_FIRST_LINEUPS=\{/);
  assert.match(html, /var PLAYER_JERSEYS=\{/);
  assert.match(html, /function teamProfileInline\(team,extraClass\)/);
  assert.match(html, /function openTeamProfile\(team,ev\)/);
  assert.match(html, /ev\.preventDefault\(\);ev\.stopPropagation\(\)/);
  assert.match(html, /window\.scrollTo\(sx,sy\)/);
  assert.match(html, /window\.setTimeout\(function\(\)\{window\.scrollTo\(sx,sy\);\},80\)/);
  assert.match(html, /function buildTeamProfile\(team\)/);
  assert.match(html, /function teamProfileRecord\(team\)/);
  assert.match(html, /function teamProfileSquadSections\(team\)/);
  assert.match(html, /function teamProfileMatchRows\(team\)/);
  assert.match(html, /function teamProfileLineup\(team,tactic\)/);
  assert.match(html, /function teamProfilePitchHTML\(profile,formation,coach\)/);
  assert.match(html, /function teamProfileJersey\(player,team\)/);
  assert.match(html, /function teamProfileLineupSourceLabel\(source\)/);
  assert.match(html, /function renderTeamProfileModal\(profile\)/);
  assert.match(html, /teamProfileCoachUnknown:"待补充"/);
  assert.match(html, /teamProfileFormationUnknown:"待补充"/);
  assert.match(html, /teamProfileDataNote:"首发来自该队小组赛第一场 ESPN 阵容/);
  assert.match(html, /class="modal team-profile-modal"/);
  assert.match(html, /class="team-profile-hero"/);
  assert.match(html, /class="team-profile-pitch"/);
  assert.match(html, /class="team-profile-pitch-field"/);
  assert.match(html, /class="pitch-player-card"/);
  assert.match(html, /class="team-profile-section roster"/);
  assert.match(html, /class="team-profile-shirt"/);
  assert.match(html, /teamProfileInline\(t\.t/);
  assert.match(html, /teamNameHTML\(m\.h\)/);
  assert.match(html, /teamNameHTML\(m\.a\)/);
  assert.match(html, /teamProfileInline\(team,"bk-team-chip"\)/);
});

test("team profile design uses a scouting-board layout instead of generic cards", () => {
  assert.match(html, /\.team-profile-modal\{[^}]*width:min\(1120px,calc\(100vw - 24px\)\)/);
  assert.match(html, /\.team-profile-body\{[^}]*grid-template-columns:minmax\(360px,0\.96fr\) minmax\(0,1\.18fr\)/);
  assert.match(html, /\.team-profile-pitch\{[^}]*linear-gradient\(180deg,rgba\(15,113,70,0\.94\),rgba\(6,69,45,0\.98\)\)/);
  assert.match(html, /\.team-profile-pitch-field\{[^}]*height:486px/);
  assert.match(html, /\.team-profile-pitch-field::after/);
  assert.match(html, /\.pitch-player-card\{[^}]*position:absolute[^}]*width:70px[^}]*height:54px/);
  assert.match(html, /style="--x:'\+coords\.x\+'\%;--y:'\+coords\.y\+'\%"/);
  assert.match(html, /\.team-profile-matches\{[^}]*max-height:320px/);
  assert.match(html, /\.team-chip-inline\{[^}]*background:transparent/);
  assert.match(html, /@media\(max-width:760px\)\{\.team-profile-body\{grid-template-columns:1fr\}/);
  assert.doesNotMatch(html, /\.team-profile-[^{]+\{[^}]*border-left:\s*[2-9]/);
  assert.doesNotMatch(html, /background-clip:text/);
});

test("team profile pitch coordinates keep first XI cards from overlapping", () => {
  const lineupMatch = html.match(/var TEAM_FIRST_LINEUPS=(.*?);\n/);
  assert.ok(lineupMatch, "TEAM_FIRST_LINEUPS should be embedded");
  const lineups = JSON.parse(lineupMatch[1]);
  const start = html.indexOf("function teamProfilePitchLine(player)");
  const end = html.indexOf("function teamProfileLineupSourceLabel(source)");
  assert.ok(start > 0 && end > start, "pitch coordinate functions should be present");
  const context = {};
  vm.createContext(context);
  vm.runInContext(html.slice(start, end), context);

  const layouts = [
    { name: "desktop", fieldWidth: 408, fieldHeight: 486, cardWidth: 70, cardHeight: 54 },
    { name: "mobile", fieldWidth: 230, fieldHeight: 430, cardWidth: 54, cardHeight: 50 },
  ];
  for (const [team, lineup] of Object.entries(lineups)) {
    const starters = lineup.starters || [];
    assert.equal(starters.length, 11, `${team} should have an 11-player first lineup`);
    for (const layout of layouts) {
      const rects = starters.map((player, index) => {
        const coords = context.teamProfilePitchCoords(player, index, starters);
        const x = (coords.x / 100) * layout.fieldWidth;
        const y = (coords.y / 100) * layout.fieldHeight;
        return {
          player: player.name,
          left: x - layout.cardWidth / 2,
          right: x + layout.cardWidth / 2,
          top: y - layout.cardHeight / 2,
          bottom: y + layout.cardHeight / 2,
        };
      });
      for (let i = 0; i < rects.length; i += 1) {
        for (let j = i + 1; j < rects.length; j += 1) {
          const a = rects[i];
          const b = rects[j];
          const overlap = a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
          assert.equal(overlap, false, `${team} ${layout.name}: ${a.player} overlaps ${b.player}`);
        }
      }
    }
  }
});

test("manual scorer picker uses full squad candidates grouped by position", () => {
  assert.match(html, /function getSquadPlayers\(team\)/);
  assert.match(html, /if\(POS\[team\]\)for\(var p in POS\[team\]\)add\(p\)/);
  assert.match(html, /uniquePlayers\(getSquadPlayers\(team\)\)/);
  assert.match(html, /function playerBucket\(player,team\)/);
  assert.match(html, /function playerSectionsHTML\(players,team,onclickBuilder\)/);
  assert.match(html, /groups=\{fwd:\[\],mid:\[\],def:\[\],gk:\[\]\}/);
  assert.match(html, /playerBucket\(players\[i\],team\)/);
  assert.match(html, /class="player-bucket-chip"/);
  assert.match(html, /function playerChoiceHTML\(player,team,onclick,extraClass\)/);
  assert.match(html, /pos=getPos\(player,team\)/);
  assert.match(html, /class="player-pos">'\+pos_t\(pos\)\+'/);
  assert.match(html, /for\(var __i=0;__i<26;__i\+\+\)/);
});

test("manual scorer modal presents a goal-by-goal scorer then assist flow", () => {
  assert.match(html, /scorerModalTitle:"\{team\} · 手动记录进球"/);
  assert.match(html, /scorerStep:"第 \{current\} \/ \{total\} 球"/);
  assert.match(html, /selectScorer:"先选进球球员"/);
  assert.match(html, /selectAssisterFor:"第 \{current\} \/ \{total\} 球 · 进球：\{player\}"/);
  assert.match(html, /scorerPickerHint:"按位置分组/);
  assert.match(html, /assisterPickerHint:"有助攻就选队友/);
  assert.match(html, /class="assist-skip"/);
  assert.match(html, /function getScorerLog\(phase,gk,mi,side,team\)/);
  assert.match(html, /function getGoalLimit\(team,phase,gk,mi,side\)/);
  assert.match(html, /slog\.push\(\{p:player,t:team,g:1,a:0,mid:gk\}\)/);
});

test("position display preserves coarse source categories", () => {
  assert.match(html, /"加拿大":\{[^}]*"拉林":"前锋"[^}]*"戴维":"前锋"/);
  assert.match(html, /"英格兰":\{[^}]*"凯恩":"前锋"/);
  assert.match(html, /"苏格兰":\{[^}]*"罗伯逊":"后卫"[^}]*"麦金":"中场"/);
  assert.match(html, /var POS_EN=\{[^}]*"前锋":"F"[^}]*"中场":"M"[^}]*"后卫":"D"/);
  assert.match(html, /var GOAL_W=\{[^}]*前锋:7[^}]*中场:4[^}]*后卫:1/);
  assert.match(html, /var ASSIST_W=\{[^}]*前锋:4[^}]*中场:5[^}]*后卫:2/);
  assert.match(html, /function getPos\(player,team\)\{[\s\S]*return"中场";[\s\S]*\}/);
  assert.doesNotMatch(html, /if\(idx<=3\)return"边锋"/);
});

test("history panel title stays plain", () => {
  assert.match(html, /histTitle:"历史预测"/);
  assert.match(html, /<span class="history-title">\'\+T\("histTitle"\)\+\'<\/span>/);
  assert.doesNotMatch(html, /📅 \'\+T\("histTitle"\)/);
  assert.doesNotMatch(html, /📅 我的历史预测/);
});

test("manual scorer action label stays plain in Chinese", () => {
  assert.match(html, /pickManually:"手动选择进球"/);
  assert.doesNotMatch(html, /pickManually:"🎯 改为手动选择进球"/);
});

test("result scoring surface is hidden from the main tab bar", () => {
  assert.match(html, /tabBaseline:"评分"/);
  assert.match(html, /tabBaseline:"Score"/);
  assert.match(html, /var ts=\["groups","knockout","scorers"\]/);
  assert.match(html, /if\(ts\.indexOf\(tab\)<0\)tab="groups"/);
  assert.doesNotMatch(html, /var ts=\["groups","knockout","baseline","scorers"\]/);
  assert.match(html, /function rBaseline\(el\)/);
  assert.match(html, /function scorePrediction\(\)/);
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
  assert.match(html, /function renderActualGoalEvents\(matchId,actual\)/);
  assert.match(html, /function getActualGoalExpectedCount\(matchId,goals,actual\)/);
  assert.match(html, /actualGoalsTitle/);
  assert.match(html, /actualGoalsPartial/);
  assert.match(html, /actualGoalsLoading/);
  assert.match(html, /T\("actualMapped",\{mapped:mapped,total:expected\|\|goals\.length\}\)/);
  assert.match(html, /detailFetchPending\[matchId\]\?T\("actualGoalsLoading"\):T\("actualGoalsPartial"/);
  assert.match(html, /function actualEventTeamBadge\(team\)/);
  assert.match(html, /class="actual-goal-team"/);
  assert.match(html, /actualEventTeamName\(event,"scorer"\)/);
  assert.match(html, /actualEventTeamName\(event,"assist"\)/);
});

test("fresh live scores hydrate missing ESPN summary goal events at runtime", () => {
  assert.match(html, /var DETAIL_API="https:\/\/site\.api\.espn\.com\/apis\/site\/v2\/sports\/soccer\/fifa\.world\/summary\?event="/);
  assert.match(html, /function matchDetailNeedsHydration\(matchId,actual\)/);
  assert.match(html, /function parseEspnSummaryDetails\(summary,matchId,actual\)/);
  assert.match(html, /function fetchActualMatchDetails\(matchId,actual\)/);
  assert.match(html, /function hydrateMissingActualDetails\(\)/);
  assert.match(html, /function loadCachedMatchDetails\(\)/);
  assert.match(html, /localStorage\.getItem\("wc26_match_details"\)/);
  assert.match(html, /MATCH_DETAILS\[matchId\]=detail/);
  assert.match(html, /fetch\(DETAIL_API\+encodeURIComponent\(matchId\)\)/);
  assert.match(html, /m\.actualEvents=events/);
  assert.match(html, /hydrateMissingActualDetails\(\);/);
  assert.match(html, /renderActualGoalEvents\(m\.id\|\|actual\.id,actual\)/);
});

test("completed match details expose partial ESPN goal-event coverage", () => {
  const partials = Object.values(matchDetails).filter(
    (detail) => detail.expectedGoalCount > detail.goalEventCount,
  );
  assert.ok(partials.length > 0);
  assert.ok(
    partials.every((detail) => detail.goalEventsStatus === "partial"),
  );
  for (const detail of partials) {
    assert.ok(detail.matchId);
    assert.equal(detail.goalEventsStatus, "partial");
    assert.ok(detail.goalEventCount < detail.expectedGoalCount);
  }
});

test("Argentina vs Algeria completed match embeds ESPN goal scorers", () => {
  const argentinaAlgeria = matchDetails["760433"];
  assert.ok(argentinaAlgeria, "760433 should be present once ESPN marks it completed");
  assert.equal(argentinaAlgeria.homeTeamCn, "阿根廷");
  assert.equal(argentinaAlgeria.awayTeamCn, "阿尔及利亚");
  assert.equal(argentinaAlgeria.homeScore, 3);
  assert.equal(argentinaAlgeria.awayScore, 0);
  assert.equal(argentinaAlgeria.expectedGoalCount, 3);
  assert.equal(argentinaAlgeria.goalEventCount, 3);
  assert.equal(argentinaAlgeria.goalEventsStatus, "complete");

  const goals = argentinaAlgeria.events.filter((event) => event.type === "goal");
  assert.equal(goals.length, 3);
  assert.deepEqual(
    goals.map((event) => event.scorer_source_name),
    ["Lionel Messi", "Lionel Messi", "Lionel Messi"],
  );
  assert.deepEqual(
    goals.map((event) => event.minute),
    ["17'", "60'", "76'"],
  );
  assert.equal(goals[0].assist_source_name, "Rodrigo De Paul");
  assert.equal(goals[2].assist_source_name, "Nico González");
});

test("embedded completed results default into blank group score inputs", () => {
  assert.match(html, /md&&md\.homeScore!=null&&md\.awayScore!=null/);
  assert.match(html, /m\.actualHs=String\(reverseDirection\?md\.awayScore:md\.homeScore\)/);
  assert.match(html, /m\.actualAs=String\(reverseDirection\?md\.homeScore:md\.awayScore\)/);
  assert.match(html, /if\(actual\.flip!=null\)m\.scheduleFlip=!!actual\.flip/);
  assert.match(html, /var hasLive=!!\(ACTUAL_RESULTS\.ready&&ACTUAL_RESULTS\.groups\)/);
  assert.match(html, /loadState\(\);\napplyActualResultsToBlankPredictions\(\);/);
  assert.match(html, /function rsG\(gk\)[\s\S]*applyActualResultsToBlankPredictions\(\);render\(\);/);
});

test("poster sharing emphasizes URL and keeps modal actions plain", () => {
  assert.match(html, /function championPosterTier\(team\)/);
  assert.match(html, /Math\.round\(raw\)/);
  assert.match(html, /var tier=championPosterTier\(champ\)/);
  assert.match(html, /var TEAM_POSTER_LINES=\{/);
  assert.match(html, /function posterPathDifficulty\(champ,path\)/);
  assert.match(html, /function selectPosterTagline\(champ,path,en,tier\)/);
  assert.match(html, /var tagline=selectPosterTagline\(champ,path,en,tier\)/);
  assert.doesNotMatch(html, /var tagline=en\?\(EN_TAGLINE\[tier\]\|\|""\):\(TAGLINE\[tier\]\|\|""\)/);
  assert.match(html, /<div class="footer-url-label">/);
  assert.match(html, /www\.cameraclaw\.cn\/2026/);
  assert.doesNotMatch(html, /<div class="footer-right">\+qrHTML/);
  assert.doesNotMatch(html, /btnDownloadPoster:"💾/);
  assert.doesNotMatch(html, /btnCopyLink:"🔗/);
  assert.match(html, /btnDownloadPoster:"保存海报"/);
  assert.match(html, /btnCopyLink:"复制链接（本次模拟完整方案）"/);
  assert.match(html, /btnCopyShort:"复制"/);
  assert.match(html, /btnShare:"分享我的专属预测 海报&链接"/);
  assert.match(html, /btnShareLocked:"完成淘汰赛后分享"/);
  assert.match(html, /posterModalActionHint:"复制链接给朋友，邀请她也来预测"/);
  assert.match(html, /posterModalTitle:"分享预测结果"/);
  assert.doesNotMatch(html, /<div class="share-result-kicker">/);
  assert.doesNotMatch(html, /posterModalTitle:"长按保存海报"/);
});

test("poster conclusions include three Chinese variants for every team", () => {
  const teamLinesMatch = html.match(/var TEAM_POSTER_LINES=(\{[\s\S]*?\});\nfunction posterPathDifficulty/);
  assert.ok(teamLinesMatch, "TEAM_POSTER_LINES table should be present");
  const table = Function(`"use strict"; return (${teamLinesMatch[1]});`)();
  const teamMatch = html.match(/var STRENGTH=(\{[^;]+\});/);
  assert.ok(teamMatch, "STRENGTH table should be present");
  const teams = Object.keys(Function(`"use strict"; return (${teamMatch[1]});`)());
  assert.equal(teams.length, 48);
  for (const team of teams) {
    assert.ok(Array.isArray(table[team]), `${team} should have poster lines`);
    assert.equal(table[team].length, 3, `${team} should have three poster lines`);
    for (const line of table[team]) {
      assert.match(line, /^“.+”$/, `${team} line should keep poster quote style`);
      assert.ok(line.length <= 34, `${team} line is too long: ${line}`);
    }
  }
});

test("poster route includes a compact group-stage explanation before knockouts", () => {
  assert.match(html, /function getPosterGroupSummary\(champ\)/);
  assert.match(html, /group-stage/);
  assert.match(html, /champRouteTitle/);
  assert.match(html, /h\+='<div class="poster-path-row group-stage">';/);
  assert.match(html, /groupSummary\.text/);
  assert.match(html, /groupSummary\.stat/);
  assert.match(html, /stat:s\.p\+" "\+T\("pts"\)\+" · "\+s\.w\+"-"\+s\.d\+"-"\+s\.l/);
  assert.doesNotMatch(html, /stat:s\.p\+" pts · "/);
});

test("shared prediction links use a shorter schedule hash while preserving old links", () => {
  assert.match(html, /var SHORT_SHARE_STATE_VERSION=3/);
  assert.match(html, /var RAW_SHORT_SHARE_STATE_VERSION="4"/);
  assert.match(html, /var PACKED_SHORT_SHARE_STATE_VERSION="5"/);
  assert.match(html, /var SHORT_SHARE_PACK_ALPHABET=/);
  assert.match(html, /function serializeShortState\(\)/);
  assert.match(html, /return PACKED_SHORT_SHARE_STATE_VERSION\+bitsToShareText\(bits\)/);
  assert.match(html, /function deserializePackedShortState\(encoded\)/);
  assert.match(html, /function deserializeRawShortState\(encoded\)/);
  assert.match(html, /function deserializeShortParts\(gPart,kPart\)/);
  assert.match(html, /if\(deserializePackedShortState\(encoded\)\)return true/);
  assert.match(html, /if\(deserializeRawShortState\(encoded\)\)return true/);
  assert.match(html, /rebuildAllScorers\(\);/);
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
  assert.doesNotMatch(html, /class="vb-icon"|👁/);
});

test("share actions guide clicks and keep long copy text readable", () => {
  assert.match(html, /id="globalActions"/);
  assert.match(html, /function shareBrandIcon\(\)/);
  assert.match(html, /class="share-brand-icon"/);
  assert.match(html, /resolvePhotoUrl\("assets\/fifa-trophy-share\.png"\)/);
  assert.match(html, /\.share-brand-icon img\{[^}]*height:38px/);
  assert.match(html, /function renderGlobalShareBar\(ready\)/);
  assert.match(html, /var cls="share-cta"\+\(ready\?"":" dim"\)/);
  assert.doesNotMatch(html, /var cls="btn-rand share-cta"/);
  assert.match(html, /var action=ready\?' onclick="genShareCard\(\)"':' disabled aria-disabled="true"/);
  assert.match(html, /if\(ge\)ge\.innerHTML=renderControlDeck\(tab,groupDone,knockoutDone\);/);
  assert.match(html, /'<div class="control-share">'\+renderGlobalShareBar\(knockoutDone\)\+'/);
  assert.doesNotMatch(html, /var shareBtn=koDone/);
  assert.match(html, /\.share-cta\{[^}]*animation:shareCtaPulse/);
  assert.match(html, /\.share-cta\{[^}]*white-space:normal/);
  assert.doesNotMatch(html, /@keyframes shareCtaPulse\{[^}]*transform:/);
  assert.match(html, /@media \(prefers-reduced-motion:reduce\)\{\.share-cta\{animation:none\}\}/);
  assert.match(html, /body\.dark \.share-cta/);
  assert.match(html, /\.global-sharebar button\{[^}]*display:inline-flex/);
  assert.match(html, /\.share-cta\.dim\{[^}]*animation:none/);
  assert.match(html, /\.share-copy-btn\{[^}]*white-space:normal/);
  assert.match(html, /\.share-url-row\{[^}]*grid-template-columns:minmax\(0,1fr\) 44px/);
  assert.match(html, /\.share-url-copy\{[^}]*min-height:54px/);
  assert.match(html, /class="share-url-row"/);
  assert.match(html, /class="share-url-copy" onclick="copyShareLink\(\)"/);
  assert.match(html, /id="copyShareLinkBtn" class="share-copy-btn" onclick="copyShareLink\(\)"/);
  assert.match(html, /btnCopyLink:"Copy link \(full simulation plan\)"/);
  assert.match(html, /btnCopyShort:"Copy"/);
  assert.match(html, /posterModalTitle:"Share prediction results"/);
  assert.match(html, /btnShare:"Share my poster & link"/);
});

test("share poster modal uses a designed landscape preview and side actions", () => {
  assert.match(html, /\.share-result-modal\{[^}]*width:min\(1320px,calc\(100vw - 24px\)\)[^}]*max-height:94vh/);
  assert.match(html, /\.share-result-modal\{[^}]*background:linear-gradient\(180deg,#08110D 0%,#050806 100%\)/);
  assert.match(html, /\.share-result-head\{[^}]*align-items:center[^}]*padding:12px 20px 10px/);
  assert.match(html, /\.share-result-body\{[^}]*display:grid;grid-template-columns:minmax\(0,1.64fr\) 372px;min-height:clamp\(560px,72vh,660px\)/);
  assert.match(html, /\.share-side-panel\{[^}]*flex-direction:column/);
  assert.match(html, /\.share-preview-frame\{[^}]*width:min\(900px,100%\)/);
  assert.match(html, /\.share-url-chip\{[^}]*overflow:hidden;text-overflow:ellipsis/);
  assert.match(html, /\.share-url-copy\{[^}]*border:1px solid rgba\(229,194,106,0\.26\)/);
  assert.match(html, /\.poster\{width:900px;height:640px/);
  assert.match(html, /width:900,\s*height:640/);
  assert.match(html, /\.poster \.poster-hero\{[^}]*justify-content:flex-start/);
  assert.match(html, /\.poster \.poster-conclusion\{[^}]*margin-top:22px/);
  assert.match(html, /class="modal share-result-modal"/);
  assert.match(html, /class="share-preview-panel"/);
  assert.match(html, /class="share-side-panel"/);
  assert.match(html, /T\("posterModalActionHint"\)/);
  assert.doesNotMatch(html, /posterModalUrlHint/);
  assert.doesNotMatch(html, /海报已突出网址/);
  assert.doesNotMatch(html, /style="max-width:520px;text-align:center;padding:24px"/);
});

test("knockout tab gently guides users after group stage completion", () => {
  assert.match(html, /\.tabs button\.tab-guide\{[^}]*animation:tabGuidePulse/);
  assert.match(html, /@media \(prefers-reduced-motion:reduce\)\{\.tabs button\.tab-guide,\.tabs button\.tab-guide svg\{animation:none\}\}/);
  assert.match(html, /var groupDone=allDone\(\),knockoutDone=!!\(ko&&ko\.FINAL&&ko\.FINAL\.w\)/);
  assert.match(html, /var guideKO=tab==="groups"&&groupDone&&!knockoutDone/);
  assert.match(html, /ts\[i\]==="knockout"&&guideKO\?" tab-guide":""/);
  assert.match(html, /class="tab-guide-badge">→<\/span>/);
});

test("completed group and knockout tabs get subtle completion markers", () => {
  assert.match(html, /tabComplete:"已完成"/);
  assert.match(html, /tabComplete:"Completed"/);
  assert.match(html, /\.tab-done-badge\{display:inline-flex[^}]*radial-gradient/);
  assert.match(html, /var done=\(ts\[i\]==="groups"&&groupDone\)\|\|\(ts\[i\]==="knockout"&&knockoutDone\)/);
  assert.match(html, /\(done\?" tab-complete":""\)/);
  assert.match(html, /class="tab-done-badge" aria-label="'\+T\("tabComplete"\)\+'"/);
  assert.doesNotMatch(html, /class="tab-done-badge"[^>]*>✓<\/span>/);
});

test("group matches render chronologically without changing fixture identity", () => {
  assert.match(html, /function chronologicalGroupMatches\(gk\)/);
  assert.match(html, /return Date\.parse\(left\.m\.date\|\|""\)-Date\.parse\(right\.m\.date\|\|""\)/);
  assert.match(html, /var mi=ordered\[oi\]\.mi,m=ordered\[oi\]\.m/);
});

test("group data enrichment orients reversed ESPN fixtures to app fixture slots", () => {
  const schedule = extractVarExpression("MATCH_SCHEDULE");
  assert.equal(schedule["760485"].home, "巴拿马");
  assert.equal(schedule["760485"].away, "英格兰");
  assert.equal(matchDetails["760485"].homeScore, 0);
  assert.equal(matchDetails["760485"].awayScore, 2);

  assert.match(html, /function orientOddsToFixture\(odds,flip\)/);
  assert.match(html, /var sameDirection=ms\.group===grp&&ms\.home===m\.h&&ms\.away===m\.a/);
  assert.match(html, /var reverseDirection=ms\.group===grp&&ms\.home===m\.a&&ms\.away===m\.h/);
  assert.match(html, /m\.scheduleFlip=reverseDirection/);
  assert.match(html, /m\.actualHs=String\(reverseDirection\?md\.awayScore:md\.homeScore\)/);
  assert.match(html, /m\.actualAs=String\(reverseDirection\?md\.homeScore:md\.awayScore\)/);
  assert.match(html, /getOutcomeOdds\(m\.odds,m\.id,m\.scheduleFlip\)/);
});

test("global control deck combines progress sharing and page actions", () => {
  assert.match(html, /function renderControlDeck\(activeTab,groupDone,knockoutDone\)/);
  assert.match(html, /if\(ge\)ge\.innerHTML=renderControlDeck\(tab,groupDone,knockoutDone\)/);
  assert.match(html, /class="control-deck"/);
  assert.match(html, /class="control-progress /);
  assert.match(html, /class="control-share"/);
  assert.match(html, /class="control-actions /);
  assert.match(html, /role="progressbar"/);
  assert.match(html, /aria-valuenow="'\+progress\.done\+'"/);
  assert.match(html, /\.control-deck\{[^}]*grid-template-areas:"progress share actions"/);
  assert.match(html, /@media\(max-width:1080px\)\{\s*\.control-deck\{[^}]*grid-template-areas:"share" "progress" "actions"/);
  assert.match(html, /koProgressLabel:"淘汰赛进度"/);
  assert.match(html, /groupsCompleteShort:"小组赛已完成"/);
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
  assert.match(html, /hintExpandGroup:"点击小组右侧模拟"/);
  assert.match(html, /hintExpandGroup:"Select a group, then simulate on the right"/);
  assert.match(html, /btnRandAll:"⚡ 重新模拟全部",btnFillRemaining:"✨ 模拟补全剩余"/);
  assert.match(html, /btnRandAll:"⚡ Re-simulate All",btnFillRemaining:"✨ Simulate Remaining"/);
  assert.match(html, /function renderGroupActions\(\)/);
  assert.match(html, /var fillBtn=state\.canFillRemaining\?'<button class="btn-rand btn-main-action" onclick="raGRemaining\(\)">'\+T\("btnFillRemaining"\)/);
  assert.match(html, /'<button class="btn-rand-secondary btn-compact-action" onclick="raG\(\)">'\+T\("btnRandAll"\)/);
  assert.match(html, /class="btn-clear-action" onclick="clearState\(\)"/);
  assert.match(html, /\.btn-text-action\{[^}]*background:transparent/);
  assert.match(html, /\.btn-clear-action\{[^}]*rgba\(220,38,38,0\.06\)/);
  assert.match(html, /\.toolbar-status-chip\{[^}]*cursor:default/);
  assert.doesNotMatch(html, /var h='<div class="topbar actionbar">'\+fillBtn/);
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

test("champion route uses a wider no-scroll layout", () => {
  assert.match(html, /\.cp-route\{[^}]*max-width:min\(1360px,calc\(100vw - 64px\)\)/);
  assert.match(html, /\.cp-route \.cr-s\{[^}]*flex-wrap:wrap/);
  assert.match(html, /\.cp-route \.cr-s\{[^}]*overflow:visible/);
  assert.match(html, /\.cp-route \.cr-step\{[^}]*white-space:nowrap/);
  assert.match(html, /\.cp-route \.cr-arrow\{[^}]*flex:0 0 auto/);
});

test("knockout toolbar can simulate the bracket one round at a time", () => {
  assert.match(html, /btnSimR32:"模拟32强",btnSimR16:"模拟16强",btnSimQF:"模拟8强",btnSimSF:"模拟半决赛"/);
  assert.match(html, /btnSimFinals:"模拟决赛及季军赛",btnKODone:"淘汰赛已完成"/);
  assert.match(html, /function getNextKOSimulationLabel\(\)/);
  assert.match(html, /keys=\["btnSimR32","btnSimR16","btnSimQF","btnSimSF","btnSimFinals"\]/);
  assert.match(html, /function renderKnockoutActions\(groupDone\)/);
  assert.match(html, /class="btn-next-round btn-main-action" onclick="raKONext\(\)"/);
  assert.match(html, /onclick="raKONext\(\)"/);
  assert.match(html, /function getKORounds\(\)/);
  assert.match(html, /function raKONext\(\)/);
  assert.match(html, /\{id:"3RD",ht:ko\["S1"\]\?ko\["S1"\]\.l:null/);
  assert.match(html, /\{id:"FINAL",ht:ko\["S1"\]\?ko\["S1"\]\.w:null/);
});

test("knockout topology follows the official 2026 bracket order", () => {
  const r32 = extractVarExpression("R32D").map((m) => [m.i, m.h, m.a]);
  assert.deepEqual(r32, [
    ["R1", "2A", "2B"], ["R2", "1E", "3_ABCDF"],
    ["R3", "1F", "2C"], ["R4", "1C", "2F"],
    ["R5", "1I", "3_CDFGH"], ["R6", "2E", "2I"],
    ["R7", "1A", "3_CEFHI"], ["R8", "1L", "3_EHIJK"],
    ["R9", "1D", "3_BEFIJ"], ["R10", "1G", "3_AEHIJ"],
    ["R11", "2K", "2L"], ["R12", "1H", "2J"],
    ["R13", "1B", "3_EFGIJ"], ["R14", "1J", "2H"],
    ["R15", "1K", "3_DEIJL"], ["R16", "2D", "2G"],
  ]);
  assert.deepEqual(extractVarExpression("R16P"), [
    ["R2", "R5"], ["R1", "R3"], ["R4", "R6"], ["R7", "R8"],
    ["R11", "R12"], ["R9", "R10"], ["R14", "R16"], ["R13", "R15"],
  ]);
  assert.match(html, /var QFP=\[\["L1","L2"\],\["L5","L6"\],\["L3","L4"\],\["L7","L8"\]\],SFP=\[\["Q1","Q2"\],\["Q3","Q4"\]\]/);
});

test("third-place knockout opponents are driven by FIFA Annex C", () => {
  const options = extractVarExpression("THIRD_PLACE_OPTIONS").split("|");
  const map = new Map(options.map((row) => row.split(":")));
  assert.equal(options.length, 495);
  assert.equal(map.size, 495);
  assert.equal(map.get("EFGHIJKL"), "EJIFHGLK");
  assert.equal(map.get("ABCDEFGH"), "HGBCAFDE");
  assert.match(html, /var THIRD_PLACE_WINNER_COLUMNS=\["1A","1B","1D","1E","1G","1I","1K","1L"\]/);
  assert.match(html, /"1A":"3_CEFHI","1B":"3_EFGIJ","1D":"3_BEFIJ","1E":"3_ABCDF","1G":"3_AEHIJ","1I":"3_CDFGH","1K":"3_DEIJL","1L":"3_EHIJK"/);
  assert.match(html, /function getThirdPlaceOptionMap\(\)/);
  assert.match(html, /var row=getThirdPlaceOptionMap\(\)\[key\]/);
  assert.doesNotMatch(html, /function solve\(idx\)/);
});

test("knockout tab renders the bracket itself before all groups finish", () => {
  assert.doesNotMatch(html, /ko-lock-title/);
  assert.doesNotMatch(html, /lockCopySmart/);
  assert.match(html, /function groupMatchesPlayed\(g\)/);
  assert.match(html, /function lockedDirectSeedInfo\(seed,st\)/);
  assert.match(html, /function resolveKOSlot\(seed,st,t3,complete\)/);
  assert.match(html, /function seedSlotName\(seed,role\)/);
  assert.match(html, /function seedSlotPrimary\(seed,role\)/);
  assert.match(html, /function seedSlotDetail\(seed,role\)/);
  assert.match(html, /function seedSlotKind\(seed,role\)/);
  assert.match(html, /function centerKnockoutScroll\(el\)/);
  assert.match(html, /resolveKOSlot\(m\.h,st,t3,complete\)/);
  assert.match(html, /hSeed:m\.h,aSeed:m\.a/);
  assert.match(html, /if\(!groupDone\)return '<button class="btn-rand-secondary btn-compact-action" onclick="tab=\\'groups\\';render\(\)">'\+T\("returnGroups"\)/);
  assert.doesNotMatch(html, /\.ko-progress-chip\{/);
  assert.doesNotMatch(html, /\.ko-preview-toolbar\{/);
  assert.doesNotMatch(html, /<div class="topbar ko-preview-toolbar"/);
  assert.match(html, /\.bk-row\.is-seed \.seed-token/);
  assert.match(html, /seedRow\(m\.hSeed,m\.seedRole\)/);
  assert.match(html, /if\(canPlay&&!r&&!pending&&!actual\)/);
  assert.match(html, /leaderMin>rowMax/);
  assert.match(html, /if\(!locked\)return null/);
  assert.match(html, /else t3Assign=\{\}/);
  assert.match(html, /var hadBk=!!bkEl/);
  assert.match(html, /else if\(tab==="knockout"\)centerKnockoutScroll\(bkEl2\)/);
  assert.doesNotMatch(html, /h\+='<p style="text-align:center;font-size:11px;color:var\(--ink-light\);margin-bottom:8px">'\+T\("bracketHint"\)/);
});

test("round-by-round simulation is visually prioritized", () => {
  assert.match(html, /\.btn-next-round\{background:var\(--accent-gold\)/);
  assert.match(html, /body\.dark \.btn-next-round\{background:var\(--accent-gold\)/);
});

test("knockout match rows align flag, team, winner marker, and score columns", () => {
  assert.match(html, /\.bk-row\{display:grid;grid-template-columns:22px minmax\(0,1fr\) 12px 22px/);
  assert.match(html, /\.bk-row\.is-seed\{grid-template-columns:22px minmax\(0,1fr\);column-gap:7px\}/);
  assert.match(html, /\.bk-team-wrap\{grid-column:1\/3;min-width:0;display:flex;flex-direction:column;align-items:flex-start\}/);
  assert.match(html, /\.bk-team-chip\{grid-column:1\/3;display:grid;grid-template-columns:16px minmax\(0,1fr\) auto/);
  assert.match(html, /\.bk-team-chip \.team-rank\{justify-self:end/);
  assert.match(html, /\.bk-copy\{min-width:0;display:flex;flex-direction:column/);
  assert.match(html, /\.seed-sub\{display:block;overflow:hidden;text-overflow:ellipsis/);
  assert.match(html, /\.bk-row\.is-seed \.seed-token\{width:22px;height:18px/);
  assert.match(html, /\.bk-row\.is-seed \.win-mark,\.bk-row\.is-seed \.sc\{display:none\}/);
  assert.match(html, /\.bk-row \.win-mark\{[^}]*justify-content:center/);
  assert.match(html, /\.bk-row \.win-mark\.on\{opacity:\.82\}/);
  assert.match(html, /\.bk-row \.sc\{[^}]*text-align:right/);
  assert.match(html, /\.bk-row\.is-cp \.win-mark\.on\{color:var\(--accent-gold-dark\)\}/);
  assert.match(html, /\.bk-m\.is-final \.bk-row\{padding-left:6px;padding-right:6px\}/);
  assert.match(html, /\.bk-m\.is-final \.bk-row\.is-cp\{margin:0\}/);
  assert.match(html, /\.bk-act\{display:grid;grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
  assert.match(html, /\.bk-act button\{min-width:0;min-height:28px/);
  assert.match(html, /\.bk-act\.is-result\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(html, /function teamRow\(team,isCp,won,score,seed,role\)/);
  assert.ok(html.includes('<span class="bk-team-wrap">\'+teamProfileInline(team,"bk-team-chip")'));
  assert.ok(html.includes('<span class="seed-sub">\'+escHtml(sub)+\'</span>'));
  assert.match(html, /<span class="win-mark'\+\(won\?" on":""\)\+'">✓<\/span><span class="sc">'\+score\+'<\/span>/);
  assert.match(html, /function koActionLabel\(team\)/);
  assert.match(html, /T\("simulateShort"\)/);
  assert.match(html, /simulateShort:"模拟"/);
});

test("completed knockout results flow from ESPN snapshot into bracket cards and details", () => {
  const schedule = extractVarExpression("MATCH_SCHEDULE");
  const southAfricaCanada = schedule["760486"];
  assert.ok(southAfricaCanada, "South Africa vs Canada knockout match must be embedded");
  assert.notEqual(southAfricaCanada.stage, "group");
  assert.equal(southAfricaCanada.completed, true);
  assert.equal(southAfricaCanada.home, "南非");
  assert.equal(southAfricaCanada.away, "加拿大");
  assert.equal(southAfricaCanada.homeScore, 0);
  assert.equal(southAfricaCanada.awayScore, 1);
  assert.equal(southAfricaCanada.winner, "加拿大");

  const detail = matchDetails["760486"];
  assert.ok(detail, "completed knockout match details must be refreshed");
  assert.equal(detail.homeScore, 0);
  assert.equal(detail.awayScore, 1);
  assert.equal(detail.goalEventsStatus, "complete");

  assert.match(html, /function orientKOMatchResult\(rec,ht,at\)/);
  assert.match(html, /function getActualKOMatchResult\(id,ht,at\)/);
  assert.match(html, /var r=ko\[m\.id\],actual=!r\?getActualKOMatchResult\(m\.id,m\.ht,m\.at\):null,shown=r\|\|actual/);
  assert.match(html, /var hw=shown&&shown\.w===ht,aw=shown&&shown\.w===at/);
  assert.match(html, /if\(actual\)h\+='<div class="bk-decision">'\+escHtml\(T\("actualScore"\)\)\+'<\/div>'/);
  assert.match(html, /else if\(canPlay&&actual\)/);
  assert.match(html, /timelineFromActual\(actual\.id,actual,home,away\)/);
});

test("pending knockout seed rows split slot labels from source details", () => {
  assert.match(html, /\.bk-wrap\{overflow-x:auto;padding:16px clamp\(8px,2vw,24px\) 40px/);
  assert.match(html, /\.bk\{--bk-card-w:156px;--bk-preview-h:94px;display:flex;align-items:stretch;width:max-content;min-width:max-content;margin:0 auto\}/);
  assert.match(html, /\.bk-round\{display:flex;flex:0 0 var\(--bk-card-w\);width:var\(--bk-card-w\)/);
  assert.match(html, /\.bk-round\.final-col\{flex:0 0 var\(--bk-card-w\);width:var\(--bk-card-w\);min-width:0;padding:0;justify-content:center/);
  assert.match(html, /\.bk-m\.is-preview\{height:var\(--bk-preview-h\);justify-content:space-between\}/);
  assert.match(html, /\.bk-meta\{display:flex;flex-direction:column;align-items:stretch;justify-content:center/);
  assert.match(html, /\.bk-meta-line\{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis\}/);
  assert.match(html, /\.bk-meta-main\{display:flex;align-items:center;justify-content:space-between/);
  assert.match(html, /\.bk-meta-detail\{[^}]*-webkit-line-clamp:2/);
  assert.match(html, /\.bk\{--bk-card-w:136px;--bk-preview-h:84px\}/);
  assert.match(html, /\.bk\{--bk-card-w:144px;--bk-preview-h:92px\}/);
  assert.match(html, /\.bk-row\.is-seed\{grid-template-columns:20px minmax\(0,1fr\);column-gap:6px\}/);
  assert.match(html, /\.bk-row\.is-seed\{grid-template-columns:21px minmax\(0,1fr\);column-gap:6px\}/);
  assert.doesNotMatch(html, /\.bk>\.bk-round:first-child,\.bk>\.bk-round:last-child\{min-width:/);
  assert.match(html, /\.bk-vs\+\.bk-row\{margin-top:2px\}/);
  assert.match(html, /function seedShort\(seed\)\{return seed&&seed\.indexOf\("3_"\)===0\?"3":\(\//);
  assert.match(html, /seed\.charAt\(1\)\+seed\.charAt\(0\):seed/);
  assert.match(html, /seedDirectCompact:"\{group\} 第\{rank\}"/);
  assert.match(html, /seedThirdPrimary:"第三名"/);
  assert.match(html, /seedThirdDetail:"候选 \{groups\}"/);
  assert.match(html, /if\(role==="loser"\|\|role==="winner"\)return "advancer"/);
  assert.match(html, /return '<div class="bk-row is-seed is-'\+kind\+'/);
  assert.match(html, /\.bk-row\.is-direct \.seed-token\{color:var\(--ink-medium\)\}/);
  assert.match(html, /\.bk-row\.is-third \.seed-token\{background:rgba\(229,181,71,0\.12\)/);
  assert.match(html, /var detail=seedSlotDetail\(seed,role\)/);
  assert.match(html, /function bkRound\(title,matches,cp,canPlay\)/);
  assert.match(html, /bkMatch\(matches\[i\],cp,canPlay\)/);
  assert.match(html, /function bkMatch\(m,cp,canPlay\)/);
  assert.match(html, /canPlay=!!canPlay/);
  assert.match(html, /\+\(canPlay\?"":" is-preview"\)\+/);
  assert.match(html, /if\(canPlay&&!r&&!pending&&!actual\)/);
  assert.ok(html.includes('<span class="seed-token">\'+escHtml(seedShort(seed))+\'</span><span class="bk-copy"><span class="name">\'+escHtml(seedSlotPrimary(seed,role))'));
  assert.ok(html.includes('<span class="seed-sub">\'+escHtml(detail)+\'</span>'));
  assert.doesNotMatch(html, /<span class="win-mark"><\/span><span class="sc"><\/span><\/div>';\n\}/);
});

test("knockout bracket shrink-wraps so wide screens center the full chart", () => {
  assert.match(html, /\.bk\{[^}]*width:max-content;min-width:max-content;margin:0 auto/);
  assert.doesNotMatch(html, /\.bk\{[^}]*min-width:min-content/);
  assert.match(html, /function centerKnockoutScroll\(el\)\{/);
});

test("knockout cards show source groups only in round-of-32 metadata", () => {
  assert.match(html, /function koGroupMeta\(ht,at\)/);
  assert.match(html, /function koShowsGroupMeta\(id\)\{return id&&id\.charAt\(0\)==="R";\}/);
  assert.match(html, /function formatVenueName\(venue\)/);
  assert.match(html, /function formatVenueCityCompact\(venue\)/);
  assert.match(html, /var KO_SCHEDULE_INDEX=null/);
  assert.match(html, /function buildKOScheduleIndex\(\)/);
  assert.match(html, /function getKOMatchSchedule\(id\)/);
  assert.match(html, /function koScheduleLabelMatchesSeed\(label,seed\)/);
  assert.match(html, /var group=TEAM_GROUP\[label\]/);
  assert.match(html, /function koFindRIdForScheduleMatch\(match\)/);
  assert.match(html, /if\(!rid\)rid=koFindRIdForScheduleMatch\(m\)/);
  assert.match(html, /function koMatchMeta\(m,ht,at\)/);
  assert.ok(html.includes("var s=getKOMatchSchedule(m.id);"));
  assert.ok(html.includes('var time=s&&s.date?formatMatchTime(s.date):(LANG==="en"?"Time TBD":"时间待定");'));
  assert.ok(html.includes('var venue=s&&s.venue?formatVenueName(s.venue):(LANG==="en"?"Venue TBD":"场地待定");'));
  assert.ok(html.includes("var fullVenue=s&&s.venue?formatVenue(s.venue):venue;"));
  assert.ok(html.includes("var city=s&&s.venue?formatVenueCityCompact(s.venue):\"\";"));
  assert.doesNotMatch(html, /var time=LANG==="en"\?"Time TBD":"时间待定"/);
  assert.doesNotMatch(html, /var venue=LANG==="en"\?"Venue TBD":"场地待定"/);
  assert.ok(html.includes('var hasTeams=!!(ht&&at),group=hasTeams?koGroupMeta(ht,at):"",stage=koStageLabel(m.id);'));
  assert.ok(html.includes('var source=koShowsGroupMeta(m.id)&&hasTeams?group:"";'));
  assert.ok(html.includes('var stageText=stage+(source?" · "+source:"");'));
  assert.ok(html.includes('var line2=venue+(city?" · "+city:"");'));
  assert.match(html, /aria-label="'\+escHtml\(label\)\+'"/);
  assert.match(html, /<span class="bk-meta-line bk-meta-main"><span class="bk-meta-stage">'\+escHtml\(stageText\)\+'<\/span><span class="bk-meta-time">'\+escHtml\(time\)\+'<\/span><\/span><span class="bk-meta-line bk-meta-detail">'\+escHtml\(line2\)\+'<\/span>/);
  assert.doesNotMatch(html, /class="bk-meta[^"]*" title="/);
  assert.match(html, /'<div class="bk-meta'\+\(\(!ht\|\|!at\)\?" is-pending":""\)\+'/);
  assert.match(html, /h\+=koMatchMeta\(m,ht,at\)/);
});

test("knockout round labels use a balanced scale with a larger final title", () => {
  assert.match(html, /\.bk-title\.stage-label\{font-size:1\.35rem/);
  assert.match(html, /\.bk-title\.stage-label\{[^}]*letter-spacing:0;line-height:1;min-height:26px;display:flex/);
  assert.match(html, /\.bk-title\.stage-label\{font-size:1\.05rem\}/);
  assert.match(html, /\.bk-final-stack,\.bk-third-stack\{width:100%;display:flex;flex-direction:column;align-items:stretch;justify-content:center\}/);
  assert.match(html, /\.bk-final-stack \.bk-title\.final-title\{font-size:1\.7rem/);
  assert.match(html, /\.bk-round\.final-col \.bk-title\.third-title\{font-size:1\.45rem/);
  assert.match(html, /\.bk-final-stack \.bk-title\.final-title\{font-size:1\.35rem\}/);
  assert.match(html, /\.bk-round\.final-col \.bk-title\.third-title\{font-size:1\.15rem\}/);
  assert.match(html, /<div class="bk-title stage-label">'\+title\+'<\/div>/);
  assert.match(html, /<div class="bk-round final-col"><div class="bk-final-stack">/);
  assert.match(html, /<div class="bk-title final-title">'\+cupIcon\(\)\+' '\+T\("finalLabel"\)/);
  assert.match(html, /<div class="bk-third-stack"><div class="bk-title third-title">'\+T\("third"\)/);
  assert.match(html, /<div class="bk-title third-title">'\+T\("third"\)/);
  assert.match(html, /r32:"R32",r16:"R16",qf:"QF",sf:"SF"/);
});

test("embedded knockout schedule includes dated venues for every bracket match", () => {
  const schedule = extractVarExpression("MATCH_SCHEDULE");
  const knockout = Object.values(schedule).filter((match) => match.stage !== "group");
  const counts = knockout.reduce((acc, match) => {
    acc[match.stage] = (acc[match.stage] || 0) + 1;
    return acc;
  }, {});
  assert.deepEqual(counts, { R: 16, L: 8, Q: 4, S: 2, "3RD": 1, FINAL: 1 });
  for (const match of knockout) {
    assert.ok(match.date, `${match.id} must have a kickoff date`);
    assert.ok(match.venue?.name_cn, `${match.id} must have a Chinese venue name`);
    assert.ok(match.venue?.city_cn, `${match.id} must have a Chinese venue city`);
  }
  const final = knockout.find((match) => match.stage === "FINAL");
  assert.equal(final.date, "2026-07-19T19:00Z");
  assert.equal(final.venue.name_cn, "大都会人寿体育场");
  assert.equal(final.venue.city_cn, "新泽西州东卢瑟福");
});

test("stats tab has a distinct selected state and non-recursive photo priming", () => {
  assert.match(html, /\.tabs button\.tab-scorers\.on\{background:linear-gradient/);
  assert.match(html, /var cls='tab-'\+ts\[i\]\+\(tab===ts\[i\]\?" on":""\)/);
  assert.match(html, /<button class="'\+cls\+'"/);
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

test("language switch clears stale toast copy", () => {
  assert.match(html, /function hideToast\(\)/);
  assert.match(html, /el\.classList\.remove\("show"\);el\.textContent=""/);
  assert.match(html, /function toggleLang\(\)[\s\S]*hideToast\(\);applyI18N\(\);render\(\);/);
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
