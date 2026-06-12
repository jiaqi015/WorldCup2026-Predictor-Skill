# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.1] - 2026-06-13

### Changed

- Moved each group-stage 1X2 decimal odd directly onto its matching Home, Draw,
  or Away quick-action button.
- Kept model-derived provenance and totals metadata visible without repeating
  the three decimal values in a separate row.
- Added responsive two-line outcome-button styling for Chinese and English.

### Validation

- Added an integration regression test for all three outcome-button odds.
- Verified the priced quick action still writes a valid result in the browser.
- Verified the dark desktop layout, English labels, and browser console.

## [0.3.0] - 2026-06-12

### Added

- Complete 104-match ESPN schedule metadata with local-time, venue, status, and
  completed-result integration.
- Explicitly sourced prediction snapshots for FIFA ranking, observed or
  estimated Elo, model-derived 1X2 completion, and player scoring/assist threat.
- Group-stage draw quick action and a progress-aware knockout bracket lock.
- Release validation for match coverage, source provenance, team identity, and
  prediction-data confidence.

### Changed

- Blank predictions now adopt completed ESPN results while preserving manually
  edited predictions.
- The odds display identifies model-derived 1X2 values instead of presenting
  them as directly observed sportsbook markets.
- Generated player headshots use the existing per-player SVG fallback rather
  than duplicated bitmap silhouettes.
- Match and prediction embedding scripts are idempotent.

### Fixed

- Removed Denmark from the 48-team strength snapshot and restored South Africa.
- Removed the invalid `JAM` to Jordan abbreviation mapping.
- Downgraded FIFA-rank-regressed Elo values to low confidence.

## [0.2.0] - 2026-06-12

### Added

- Four independently selectable prediction strategies: random baseline,
  calibrated strength odds, offline power ranking, and offline AI ensemble.
- Structured prediction results with probabilities, explanations, events,
  half-time scores, and card totals.
- Prediction-engine and application-wiring tests in the release gate.
- Reproducible 48-team, 1,248-player squad validation.
- ESPN public roster snapshots with local headshots or generated placeholders.
- Page-cited RAG corpus generated from the 205-page Kimi World Cup report.
- Expanded domain model for observations, features, model runs, evidence,
  uncertainty, calibration, and dynamic updates.
- Lightweight local report retrieval CLI and machine-readable entity catalog.

### Changed

- Calibrated knockout strength advantages to the documented probability curve.
- Separated prediction strategy from Normal, Fun, and Upset gameplay modes.
- Mapped Normal to the three strength models, Fun to every model, and Upset to
  the random baseline.
- Moved model controls into responsive page flow to prevent content overlap.
- Replaced champion trophy emoji with a consistent World Cup trophy SVG.
- Clarified editable simulated scores, poster sharing, and save-reset labels.
- Synchronized the canonical app and installable Skill asset.

## [0.1.1] - 2026-06-12

### Changed

- New visitors now see the predictor in Chinese by default.
- Existing visitors keep their saved language preference.

## [0.1.0] - 2026-06-12

### Added

- Installable `world-cup-2026-predictor` Codex Skill.
- Codex plugin manifest and GitHub marketplace distribution.
- Bundled interactive 48-team predictor and local launch command.
- Public demo deployment at `https://www.cameraclaw.cn/2026`.
- Live ESPN result lookup, structural validation, and asset synchronization.
- Automated release checks and GitHub Actions validation.
