# 2026 World Cup Predictor

> Play the entire 2026 World Cup in one browser tab, then ask Codex to keep the prediction, live data, scoring, and release checks honest.

<p align="center">
  <a href="https://www.cameraclaw.cn/2026"><strong>Live Demo</strong></a>
  ·
  <a href="#why-star-this">Why Star This</a>
  ·
  <a href="#choose-your-path">Choose Your Path</a>
  ·
  <a href="#screenshots">Screenshots</a>
  ·
  <a href="#codex-skill">Codex Skill</a>
  ·
  <a href="#developer-workflow">Developer Workflow</a>
  ·
  <a href="#中文说明">中文说明</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/World_Cup_2026-48_teams-d6aa48?style=for-the-badge">
  <img src="https://img.shields.io/badge/Matches-104-111827?style=for-the-badge">
  <img src="https://img.shields.io/badge/App-single_file_HTML-0f766e?style=for-the-badge">
  <img src="https://img.shields.io/badge/ESPN-live_results-991b1b?style=for-the-badge">
  <img src="https://img.shields.io/badge/Codex-Skill-2563eb?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-64748b?style=for-the-badge">
</p>

<p align="center">
  <a href="https://www.cameraclaw.cn/2026">
    <img src="docs/readme-groups.jpg" alt="2026 World Cup predictor group stage screen" width="900">
  </a>
</p>

Looking for a 2026 FIFA World Cup predictor, World Cup 2026 bracket simulator, or shareable football prediction game? This repo is not just a champion picker. It is a full tournament workspace: simulate 48 teams, override the matches you care about, watch the bracket unfold, inspect scorer stories, share a champion poster, and use the bundled Codex skill when you want the data and app checked instead of guessed.

| Surface | Use it when you want to | Start |
| --- | --- | --- |
| Browser app | Fill the tournament fast, tweak scores manually, inspect scorers, and send a read-only bracket to someone else. | [Open the live demo](https://www.cameraclaw.cn/2026) |
| Codex Skill mode | Let Codex launch the app, guide a prediction, fetch live ESPN context, score a bracket, or audit the repo before release. | Use `$world-cup-2026-predictor` |

It is an unofficial fan and software project. It is not affiliated with FIFA, and it is not betting advice.

## Why Star This

- You want a no-login 2026 FIFA World Cup bracket that people can open, play, and share quickly.
- You want a small static app that still carries real data contracts: ESPN snapshots, match venues, rankings, odds completions, scorers, assists, extra time, shootouts, and validation scripts.
- You want a concrete Codex skill example: not a README wrapper, but a runnable skill with launch, live-result, scoring, freshness, maintenance, and release-check workflows.
- You want a benchmark target for football prediction projects: `Random baseline`, `Strength model`, and `Ensemble model` are exposed in the UI and validated in tests.

Useful GitHub search phrases for this repo:

```text
2026 FIFA World Cup predictor
World Cup 2026 bracket simulator
FIFA World Cup bracket predictor
football prediction game
Codex skill example
ESPN soccer scoreboard parser
```

## What Makes It Fun

Open the page, press simulate, and you get a complete tournament. Then the useful part starts: change one result, see the table move, carry the bracket into knockouts, track who scored, and share a finished story instead of a spreadsheet.

The Codex skill adds the second layer. It can explain how to play, run the same app locally, check whether ESPN mappings drifted, compare predictions with real results, and validate that the shipped skill still matches the canonical source.

## Benchmark

Most World Cup projects are one of three things: a prediction pool, a model notebook, or a bracket library. This repo deliberately combines the good parts without adding accounts or a backend.

| Benchmark | What good tools do | This project adds |
| --- | --- | --- |
| Prediction pool | Make it easy to finish and share a bracket. | Local-only state, compact share URLs, read-only shared views, and no sign-in wall. |
| Tournament manager | Keep the bracket topology explicit. | 2026 48-team groups, Round of 32 third-place placement, venues, third-place match, and share-state tests. |
| Modeling repo | Explain and validate the model. | `Random baseline`, `Strength model`, and `Ensemble model`, plus event-level goals, own goals, penalties, extra time, and shootouts. |
| Skill package | Give users repeatable commands, not vague prompts. | Installable Codex skill with launch, play, live-result, scoring, freshness, maintenance, and deployment validation workflows. |

## Highlights

- Full 2026 structure: 48 teams, 12 groups, 72 group matches, 32-team knockout bracket, and 104 total matches.
- Fast play: simulate all groups, finish one knockout round, or run the whole tournament.
- Manual control: override scores, pick scorers, and keep the bracket responsive instead of frozen.
- Three prediction modes: Random baseline, Strength model, and Ensemble model.
- Event-aware simulation: goal minutes, scorers, assists, own goals, penalties, extra time, and shootouts.
- Data view: goal and assist leaderboards with squad photos where available.
- Share view: champion poster plus compact links (`#s=` when possible, `#p=` when full metadata is needed).
- Real-result context: completed ESPN-backed snapshots can be embedded and used for scoring.
- Bilingual UI: Chinese/English, light/dark themes, and a small in-app help surface.
- Real skill behavior: commands for play, live results, scoring, freshness checks, maintenance, and deployment validation.

## Live Demo

Open the current public build:

[https://www.cameraclaw.cn/2026](https://www.cameraclaw.cn/2026)

The app is static. All prediction state lives in the browser through local storage or URL hashes. No backend is required for normal play.

If the project helps you run a bracket night, test a football model, or build a Codex skill, star the repo so it is easier for other World Cup and agent-tooling people to find.

## Screenshots

| Group stage and live result context | Knockout bracket |
|---|---|
| <img src="docs/readme-groups.jpg" alt="Group stage with match details" width="100%"> | <img src="docs/readme-knockout.jpg" alt="Knockout bracket" width="100%"> |

| Scorers and assists | Share poster and short link |
|---|---|
| <img src="docs/readme-stats.jpg" alt="Scorer and assist leaderboard" width="100%"> | <img src="docs/readme-share.jpg" alt="Share poster modal" width="100%"> |

## Choose Your Path

### Browser mode vs Codex Skill mode

| Mode | Best for | Start here |
| --- | --- | --- |
| Browser mode | Playing the predictor directly, editing scores, sharing a bracket, and checking the score tab. | Open the live site or run the static app locally. |
| Codex Skill mode | Asking Codex to guide, generate, score, inspect, repair, validate, or explain the workflow. | Use `$world-cup-2026-predictor` followed by a natural-language task. |

Install -> Learn -> Use:

1. Install or open: use the live site for browser play, or install the Codex plugin/skill for agent-assisted workflows.
2. Learn the commands: read the examples below, use the plugin prompt chips, or open the in-app `?` help.
3. Use the workflow: ask Codex for guided play, one-shot simulation, live results, scoring, or maintenance review.
4. Verify the result: browser workflows end with a champion/share/score state; skill workflows end with source output, tests, or validators.

### Open The App Locally

```bash
git clone https://github.com/jiaqi015/WorldCup2026-Predictor-Skill.git
cd WorldCup2026-Predictor-Skill
python3 -m http.server 8765
```

Then open:

[http://localhost:8765](http://localhost:8765)

For the persistent macOS preview used during development:

```bash
./scripts/manage_local_preview.sh install
./scripts/manage_local_preview.sh status
./scripts/manage_local_preview.sh logs
```

The persistent preview serves the canonical root `index.html`.

### Play A Bracket

1. Choose a gameplay mode: Standard, Fun, or Upset.
2. Pick a prediction model: Random baseline, Strength model, or Ensemble model.
3. Simulate or manually edit group-stage scores.
4. Open the knockout tab and simulate one round at a time, or simulate the full bracket.
5. Inspect the Data tab for top scorers and assists.
6. Generate a champion poster or copy a share link.
7. When real results are available, compare your prediction against completed matches.

Shared links open in a read-only view, so recipients can inspect the bracket without changing the original prediction.

## Codex Skill

This repository includes an installable Codex skill:

```text
$world-cup-2026-predictor
```

Use it when you want Codex to operate the app, inspect live result data, or maintain the repo.

### Core Commands

```text
$world-cup-2026-predictor 打开预测器，陪我做一版完整预测
$world-cup-2026-predictor launch the predictor and guide me through a complete bracket

$world-cup-2026-predictor 一键生成完整预测并总结冠军之路
$world-cup-2026-predictor generate a full tournament prediction and summarize the champion path

$world-cup-2026-predictor 查询最新已结束的世界杯比赛
$world-cup-2026-predictor check the latest completed World Cup matches from ESPN

$world-cup-2026-predictor 解释我的预测怎么按真实赛果计分
$world-cup-2026-predictor explain or score my bracket against real results

$world-cup-2026-predictor CR 并修复球队、阵容、位置和 ESPN 映射问题
$world-cup-2026-predictor review, repair, and validate the predictor data and bundled app
```

Useful skill play styles:

| Style | What Codex should do |
| --- | --- |
| Guided play | Launch the app, keep the browser open, and walk through group stage, knockout, scorer selection, and sharing. |
| One-shot simulation | Complete all 72 group matches and every knockout match, then report champion, runner-up, third place, and share status. |
| Live-results check | Fetch ESPN's current scoreboard feed and report source, fetch time, completed count, and relevant matches. |
| Today/upcoming fixtures | Use the normalized ESPN contract to answer today's completed matches or the next fixtures. |
| ESPN mapping check | Detect whether ESPN team names no longer map cleanly to the app's team aliases. |
| Scoring explainer | Explain or calculate group, knockout, and podium points against real results. |
| Maintenance review | Inspect app/data/skill drift, patch the canonical source, sync the bundled asset, and run validation. |

Additional useful prompts:

```text
$world-cup-2026-predictor show today's completed matches and the next upcoming fixtures from ESPN
$world-cup-2026-predictor check whether ESPN team-name mapping has drifted
$world-cup-2026-predictor 检查这个 skill 是不是最新版本
$world-cup-2026-predictor check whether this skill is up to date
```

### Install As A Codex Plugin

```bash
codex plugin marketplace add jiaqi015/WorldCup2026-Predictor-Skill --ref main
codex plugin add world-cup-2026-predictor@world-cup-2026
```

Upgrade later:

```bash
codex plugin marketplace upgrade world-cup-2026
codex plugin add world-cup-2026-predictor@world-cup-2026
```

The skill does not silently auto-update on every use. Installed skills are local packages so prediction runs stay reproducible. Use the freshness check when you want to compare local version/commit with remote `main`, then run the explicit upgrade commands above.

### Install Only The Skill

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo jiaqi015/WorldCup2026-Predictor-Skill \
  --path skills/world-cup-2026-predictor
```

## Model And Data

The predictor combines a compact browser engine with offline data artifacts.

### Runtime Prediction Engine

- `random`: neutral baseline for comparison.
- `strength`: blends team strength, rankings, and available market-style context.
- `ensemble`: adds uncertainty calibration and provider-style probability inputs.
- Standard mode keeps favorites more stable.
- Fun mode can clone star-player behavior for entertainment scenarios.
- Upset mode increases chaos and underdog paths.

Scores are sampled with mode-specific calibration. Goal scorers and assists use position weights plus separated goal-threat and assist-threat multipliers. Knockout simulation records regulation, extra time, shootout metadata, penalties, and own goals as explicit event types.

### Embedded Tournament Data

- 12 groups and 48 teams in `GD`.
- 72 fixed group fixtures.
- 32-team knockout topology through `R32D`, `R16P`, `QFP`, and `SFP`.
- 528-player simulation roster embedded in `index.html`.
- 1,248-player squad snapshot under `data/`.
- Match schedule, match details, actual-result snapshots, rankings, odds completions, Elo estimates, and player threat maps under `data/`.

Important accuracy notes:

- Some Elo values are marked as low-confidence FIFA-rank regression estimates.
- Some three-way odds are model completions of partial source fields.
- Player and squad data is a dated simulation snapshot, not a final FIFA registration list.
- ESPN public payloads are external contracts and can change.

## Real Result Scoring

Predictions can be scored once real results are available.

| Correct prediction | Points |
|---|---:|
| Group result direction | 3 |
| Exact group score bonus | 2 |
| Team reaches Round of 16 | 5 |
| Team reaches quarterfinal | 8 |
| Team reaches semifinal | 12 |
| Team reaches final | 16 |
| Third place | 15 |
| Runner-up | 20 |
| Champion | 30 |

Group games are compared by fixed fixture slot. Knockout scoring compares which teams reach each round, so it still works when the predicted and real matchups differ.

## Developer Workflow

Root `index.html` is canonical. The bundled skill app is a synced copy and must not become a second implementation.

```bash
python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py
python3 skills/world-cup-2026-predictor/scripts/validate_predictor.py
python3 scripts/full_system_experience_test.py
python3 scripts/release_check.py
git diff --check
```

Useful development commands:

```bash
python3 scripts/validate_match_data.py
python3 scripts/validate_prediction_data.py
python3 scripts/validate_squads.py
python3 scripts/full_system_experience_test.py --public-url https://www.cameraclaw.cn/2026
node --test
```

Live-result check:

```bash
python3 skills/world-cup-2026-predictor/scripts/live_results.py
python3 skills/world-cup-2026-predictor/scripts/live_results.py --json
python3 skills/world-cup-2026-predictor/scripts/live_results.py --mode mapping
```

Deploy the current working tree to the existing Vercel project:

```bash
vercel --prod --yes
```

After deploy, verify the actual public route:

```bash
python3 scripts/full_system_experience_test.py --skip-browser --public-url https://www.cameraclaw.cn/2026
python3 scripts/verify_public_deployment.py --base-url https://www.cameraclaw.cn/2026
```

## Repository Layout

```text
.
├── index.html
├── data/
│   ├── matches/
│   ├── prediction/
│   ├── rag/kimi-world-cup-report/
│   ├── rankings/
│   ├── schema/prediction-domain.v1.json
│   └── squads/
├── docs/
│   ├── domain-model.md
│   ├── prediction-architecture.md
│   ├── rag-corpus.md
│   └── readme-*.jpg
├── scripts/
│   ├── build_prediction_data.py
│   ├── embed_prediction_data.py
│   ├── full_system_experience_test.py
│   ├── live-data and validation helpers
│   └── release_check.py
├── skills/world-cup-2026-predictor/
│   ├── SKILL.md
│   ├── assets/predictor/index.html
│   ├── references/predictor-model.md
│   └── scripts/
├── test/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── RELEASING.md
├── LICENSE
└── NOTICE.md
```

Key files:

| Path | Purpose |
|---|---|
| `index.html` | Canonical single-file web app |
| `skills/world-cup-2026-predictor/assets/predictor/index.html` | Bundled app shipped with the Codex skill |
| `skills/world-cup-2026-predictor/SKILL.md` | Skill trigger scope and operational workflow |
| `skills/world-cup-2026-predictor/references/user-playbooks.json` | Install/learn/use journey, five skill modes, and 20 user scenarios |
| `skills/world-cup-2026-predictor/references/predictor-model.md` | Model invariants and maintenance notes |
| `data/prediction/prediction_data_v1.json` | Generated prediction dataset |
| `data/matches/` | Schedule and match detail snapshots |
| `data/schema/prediction-domain.v1.json` | Machine-readable domain catalog |
| `scripts/full_system_experience_test.py` | Product-level skill/browser/share/public deployment validation |
| `scripts/release_check.py` | Main release validation gate |
| `scripts/embed_prediction_data.py` | Embeds generated data into `index.html` |
| `scripts/manage_local_preview.sh` | Persistent local preview manager |

## Community And Growth

This project grows best through useful proof, not spam links.

- If you find a bracket-placement, venue, odds, scorer, translation, or ESPN mapping issue, open an issue with the fixture/team and a source link.
- If you compare this with another World Cup predictor, share the concrete difference: format coverage, bracket topology, scoring, data source, or validation.
- If you mention the project in another repository, only do it when it directly answers a question, fixes a bug, or contributes a reusable reference.
- Do not post generic "check my repo" comments. They hurt trust and make the project look weaker.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/promotion-strategy.md](docs/promotion-strategy.md).

## Research Corpus

The repository includes a page-cited RAG corpus generated from a 205-page World Cup report.

```bash
python3 scripts/validate_rag_corpus.py
python3 scripts/search_report_rag.py "Brier calibration model drift"
```

See:

- [Domain model](docs/domain-model.md)
- [Prediction architecture](docs/prediction-architecture.md)
- [RAG corpus guide](docs/rag-corpus.md)
- `data/rag/kimi-world-cup-report/chunks.jsonl`

Report-derived claims remain source assertions until independently verified. Retrieved chunks retain page citation and source hash metadata.

## Release Checklist

1. Edit root `index.html` or data/scripts.
2. Sync the bundled skill asset.
3. Run `python3 scripts/release_check.py`.
4. Run `git diff --check`.
5. Browser-test the changed flow locally.
6. Commit and push.
7. Deploy with `vercel --prod --yes`.
8. Verify `https://www.cameraclaw.cn/2026`, not only the Vercel deployment URL.

See [RELEASING.md](RELEASING.md) for semantic versioning, plugin publishing, and tag rules.

## Roadmap

- [x] Complete 48-team browser predictor
- [x] One-click group and knockout simulation
- [x] Strength and ensemble prediction modes
- [x] Event-aware goals, assists, penalties, extra time, and shootouts
- [x] Champion poster and share links
- [x] Live-result and scoring integration
- [x] Codex skill packaging
- [x] Full-system experience validation
- [x] Public Vercel deployment
- [x] Release validation and CI
- [ ] Final official 2026 squad refresh
- [ ] PWA/offline install support

## 中文说明

如果你在找 2026 FIFA World Cup predictor、世界杯 2026 淘汰赛模拟器、足球预测游戏、Codex skill 示例，这个项目就是为这些搜索场景做的。它不是一个只填冠军的小玩具，而是一套完整的 2026 世界杯预测工作台：你可以直接在网页里跑完 104 场比赛，也可以让 Codex 作为 skill 帮你查赛果、解释计分、检查数据、验证发布。

你打开它之后可以做这些事：

- 一键跑完 48 队、12 个小组、104 场比赛；
- 手动改比分、选进球球员，看小组排名和淘汰赛落位怎么变化；
- 生成从 32 强到决赛、季军赛的完整路径；
- 查看射手榜和助攻榜，而不是只看谁夺冠；
- 生成冠军海报和只读分享链接；
- 等真实比赛结束后，用真实赛果给自己的预测计分；
- 让 Codex 检查 ESPN 赛果、球队映射、数据来源、测试和部署状态。

两种用法：

| 模式 | 适合谁 | 从哪开始 |
| --- | --- | --- |
| 浏览器模式 | 想马上玩、改比分、生成海报、发给朋友。 | 打开线上地址，或本地运行静态页面。 |
| Codex Skill 模式 | 想让 Codex 陪玩、一键生成、查赛果、解释计分、CR/修复/验证。 | 使用 `$world-cup-2026-predictor` 加一句自然语言任务。 |

安装 -> 学习 -> 使用：

1. 安装或打开：普通用户打开网页，Codex 用户安装 plugin/skill。
2. 学口令：看下面的常用命令、plugin prompt，或打开网页左上角 `?`。
3. 开始用：选择陪玩、一键生成、查赛果、计分解释，或者让它做维护审查。
4. 验结果：网页以冠军、分享、评分状态为准；skill 以脚本输出、测试和 validator 为准。

在线体验：

[https://www.cameraclaw.cn/2026](https://www.cameraclaw.cn/2026)

本地运行：

```bash
git clone https://github.com/jiaqi015/WorldCup2026-Predictor-Skill.git
cd WorldCup2026-Predictor-Skill
python3 -m http.server 8765
```

然后打开：

[http://localhost:8765](http://localhost:8765)

Codex Skill：

```text
$world-cup-2026-predictor 打开预测器，陪我做一版完整预测
$world-cup-2026-predictor 一键生成完整预测并总结冠军之路
$world-cup-2026-predictor 查询最新已结束的世界杯比赛
$world-cup-2026-predictor 今天有哪些比赛结束了
$world-cup-2026-predictor 接下来最近几场是谁踢谁
$world-cup-2026-predictor 检查 ESPN 队名映射有没有失败
$world-cup-2026-predictor 检查这个 skill 是不是最新版本
$world-cup-2026-predictor 解释我的预测怎么按真实赛果计分
$world-cup-2026-predictor CR 并修复球队、阵容、位置和 ESPN 映射问题
```

维护命令：

```bash
python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py
python3 skills/world-cup-2026-predictor/scripts/validate_predictor.py
python3 scripts/full_system_experience_test.py
python3 scripts/release_check.py
git diff --check
```

预测结果仅用于娱乐和软件实验，不构成事实预测或投注建议。

如果这个项目对你有用，欢迎 star、fork，或者提交数据/赛程/翻译问题。真正有用的反馈比泛泛宣传更能帮项目传播。

## Credits

- Match data and live results: ESPN public scoreboard feed
- Flags: [FlagCDN](https://flagcdn.com/)
- Poster rendering: [html2canvas](https://html2canvas.hertzen.com/)
- Celebration effects: [canvas-confetti](https://github.com/catdad/canvas-confetti)
- Browser automation and maintenance workflow: Codex skill tooling

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
