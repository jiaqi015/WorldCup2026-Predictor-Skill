// Goal: 榜单渲染链 TDD + 全数据集中英混合扫描
import fs from 'fs';
import vm from 'vm';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const re = /<script(?: [^>]*)?>([\s\S]*?)<\/script>/g;
let m, blocks = []; while ((m = re.exec(html))) blocks.push(m[1]);
const main = blocks[2];

const fakeEl = new Proxy({lang:'zh',innerHTML:'',value:'',style:{},textContent:'',classList:{add:()=>{},remove:()=>{},contains:()=>false,toggle:()=>{}},getAttribute:()=>null,setAttribute:()=>{},addEventListener:()=>{},removeEventListener:()=>{},appendChild:()=>{},focus:()=>{},blur:()=>{},click:()=>{}}, {
  get(t,p){ if(p in t) return t[p]; if(p===Symbol.toPrimitive)return ()=>'x'; return ()=>fakeEl; },
  set(t,p,v){ t[p]=v; return true; }
});
const sb = {localStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{}},document:{addEventListener:()=>{},getElementById:()=>fakeEl,documentElement:fakeEl,body:{classList:{add:()=>{},remove:()=>{},contains:()=>false},appendChild:()=>{}},querySelector:()=>fakeEl,querySelectorAll:()=>[fakeEl],createElement:()=>fakeEl,cookie:'',title:'',readyState:'complete'},window:{},location:{hash:'',href:'http://x/',pathname:'/',search:'',origin:'http://x'},navigator:{language:'zh-CN'},history:{pushState:()=>{},replaceState:()=>{}},console,setTimeout,clearTimeout,setInterval,clearInterval,Math,Date,JSON,fetch:()=>Promise.reject('mock'),performance:{now:()=>Date.now()}};
sb.window.localStorage=sb.localStorage; sb.window.document=sb.document; sb.window.location=sb.location; sb.window.navigator=sb.navigator;
vm.createContext(sb);
try { vm.runInContext(main, sb, { timeout: 6000 }); } catch(e) { console.log('Init err:',e.message); }

const {GD, R32D, R16P, QFP, SFP, STRENGTH, MODEL_RANKING, WW, PredictionEngine, PL, POS, EN, STAR_PLAYER, PLAYER_THREATS_MAP, PHOTO_MAP, photoCache, MATCH_DETAILS, getPos, getPhotoUrl, loadPhotos, pn, fi, pos_t, rScorers} = sb;

let totalAsserts = 0, totalFailures = 0;
function assert(name, cond, detail) {
  totalAsserts++;
  if (!cond) { totalFailures++; console.log(`✗ ${name}: ${detail}`); }
}

function simKO(p,g,h,a) {
  const r = PredictionEngine.simulateMatch({predictionMode:p,gameplayMode:g,allowDraw:false,homeTeam:h,awayTeam:a,strengths:STRENGTH,rankings:MODEL_RANKING,goalDistribution:WW});
  return r.homeGoals>r.awayGoals?h:a;
}
function simGroup(p,g,h,a) {
  return PredictionEngine.simulateMatch({predictionMode:p,gameplayMode:g,allowDraw:true,homeTeam:h,awayTeam:a,strengths:STRENGTH,rankings:MODEL_RANKING,goalDistribution:WW});
}
const GW = {"中锋":9,"边锋":7,"前腰":7,"中前卫":4,"后腰":2,"边卫":3,"中卫":1,"门将":0};
const AW = {"中锋":3,"边锋":5,"前腰":7,"中前卫":5,"后腰":4,"边卫":4,"中卫":1,"门将":0};

function weightedPick(players, team, weights, fallback, type) {
  if (!players || !players.length) return null;
  const pool = [];
  for (const p of players) {
    const pos = (POS && POS[team] && POS[team][p]) || '中前卫';
    let w = weights[pos]; if (w === undefined) w = fallback;
    const tEntry = team ? PLAYER_THREATS_MAP[team+'|'+p] : null;
    const entry = tEntry || PLAYER_THREATS_MAP[p];
    if (entry) {
      const mult = type === 'assist' ? entry.a : entry.g;
      if (mult > 0) w = Math.max(1, Math.round(w * mult));
    }
    for (let j = 0; j < w; j++) pool.push(p);
  }
  if (!pool.length) return players[Math.floor(Math.random()*players.length)];
  return pool[Math.floor(Math.random()*pool.length)];
}
function genScorers(team, goals, mode) {
  const players = (mode === 'clone' && STAR_PLAYER[team]) ?
    Array(11).fill(STAR_PLAYER[team]) : (PL[team] || []);
  const events = [];
  for (let i = 0; i < goals; i++) {
    const sc = weightedPick(players, team, GW, 1, 'goal');
    if (!sc) continue;
    const pool = mode === 'clone' ? players : players.filter(x => x !== sc);
    const ast = Math.random() < 0.7 ? weightedPick(pool, team, AW, 1, 'assist') : null;
    events.push({ team, scorer: sc, assist: ast });
  }
  return events;
}

const PAIRS = [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]];
function runGroup(p, g) {
  const allEvents = [];
  for (const grp in GD) {
    const teams = GD[grp];
    for (const [i,j] of PAIRS) {
      const h = teams[i], a = teams[j];
      const r = simGroup(p, g, h, a);
      for (const e of genScorers(h, r.homeGoals, g)) {
        allEvents.push({p:e.scorer,t:e.team,role:'scorer'});
        if (e.assist) allEvents.push({p:e.assist,t:e.team,role:'assister'});
      }
      for (const e of genScorers(a, r.awayGoals, g)) {
        allEvents.push({p:e.scorer,t:e.team,role:'scorer'});
        if (e.assist) allEvents.push({p:e.assist,t:e.team,role:'assister'});
      }
    }
  }
  return allEvents;
}

let posMisses = [], photoMisses = [], enMisses = [], plNotInPl = [];
for (let round = 0; round < 3; round++) {
  for (const [pm, gm] of [['strength','normal'],['strength','clone'],['random','clone'],['random','chaos']]) {
    const evs = runGroup(pm, gm);
    for (const e of evs) {
      if (gm !== 'clone' && !(PL[e.t]||[]).includes(e.p)) { plNotInPl.push(`${pm}+${gm} R${round}: ${e.p} not in PL[${e.t}]`); continue; }
      if (!(POS && POS[e.t] && POS[e.t][e.p])) posMisses.push(`${pm}+${gm} R${round}: getPos(${e.p}, ${e.t}) fallback`);
      if (!getPhotoUrl(e.p, e.t)) photoMisses.push(`${pm}+${gm} R${round}: getPhotoUrl(${e.p}, ${e.t}) null`);
      if (!EN[e.p]) enMisses.push(`${pm}+${gm} R${round}: EN[${e.p}] undefined`);
    }
  }
}

assert('G2.1 PL 完整性', plNotInPl.length===0, `${plNotInPl.length}: ${plNotInPl.slice(0,5).join(' | ')}`);
assert('G2.2 getPos 命中率 100%', posMisses.length===0, `${posMisses.length}: ${posMisses.slice(0,5).join(' | ')}`);
assert('G2.3 getPhotoUrl 命中率 100%', photoMisses.length===0, `${photoMisses.length}: ${photoMisses.slice(0,5).join(' | ')}`);
assert('G2.4 EN 命中率 100%', enMisses.length===0, `${enMisses.length}: ${enMisses.slice(0,5).join(' | ')}`);

let actualPosMisses = [], actualPhotoMisses = [], actualEnMisses = [];
for (const details of Object.values(MATCH_DETAILS || {})) {
  for (const event of details.events || []) {
    if (event.type !== 'goal') continue;
    for (const role of ['scorer', 'assist']) {
      const player = event[`${role}_app_alias`];
      const team = event[`${role}_team_cn`];
      if (!player || !team) continue;
      if (!(POS && POS[team] && POS[team][player])) actualPosMisses.push(`${team}|${player}`);
      if (!getPhotoUrl(player, team)) actualPhotoMisses.push(`${team}|${player}`);
      if (!EN[player]) actualEnMisses.push(`${team}|${player}`);
    }
  }
}
assert('G2.5 真实进球球员位置命中率 100%', actualPosMisses.length===0, `${actualPosMisses.length}: ${actualPosMisses.slice(0,5).join(' | ')}`);
assert('G2.6 真实进球球员头像命中率 100%', actualPhotoMisses.length===0, `${actualPhotoMisses.length}: ${actualPhotoMisses.slice(0,5).join(' | ')}`);
assert('G2.7 真实进球球员英文名命中率 100%', actualEnMisses.length===0, `${actualEnMisses.length}: ${actualEnMisses.slice(0,5).join(' | ')}`);

let leaderboardError = null;
try {
  fakeEl.innerHTML = '';
  rScorers(fakeEl);
} catch (error) {
  leaderboardError = error;
}
assert('G2.8 数据榜运行时不递归爆栈', !leaderboardError, leaderboardError?.message || '');
assert(
  'G2.9 数据榜真实球员姓名位置头像国家队已接入',
  fakeEl.innerHTML.includes('黄仁范') &&
    fakeEl.innerHTML.includes('中前卫') &&
    fakeEl.innerHTML.includes(getPhotoUrl('黄仁范', '韩国')) &&
    fakeEl.innerHTML.includes('alt="韩国"'),
  `name=${fakeEl.innerHTML.includes('黄仁范')} pos=${fakeEl.innerHTML.includes('中前卫')} photo=${fakeEl.innerHTML.includes(getPhotoUrl('黄仁范', '韩国'))} team=${fakeEl.innerHTML.includes('alt="韩国"')}`
);

const KEEP_MIXED = new Set([
  'B费', 'C罗', '希门尼斯MEX', '希门尼斯',
  'Nico冈萨雷斯', 'NicoPaz', 'Nico Paz', 'Nico洛佩斯',
  'JoséManuel洛佩斯', 'José López', 'Jose洛佩斯',
]);
const isCleanDisplayName = (s) => KEEP_MIXED.has(s) || !/[A-Za-z0-9]/.test(s);

let mixedPl = [];
for (const t of Object.keys(PL)) for (const p of PL[t]) if (!isCleanDisplayName(p)) mixedPl.push(`PL[${t}]=${p}`);
assert('G3.1 PL 球员 key 全中文或白名单', mixedPl.length===0, `${mixedPl.length}: ${mixedPl.slice(0,5).join(' | ')}`);

let mixedStar = [];
for (const t of Object.keys(STAR_PLAYER)) { const s = STAR_PLAYER[t]; if (!isCleanDisplayName(s)) mixedStar.push(`STAR[${t}]=${s}`); }
assert('G3.2 STAR_PLAYER 值全中文或白名单', mixedStar.length===0, `${mixedStar.length}: ${mixedStar.slice(0,5).join(' | ')}`);

let starOutsidePl = [];
for (const t of Object.keys(STAR_PLAYER)) {
  const star = STAR_PLAYER[t];
  if (!(PL[t] || []).includes(star)) starOutsidePl.push(`STAR[${t}]=${star}`);
}
assert('G3.2b STAR_PLAYER 均属于球队首发名单', starOutsidePl.length===0, `${starOutsidePl.length}: ${starOutsidePl.slice(0,5).join(' | ')}`);

let mixedEn = [];
for (const k of Object.keys(EN)) if (!isCleanDisplayName(k)) mixedEn.push(k);
assert('G3.3 EN 键全中文或白名单', mixedEn.length===0, `${mixedEn.length}: ${mixedEn.slice(0,5).join(' | ')}`);

let mixedPm = [];
for (const k of Object.keys(PHOTO_MAP)) { const bare = k.includes('|') ? k.split('|')[1] : k; if (!isCleanDisplayName(bare)) mixedPm.push(k); }
assert('G3.4 PHOTO_MAP key 全中文或白名单', mixedPm.length===0, `${mixedPm.length}: ${mixedPm.slice(0,5).join(' | ')}`);

let mixedPos = [];
for (const t of Object.keys(POS)) for (const k of Object.keys(POS[t])) if (!isCleanDisplayName(k)) mixedPos.push(`POS[${t}]=${k}`);
assert('G3.5 POS 球员 key 全中文或白名单', mixedPos.length===0, `${mixedPos.length}: ${mixedPos.slice(0,5).join(' | ')}`);

let mixedPtt = [];
for (const k of Object.keys(PLAYER_THREATS_MAP)) { const bare = k.includes('|') ? k.split('|')[1] : k; if (!isCleanDisplayName(bare)) mixedPtt.push(k); }
assert('G3.6 PLAYER_THREATS_MAP key 全中文或白名单', mixedPtt.length===0, `${mixedPtt.length}: ${mixedPtt.slice(0,5).join(' | ')}`);

console.log(`\n=== ${totalAsserts} asserts, ${totalFailures} failures ===`);
process.exit(totalFailures>0?1:0);
