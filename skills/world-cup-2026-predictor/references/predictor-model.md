# Predictor Model

## Canonical Files

- Source repository app: `index.html`
- Installed skill app: `assets/predictor/index.html`
- Sync command: `python3 scripts/sync_predictor_asset.py`

Edit the repository app first when it exists. The validator fails if the bundled copy drifts from it.

## Core Data

The app is intentionally a single HTML file. Search these JavaScript variables before changing data:

- `GD`: 12 groups with 4 teams each.
- `PL`: 11-player simulation roster for every team.
- `POS`: team-scoped player positions.
- `FC`: FlagCDN country codes.
- `TEAM_EN`: English display names and the base ESPN name map.
- `STRENGTH`: simulation strength tiers.
- `R32D`, `R16P`, `QFP`, `SFP`: knockout topology.

The current and proposed entity boundaries are documented in
`docs/domain-model.md`. The machine-readable catalog is
`data/schema/prediction-domain.v1.json`.

Preserve these invariants:

- 12 groups, 48 unique teams, 72 group matches.
- 16 round-of-32 matches and 104 tournament matches overall.
- Exactly 11 simulation players per team.
- Every team has flag, English-name, roster, and position mappings.
- A knockout match cannot finish level.

## Runtime State

- `gm`: group predictions.
- `ko`: knockout predictions.
- `slog`: scorer and assist events.
- `predictionMode`: random baseline, consolidated strength model, or
  uncertainty-calibrated ensemble model. Legacy `odds` and `worldRanking`
  values migrate to `strength`; `aiReasoning` migrates to `ensemble`.
- `playMode`: normal, clone, or chaos presentation/gameplay modifier.

Keep the UI compatibility map intact: Normal offers strength and ensemble, Fun
also allows the random baseline, and Upset locks prediction to random.
- `ACTUAL_RESULTS`: normalized completed results used for scoring.
- `localStorage`: prediction, display, history, and live-result cache.
- URL hash `#p=`: compact shared-prediction payload.

Changing state shapes requires backward-compatible loading or an explicit version migration.

## Research Evidence

The Kimi report corpus is stored under
`data/rag/kimi-world-cup-report/`. Retrieve from `chunks.jsonl`, preserve the
page citation, and treat report-derived quantitative claims as source
assertions until independently verified.

Use `python3 scripts/search_report_rag.py "<query>"` for a local retrieval smoke
test. For production RAG, embed the chunk `text` and retain chapter, section,
keywords, content type, citation, and source hash as metadata.

## Live Results

`RESULTS_API` queries ESPN's public World Cup scoreboard feed for June 11 through July 19, 2026.

`ESPN_STAGE` maps external `season.type` values to the app's round prefixes. `ensureEN2CN()` handles display-name differences such as:

- `Bosnia-Herzegovina`
- `United States`
- `Ivory Coast`
- `Congo DR`

Treat stage IDs, team spellings, CORS behavior, and payload shape as unstable external data. Re-fetch and inspect the current payload before changing mappings.

The scorer compares:

- Group results by fixed fixture slot.
- Knockout progress by the set of teams reaching each round.
- Champion, runner-up, and third place exactly.

## Verification

After any behavior change:

1. Run `scripts/sync_predictor_asset.py`.
2. Run `scripts/validate_predictor.py`.
3. Run the repository release check, including model and squad tests.
4. Serve the app locally.
5. Exercise every prediction model at least once.
6. Complete group and knockout randomization.
7. Confirm the champion and Share button.
8. Check browser console errors.

For live-result changes, also verify at least one completed event from the current ESPN payload maps into `ACTUAL_RESULTS`.
