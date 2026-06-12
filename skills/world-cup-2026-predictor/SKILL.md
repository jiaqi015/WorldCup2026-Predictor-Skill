---
name: world-cup-2026-predictor
description: Launch, use, validate, or maintain the interactive 2026 World Cup predictor; generate group-stage and knockout brackets, compare predictions with current ESPN results, inspect scoring, and update teams, squads, mappings, or simulation logic. Use for 2026 World Cup prediction and live-score tasks, not unrelated football tournaments or betting advice.
---

# World Cup 2026 Predictor

Use the bundled single-file web app for interactive brackets and the bundled scripts for live-result checks and deterministic validation.

## Choose The Workflow

- For an interactive prediction, launch the web app and use browser automation when available.
- For current scores or completed-match counts, run the live-results script before answering.
- For code or data changes, read `references/predictor-model.md`, edit the canonical app, sync the bundled asset, then validate.
- For a quick health check, run the validator without launching a browser.

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
```

Always use a fresh result check when the user asks for current, latest, today, completed, or live tournament information. ESPN stage IDs and payload fields are external contracts; report a fetch or mapping failure instead of inventing a result.

## Maintain The App

Read `references/predictor-model.md` before changing teams, players, bracket mappings, scoring, or ESPN parsing.

When working in this source repository:

1. Edit the root `index.html`; it is the canonical GitHub Pages app.
2. Run `python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py`.
3. Run the validator.
4. Launch the app and browser-test the changed user flow.

When the skill is installed standalone and no repository root exists, edit `assets/predictor/index.html` directly.

Do not add copyrighted music. The app intentionally works without bundled audio.

## Validate

Run from the skill directory:

```bash
python3 scripts/validate_predictor.py
```

In the source repository, also run:

```bash
python3 scripts/release_check.py
git diff --check
```

The validator checks skill structure, tournament data invariants, inline JavaScript syntax when Node.js is available, and source/bundled-app drift.
