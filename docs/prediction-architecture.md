# Prediction Architecture

This app is still shipped as a single HTML file, but the prediction core has an explicit, tested domain boundary in `PredictionEngine`.

For the expanded fact, observation, feature, forecasting, and feedback model,
see [`domain-model.md`](domain-model.md).

## Layers

- Domain entities: `Team`, `Player`, `Coach`, `Match`, and `Prediction`.
- Prediction application service: `simulateMatch`, `estimateOutcomeProbabilities`, and mode registry lookups.
- Prediction modes: pluggable strategies selected by `predictionMode`.
- Gameplay modes: UI-facing variants selected by the existing Normal / Fun / Upset controls.
- Presentation: group tables, knockout bracket, scorer picker, poster, and history remain in the page renderer.

## Domain Model

- `Team`: stable team identity, display name, strength tier, world ranking, confederation, coach, and players.
- `Player`: identity, name, position, team reference, and future attributes.
- `Coach`: identity, name, nationality, and tactical style placeholder.
- `Match`: identity, stage, home team, away team, venue, and scheduled time.
- `Prediction`: mode, gameplay mode, match id, outcome, scoreline, events, probabilities, and explanation trail.

The current legacy data tables (`GD`, `PL`, `POS`, `FC`, `TEAM_EN`, `STRENGTH`) remain canonical for the shipped single-file app. The entity constructors create the future extraction path without forcing a risky data migration in this pass.

## Prediction Modes

`PredictionEngine.PREDICTION_MODES` defines the extension points:

- `random`: pure random baseline that intentionally ignores team strength.
- `odds`: calibrated strength prior with optional external decimal odds.
- `worldRanking`: bundled offline power-ranking snapshot.
- `aiReasoning`: offline ensemble of strength, ranking, and uncertainty, with optional structured provider probabilities.

All modes return the same output contract:

- winner
- scoreline
- goals
- assists
- cards
- halfTimeScore

The result also includes normalized probabilities and an explanation trail. Goal events
are aggregate simulation events; the presentation layer continues to assign named
scorers and assists from the team roster.

## Odds Mode

The current offline `COMPLETE_ODDS` snapshot is not a claim that every match
has a directly observed three-way sportsbook market. ESPN sometimes exposes
only one team moneyline plus the draw. In those cases the missing side is
completed with the documented strength prior and stored as
`derived_from_partial`. The UI labels these values as model-derived, and the
prediction snapshot retains method, confidence, source type, and original
market text.

Completed matches have no reconstructed historical odds. Missing markets stay
missing and fall back to the strength model.

Odds mode accepts an optional decimal-odds market:

```js
{ home: 2.1, draw: 3.4, away: 3.8 }
```

The engine converts decimal odds to implied probabilities with `1 / odds`, normalizes overround, and samples the match outcome from that distribution.

When live odds are not available, odds mode falls back to a strength-derived synthetic market. This keeps the app deterministic in shape and ready for a future odds provider without blocking current offline use.

For knockout matches, `allowDraw:false` removes the draw bucket and normalizes home/away probabilities.

## Gameplay Mapping

The existing UI modes are not prediction modes. They are modifiers on top of the selected prediction strategy:

- `normal`: no probability modifier.
- `clone`: scorer selection can clone a team's star player.
- `chaos`: shifts probability mass toward the underdog.

The prediction-model selector and gameplay selector are persisted independently,
with a deliberate compatibility map:

- `normal`: strength odds, power ranking, or AI ensemble.
- `clone`: all four prediction strategies.
- `chaos`: random baseline only.

Changing gameplay mode automatically selects the first compatible strategy when
the previous selection is no longer valid.

## Provider Extension Points

Provider modules should adapt external data into the engine inputs instead of changing UI code:

- `OddsProvider`: fetch and normalize bookmaker odds by match.
- `RankingProvider`: fetch FIFA/world ranking snapshots.
- `AIReasoningProvider`: return structured probabilities with citations and explanation.
- `SquadProvider`: update teams, players, coaches, injuries, and cards-related priors.

The static app works without providers. A connected host can call providers at the
application-service boundary and pass normalized inputs into
`PredictionEngine.simulateMatch`.
