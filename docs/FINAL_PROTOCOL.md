# Frozen final-evaluation protocol (odds-free NBA home-win probabilities)

Status: DRAFT SPECIFICATION. Nothing here has been executed. The 2025-26 final
holdout remains unscored. This document must be reviewed, approved and frozen
BEFORE any code reads holdout labels. It is a pre-registration of one single
evaluation, not another tuning round.

This protocol covers only forecast quality without odds. It cannot demonstrate
a betting edge, ROI, stake sizing, or that any price was executable.

## 0. Provenance at drafting time

- Dataset: `data/normalized/nba-v3` (7,230 games; 6,000 development, 1,230 holdout).
  - `games.csv` sha256 `32d3037da5088ea9a726a2fc561b7fcb8a2230bef3007742f3602449df691d73`
  - `results.csv` sha256 `62e88041b0d981f0bb1307144fd6a0dcf616a4fefae8b3f2ed36997b088e97e2`
  - Six reviewed neutral-venue overrides vs nba-v2; all six fall in development
    seasons. The holdout contains 5 provider-flagged neutral games, unmodified.
- Current source hash (`io.code_hash()`): `a3d061cdb5ad6627333ff91b1c1e442ed95b2830c45a87623460e36a96587cd6`.
  `runs/free-venue-v1`, `free-robustness-venue-v1` and `free-ablation-venue-v1`
  were produced under `76d49b2b1403d46e4bbc9df79f72aa62376c587935af538dd3fd36f86aee49b3`
  (before the `fit_logistic` `l2` keyword and `free_regularize.py` existed).
  `runs/free-regularization-v1` matches the current hash. The freeze record must
  store the hash at freeze time; earlier reports are not re-derivable from it.
- The project is not under version control. Hashes are the only provenance.
  Recommended before freezing: `git init` and an initial commit, so the frozen
  code hash maps to a recoverable tree.

## 1. Frozen candidate

Primary candidate (one, fixed, no alternatives scored as primary):

- Model: regularized logistic regression on all eleven features.
- Features, exact order (`free_data.FEATURES`): margin_diff, scored_diff,
  allowed_diff, win_rate_diff, history_count_diff, home_rest, away_rest,
  home_b2b, away_b2b, elo_diff, neutral.
- Objective: mean binary log loss + lambda * sum of squared standardized slopes,
  intercept unpenalized, offset q = 0.5. lambda = 0.01, FIXED.
  Rationale: `runs/free-regularization-v1` did not demonstrate improvement from
  chronological penalty selection (pooled calibrated log loss 0.621258 fixed vs
  0.622063 selected). The baseline is retained, not re-tuned.
- Standardization: mean/scale fitted on the refit rows only (section 2).
- Calibration: single sigmoid (intercept + exp-parameterized slope, L2 0.001)
  fitted on the calibration period only. Both raw and calibrated holdout metrics
  are reported; the calibrated model is the primary.
- Feature engineering, unchanged and frozen:
  - Rolling window 20 settled games; cold start = zero scoring averages, win rate 0.5.
  - Elo: init 1500, K=20, scale 400, home advantage 65 when not neutral, no season reset.
  - Rest: days since that team's previous scheduled start, capped at 14; b2b = rest < 1.5.
  - Prior results revealed strictly before each decision cutoff, in availability order.
- Explicitly NOT changed based on inspected validation: no feature is removed.
  The pooled ablation showed removing `neutral` slightly improved pooled log loss
  (-0.000713) with inconclusive per-season evidence and scarce neutral examples;
  that is not sufficient to alter the frozen candidate, and no combined-removal
  variant was ever evaluated.

Comparators (reported alongside, never promoted to primary):

- `home_rate`: constant equal to the home-win rate of the refit rows.
- `elo`: fixed Elo probability at each decision cutoff, uncalibrated, same parameters.
- `boosted` (secondary, pre-declared): XGBoost over the same four predeclared
  candidates (depth 2/3 x 100/250 trees, lr .03, reg_lambda 10, min_child_weight 20,
  seed 42), selected by raw log loss on the final tune period, refit on train+tune,
  sigmoid-calibrated on the calibration period. Included because it has been part
  of every development report; its holdout result is secondary, not the headline.

## 2. Final fitting chronology

All boundaries exclusive, UTC. This is exactly the shape of the three development
folds (`free_validate.fold_boundaries(Y)` with Y = 2025), so no new degrees of
freedom are introduced for the final fit.

| Stage | decision_at window | Label availability requirement |
|---|---|---|
| Train | 2020-07-01 -> 2024-07-01 | available_at < 2024-07-01 |
| Tune | 2024-07-01 -> 2025-01-01 | available_at < 2025-01-01 |
| Refit (train + tune) | 2020-07-01 -> 2025-01-01 | available_at < 2025-01-01 |
| Calibration | 2025-01-01 -> 2025-07-01 | available_at < 2025-07-01 |
| Final holdout | 2025-07-01 -> 2026-07-01 | no availability filter; labels used only for scoring |

Rules:

- Rows whose labels had not arrived by the end of their own stage are excluded
  from fitting, exactly as `free_train.partition` does today. The excluded count
  is reported.
- The tune period exists to select the boosted candidate. The primary logistic
  candidate has no tuned hyperparameter; train+tune is simply its refit set.
- No refitting, recalibration, feature rebuilding or model selection occurs at
  or after 2025-07-01. One fit, one calibration, one scoring pass.
- Features for holdout rows MUST be built over the full dataset in one pass, so
  Elo and rolling history continue to update inside the holdout as prior results
  become available. That is sequential forecasting, not leakage: each row sees
  only results with available_at strictly before its own decision_at. The current
  `fit_free` drops holdout rows before building features, so a separate code path
  is required (section 5).
- Holdout labels are never used for standardization, coefficients, calibration,
  candidate selection, or any threshold.

## 3. Metrics and interpretation, fixed before running

Primary (one comparison, declared in advance):

- Calibrated logistic mean log loss on the 1,230 holdout games.
- Paired log-loss difference, calibrated logistic minus Elo, with a 95% paired
  seven-day block bootstrap interval (1,000 resamples, seed 42) as implemented in
  `free_train.paired_interval`. Negative favors the logistic model.

Secondary, pre-specified:

- Logistic minus home-rate paired difference and interval.
- Brier score and accuracy for all four model families.
- Calibration diagnostic: sigmoid intercept/slope fitted to holdout predictions,
  reported only as a diagnostic and never applied to the scored predictions.
- Ten-bin reliability table with counts for each family.
- Raw (uncalibrated) logistic and boosted metrics alongside calibrated ones.
- Boosted vs Elo paired difference and interval.

Exploratory, produced in the same single run, not multiplicity-corrected:

- Monthly log loss.
- Neutral-site subset (expected n = 5; too small for inference, reported for completeness).
- Extra result-availability delays of 24h and 48h. These refit and recalibrate
  under the delayed regime and score the same holdout games; they are a delayed-data
  deployment diagnostic, not additional evidence about the primary candidate.

Interpretation rules agreed in advance:

- Intervals are conditional on the fitted models. They exclude training and
  model-selection uncertainty and are not corrected for the many development
  experiments already performed.
- Only the primary comparison is confirmatory. Everything else is descriptive.
- No accuracy, log-loss or interval outcome constitutes evidence of a market edge,
  and no result is to be described as one. A poor holdout result is not a reason
  to re-tune and re-score: the holdout is spent either way.
- Pre-committed reading: if the primary interval excludes zero in favor of the
  logistic model, the honest claim is "on one previously untouched NBA season,
  this feature set beat a fixed Elo baseline on log loss". If it includes zero,
  the honest claim is "no confirmed improvement over Elo on unseen data".

## 4. What the holdout can and cannot support

- It is a single season, one league, sequentially dependent, with reconstructed
  schedule-observation timestamps and an assumed +24h result availability.
- It confirms nothing about revised start times, delayed games, temporary home
  venues, injuries, or referee effects, none of which are modeled.
- It is a one-use resource. After scoring, 2025-26 becomes development data and
  cannot honestly back any later claim of a fresh holdout.

## 5. Artifacts and freezing

Freeze step (before any holdout access), writing `freeze.json` into a NEW run
directory:

- Candidate specification: model family, feature list and order, lambda, offset,
  Elo parameters, rolling window, rest cap, b2b threshold, calibration method.
- Boundaries table from section 2, verbatim.
- Comparator specification including the boosted grid and selection rule.
- Metric plan from section 3, including which comparison is primary.
- `data_sha256` for `games.csv`, `results.csv` and `manifest.json` of the dataset.
- `code_sha256` from `io.code_hash()`, python version and numpy / pandas / scipy /
  scikit-learn / xgboost versions.
- Freeze timestamp and a statement that this is local tamper-evidence, not an
  independent preregistration service.

Evaluation step (one use only):

- Refuses to run unless `freeze.json` exists and its `code_sha256` and
  `data_sha256` still match the current tree and dataset.
- Writes `HOLDOUT_CONSUMED.json` with `open("x")` BEFORE reading any holdout
  label, so a crash still consumes the attempt.
- Refuses to run a second time in the same run directory, and refuses if the
  run directory already exists.
- Emits `holdout_predictions.csv` (game_id, decision_at, y, one probability column
  per family, raw and calibrated), `report.json`, `PASTE_BACK.md`, the fitted
  logistic coefficients/scaler/calibrators, the boosted model, the tune trials,
  and the full feature table for the fitted and scored rows.
- Existing `freeze` / `evaluate` commands belong to the odds-based pipeline and
  are NOT reused; they expect odds columns and a different bundle schema.

Required tests before the protocol is executed:

1. Holdout features are identical whether or not later holdout labels are perturbed
   (leakage test, same shape as `test_no_current_or_future_score_leakage`).
2. No fitting row has `available_at` at or after its own stage boundary.
3. Refit/calibration rows and holdout rows are disjoint and chronologically ordered.
4. Second evaluation attempt in the same run directory raises.
5. Evaluation raises if `code_sha256` or `data_sha256` drifted from the freeze record.
6. The existing development commands still refuse boundaries past 2025-07-01
   (the current guards must remain intact, not be relaxed).
7. Saved-model replay reproduces the recorded holdout predictions exactly.

## 6. Open decisions requiring sign-off before freezing

1. Confirm the final chronology in section 2 (train through 2024-07-01, tune to
   2025-01-01, calibrate 2025-01-01 to 2025-07-01). The alternative, refitting on
   everything through 2025-07-01 with a shorter calibration slice, would use more
   data but would no longer match the development folds.
2. Confirm boosted stays a secondary comparator rather than being dropped.
3. Confirm the delay diagnostics (24h / 48h) run inside the same one-use
   evaluation, or are omitted entirely.
4. Confirm whether the repository is placed under git before the freeze.

Nothing in this document is executed until items 1-4 are answered and the freeze
command is run deliberately.
