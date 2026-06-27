# Contributing

Thanks for helping improve the 2026 World Cup Predictor. This project is most useful when the browser app, data snapshots, and Codex skill stay aligned.

## Good Contributions

- Fixture, venue, kickoff-time, or bracket-placement corrections with a source link.
- ESPN result, scorer, assist, or team-name mapping fixes.
- UI fixes that make the bracket, match cards, scorer picker, or share flow easier to use.
- Prediction-model improvements that include a benchmark or regression test.
- Translation fixes for Chinese or English copy.
- Codex skill playbook improvements that make install, launch, scoring, or maintenance clearer.

## Before Opening A Pull Request

Run the focused checks for your change:

```bash
python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py
python3 skills/world-cup-2026-predictor/scripts/validate_predictor.py
python3 scripts/audit_source_lineage.py
python3 scripts/test_skill_product_ux.py
git diff --check
```

For broader app, data, or release changes, run:

```bash
python3 scripts/release_check.py
```

If you changed visible browser behavior, also open the app locally and verify the flow:

```bash
node scripts/serve_local.mjs --host 127.0.0.1 --port 8765
```

Then open `http://localhost:8765`.

## Source Boundaries

- Edit root `index.html` for app behavior.
- Treat `skills/world-cup-2026-predictor/assets/predictor/index.html` as a synced copy.
- Do not edit generated embedded data by hand unless the generating source is also updated.
- Do not add copyrighted music or broadcast footage.
- Keep betting language out of user-facing copy. Odds in this repo are prediction calibration context, not betting advice.

## Useful Issue Details

When reporting a bug, include:

- Browser and device.
- The mode you used: Standard, Fun, or Upset.
- The prediction model: Random baseline, Strength model, or Ensemble model.
- The fixture/team/player involved.
- A screenshot or share link when possible.
- The source link for any real-world data correction.

