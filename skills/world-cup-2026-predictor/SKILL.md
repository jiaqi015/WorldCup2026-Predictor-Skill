---
name: world-cup-2026-predictor
description: Launch, use, validate, or maintain the interactive 2026 World Cup predictor; generate group-stage and knockout brackets, query ESPN-backed latest/today/upcoming results, compare predictions with current ESPN results, inspect scoring, and update teams, squads, mappings, or simulation logic. Use for 2026 World Cup prediction and live-score tasks, not unrelated football tournaments or betting advice.
---

# World Cup 2026 Predictor

Use the bundled single-file web app for interactive brackets and the bundled scripts for live-result checks and deterministic validation.

## Choose The Workflow

- For an interactive prediction, launch the web app and use browser automation when available.
- For ESPN-backed latest, today, upcoming, or mapping checks, run the live-results script before answering.
- For completed matches that show scores but no scorers, treat it as a score/detail freshness split: run the full results refresh pipeline, then the live freshness check.
- For code or data changes, read `references/predictor-model.md`, edit the canonical app, sync the bundled asset, then validate.
- For version freshness or upgrade questions, run the update checker and report explicit upgrade commands.
- For a quick health check, run the validator without launching a browser.
- For browser comments or UX bug reports, reproduce the visible flow first, then add or update a focused regression test before validating.
- For onboarding, command discovery, or broad product testing, read `references/user-playbooks.json`; it is the source of truth for the install/learn/use journey, five primary skill modes, and 20 simulated user scenarios.

## User Intent Playbooks

Use these playbooks to map the user's wording to an execution path.

### Launch And Guide

Example prompts:

- `$world-cup-2026-predictor 打开预测器，陪我做一版预测`
- `$world-cup-2026-predictor launch the predictor and help me finish a bracket`

Do this:

1. Start `python3 scripts/serve_predictor.py --port 8000`.
2. Open the printed URL when browser tools are available.
3. Guide the user through group scores, knockout completion, scorers, and sharing.
4. Do not call the run complete until a champion is visible and Share is enabled.

### Generate A Complete Bracket

Example prompts:

- `$world-cup-2026-predictor 一键生成完整预测`
- `$world-cup-2026-predictor simulate the full tournament`

Do this:

1. Launch the app.
2. Pick a compatible gameplay and prediction model when the user does not specify one.
3. Fill all 72 group matches.
4. Complete every knockout match, including final and third-place match.
5. Report champion, runner-up, third place, top scorer/assist leaders if available, and whether a share link was created.

### Score Or Explain A Prediction

Example prompts:

- `$world-cup-2026-predictor 解释我的预测怎么计分`
- `$world-cup-2026-predictor score my bracket against real results`

Do this:

1. Check whether the app state or shared URL contains a completed bracket.
2. Run a fresh live-result check if the user asks for current scoring.
3. Explain group-score points, knockout advancement points, and podium points.
4. If real results are unavailable, say that scoring is waiting on completed ESPN results.

### Check Live Results

Example prompts:

- `$world-cup-2026-predictor 今天结束了哪些比赛`
- `$world-cup-2026-predictor check latest completed matches`
- `$world-cup-2026-predictor 接下来最近几场是谁踢谁`
- `$world-cup-2026-predictor 检查 ESPN 队名映射有没有失败`

Do this:

1. Run `python3 scripts/live_results.py --json --mode latest` for latest completed results.
2. Run `python3 scripts/live_results.py --json --mode today --date YYYY-MM-DD --timezone <zone>` when the user says today; state the absolute date.
3. Run `python3 scripts/live_results.py --json --mode upcoming --upcoming N` for upcoming fixtures.
4. Run `python3 scripts/live_results.py --json --mode mapping` for ESPN team-name mapping drift.
5. Report `fetched_at`, completed count, source, and the relevant matches or mapping issues.
6. Treat ESPN as an external source; if the fetch or mapping fails, report the failure instead of inventing a score.
7. If the app has a completed score but missing scorer events, run `python3 scripts/refresh_results.py` from the source repo; verify with `python3 scripts/refresh_results.py --check --live-check`.

### Maintain Or Review The Product

Example prompts:

- `$world-cup-2026-predictor CR 预测器代码和数据`
- `$world-cup-2026-predictor 修这个浏览器反馈并加测试`
- `$world-cup-2026-predictor validate all teams, squads, positions, and ESPN mappings`
- `$world-cup-2026-predictor 检查这个 skill 是不是最新版本`

Do this:

1. For freshness checks, run `python3 scripts/check_updates.py --json`, then report local version, local commit when known, remote version, remote commit, local dirty state, and plugin upgrade commands.
2. For review or repair work, read `references/predictor-model.md`.
3. Identify whether the change affects UI, embedded data, scripts, or skill packaging.
4. Edit the root `index.html` for app changes, not only the bundled asset.
5. Add or update focused tests for the user-visible behavior.
6. Sync the bundled app and run the validation commands below.

## Launch The Predictor

Run:

```bash
python3 scripts/serve_predictor.py --port 8000
```

Open the printed local URL. Keep the server process running until browser verification is complete.

For a full prediction:

1. Choose Normal, Clone, or Chaos mode.
2. Fill or randomize all 72 group matches.
3. Open Knockout and complete or randomize the bracket.
4. Verify that a champion appears and Share becomes enabled.
5. Treat simulated outcomes as entertainment, not factual forecasts or betting guidance.

## Check Current Results

Run:

```bash
python3 scripts/live_results.py
python3 scripts/live_results.py --json
python3 scripts/live_results.py --mode today --date 2026-06-17 --timezone Asia/Shanghai
python3 scripts/live_results.py --mode upcoming --upcoming 5
python3 scripts/live_results.py --mode mapping
```

Always use a fresh result check when the user asks for current, latest, today, upcoming, completed, or live tournament information. ESPN stage IDs and payload fields are external contracts; report a fetch or mapping failure instead of inventing a result.

The ESPN contract lives in `scripts/espn_source.py`. Keep new live-result commands on that normalized contract instead of parsing ESPN payloads independently.

## Maintain The App

Read `references/predictor-model.md` before changing teams, players, bracket mappings, scoring, or ESPN parsing.

When working in this source repository:

1. Edit the root `index.html`; it is the canonical GitHub Pages app.
2. For match result/data changes, run `python3 scripts/refresh_results.py` so `MATCH_SCHEDULE`, `MATCH_DETAILS`, prediction data, root app, and bundled asset advance together.
3. Otherwise run `python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py`.
4. Run the validator.
5. Launch the app and browser-test the changed user flow.

When the skill is installed standalone and no repository root exists, edit `assets/predictor/index.html` directly.

Do not add copyrighted music. The app intentionally works without bundled audio.

## Keep The Skill Current

Run:

```bash
python3 scripts/check_updates.py
python3 scripts/check_updates.py --json
```

Do not silently auto-update on every skill use. Treat the installed skill as a reproducible local package. When the user asks for latest version, upgrade, freshness, or a maintenance/deploy check, compare the local install with remote `main` and show the explicit commands:

```bash
codex plugin marketplace upgrade world-cup-2026
codex plugin add world-cup-2026-predictor@world-cup-2026
```

For skill-only installs, the installer refuses to overwrite an existing destination. Tell the user to remove the old skill directory first, then reinstall from GitHub.

## Validate

Run from the skill directory:

```bash
python3 scripts/validate_predictor.py
```

In the source repository, also run:

```bash
python3 scripts/refresh_results.py --check
python3 scripts/release_check.py
git diff --check
```

Before deploys or live-data fixes, use:

```bash
python3 scripts/refresh_results.py --check --live-check
```

The validator checks skill structure, tournament data invariants, inline JavaScript syntax when Node.js is available, and source/bundled-app drift.

## Done Criteria

- Interactive work: the browser state proves the requested prediction, score, or share flow.
- Live-result work: the response names the source, fetch time, and completed-match count.
- Update-check work: the response names local version/commit, remote version/commit, dirty state, and upgrade commands.
- Code/data work: root `index.html` and bundled asset are in sync, targeted tests pass, and validator output is reported.
- Review work: findings lead, with file/line references and severity; include test gaps when no code is changed.
