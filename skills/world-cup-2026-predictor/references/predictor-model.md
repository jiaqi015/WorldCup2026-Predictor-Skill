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
- `ACTUAL_RESULTS`: normalized completed results used for scoring.
- `localStorage`: prediction, display, history, and live-result cache.
- URL hash `#p=`: compact shared-prediction payload.

Changing state shapes requires backward-compatible loading or an explicit version migration.

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
3. Serve the app locally.
4. Complete group and knockout randomization.
5. Confirm the champion and Share button.
6. Check browser console errors.

For live-result changes, also verify at least one completed event from the current ESPN payload maps into `ACTUAL_RESULTS`.
