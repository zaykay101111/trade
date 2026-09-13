# Offline statistics-only training

No API keys, network requests, new dependencies, or odds are required.
This track is separate from `build`, `train`, and betting-policy commands.
Do not pass an odds-free bundle to the market-based or paper commands.

```bash
source .venv/bin/activate
python -m pytest -q
sports train-free --data data/normalized/nba-v2 --out runs/free-v1 --threads 2
sports report --path runs/free-v1 | pbcopy
```

Output directories cannot be overwritten. Choose `runs/free-v2` for a later
experiment and retain earlier reports to track all attempts.

## Fixed protocol

- Training: 2020-07-01 through 2023-06-30 UTC.
- Tree tuning: 2023-07-01 through 2023-12-31.
- Refit selected tree and logistic model on training plus tuning data.
- Sigmoid calibration of logistic and boosted models: 2024-01-01 through 2024-06-30.
- Development validation: 2024-07-01 through 2025-06-30.
- Games from 2025-07-01 onward remain unscored. This command intentionally does
  not provide a final-test override; agree on and freeze the final protocol first.

Four model families: a training-derived constant home-win rate, fixed Elo,
regularized logistic regression, and boosted trees. Tree search is only four
predeclared candidates (depth 2/3, 100/250 trees), selected by tuning log loss.
Calibration is not fitted on validation. Raw and calibrated challenger metrics
are both reported. Logistic regularization and Elo parameters are fixed, not tuned.

Features: 20-settled-game scoring margin, points for/against, win rates, history
counts, capped rest, back-to-backs, Elo difference and neutral court flag. No
possession-adjusted ratings, injury information, referee data or odds are used.
Elo starts at 1500, uses K=20, scale=400, home advantage=65, with no season reset.
Elo and rolling team state update during validation only when a previous result
becomes available. This is sequential forecasting, not fitting on future labels.
Rest uses previous scheduled starts. Cold-start score averages are zero and win
rates 0.5; no games are dropped solely for short history.

The importer assumes result availability 24h after scheduled start. The schedule
observation timestamps are reconstructed. These are research assumptions, not
verified historical revisions. Postponed/delayed games and timing revisions need
an audit before any claims of deployable betting performance.

## Reading the report

Lower log loss and Brier score are better. Accuracy is secondary. Compare both
challengers to home-rate and Elo; inspect calibration-bin counts and monthly
stability. Negative paired log-loss differences favor the challenger. The 95%
interval resamples seven-day blocks; it does not include model-selection or
training uncertainty, and does not correct for trying many experiments. Monthly
results are diagnostics, not independent validation folds. Additional rolling
origin folds should be added before declaring a robust forecasting improvement.

Artifacts: model JSON, logistic coefficients/scaler/calibrators, four tuning
trials, source/code hashes, dependency versions, development features, validation
predictions, full JSON metrics, and `PASTE_BACK.md` readable with `sports report`.
Repeated validation tuning can overfit. No win-rate target, ROI, stakes or claim
of market edge is produced. A market edge requires timestamped executable odds.

## Rolling-season and delayed-result checks

```bash
sports validate-free --data data/normalized/nba-v2 --out runs/free-robustness-v1 --threads 2
sports report --path runs/free-robustness-v1 | pbcopy
```

Nine full training runs: validation seasons 2022-23, 2023-24, 2024-25, each
with an extra 0, 24, or 48 hours added to result availability. With the current
importer's +24h assumption these correspond to total +24h, +48h, and +72h.
For validation season starting in year Y, train through July 1 of Y-1,
tune through January 1 of Y, calibrate through July 1 of Y, then validate
through July 1 of Y+1. All upper boundaries are exclusive UTC. Training
expands from July 2020; each fold's tree selection uses only its own tuning
period. No scenario uses 2025-26 for fitting, calibration or scoring.

Every delay scenario rebuilds history/Elo and refits the same predefined model
families, including tree selection and calibration. This tests a delayed-data
training/deployment regime, not an unexpected outage of a frozen model. It does
not test revised start times or historical injury information. Compare the
matched scenario log losses, probability changes and calibration bins; delay
need not monotonically hurt performance because fitting also changes.

Validation IDs must match between delay scenarios and cannot overlap between
seasons. Earlier validation seasons can enter later training, as they would in
a chronological deployment. Therefore folds are not independent replications.
2024-25 has already been inspected, and the system design was informed by it;
this is development robustness evidence, not a new untouched confirmation.
The report gives per-fold paired weekly-block intervals and descriptive pooled
metrics, with no automatic promotion or multiple-testing-adjusted claim.

Each child directory preserves full features, validation predictions, model
parameters, source hashes, calibration bins and split counts. The parent report
summarizes the nine runs; progress.json records completed runs. Choose a new
output directory to retry an interrupted run; no prior runs are overwritten.

## Feature-ablation checks

```bash
sports ablate-free --data data/normalized/nba-v2 --out runs/free-ablation-v1
sports report --path runs/free-ablation-v1
```

Twenty-one logistic fits: full features plus six leave-one-group-out variants,
across the same 2022-23, 2023-24 and 2024-25 development folds. Groups are scoring
(margin/points for/points against together), recent win rate, history count,
rest/back-to-backs, Elo difference, and the direct neutral-court flag. Margin is
exactly points-for minus points-against, so removing only one scoring column
would leave redundant information. Removing neutral does not erase venue effects
already encoded in historical Elo updates. Group removal is conditional on the
remaining inputs, not a causal attribution or an independent information test.

Each variant refits its scaler, logistic coefficients and sigmoid calibrator;
regularization, calibration protocol and data timing remain fixed. Both raw and
calibrated metrics are saved. This is baseline imported availability (+24h), not
the additional-delay grid. All validation rows match across variants; the final
holdout remains unscored. No feature subset is automatically promoted and the
existing training commands remain unchanged.

Positive ablated-minus-full log-loss differences favor keeping a group. Inspect
consistency across seasons, Brier score, raw versus calibrated changes, and
constant-feature diagnostics. Weekly-block intervals are descriptive, omit
training/selection uncertainty, and are not multiple-testing corrected. An
interval containing zero does not prove a feature is useless. These are already
inspected development folds, not independent confirmatory evidence. Combining
several individually harmless removals can still hurt; this command does not
evaluate combined removals. Each child saves the refitted model and predictions.

## Reviewed venue corrections (nba-v3)

Use `data/normalized/nba-v3` for subsequent experiments. It changes only six
`is_neutral` cells from nba-v2; scores, timestamps and final-holdout rows are
unchanged. Raw caches remain verbatim. The new manifest records per-game source
URLs, old/new values, cached venues, and input/output hashes. Reproduce with:

```bash
sports correct-venues --data data/normalized/nba-v2 --out data/normalized/nba-v3
```

The six reviewed game IDs are 0022200439, 0022200678, 0022300172, 0022301229,
0022301230 and 0022300527 (Mexico City, Paris and Las Vegas). Sources establish
location; neutral classification is our modeling convention consistent with
the later provider flags, not a measured assertion of zero home advantage.
Austin regional home games and temporary home bases are not automatically
neutral merely because their city differs from the franchise name. This is a
targeted correction, not an exhaustive home-advantage or venue audit.

The generic schedule downloader remains a raw provider mapping. Its output must
still be audited; these historical overrides are explicit, not silently applied
to future data. All older runs are retained for provenance, not overwritten.

## Chronological regularization check

```bash
sports regularize-free --data data/normalized/nba-v3 --out runs/free-regularization-v1
sports report --path runs/free-regularization-v1
```

For each of the existing three development folds, fit four logistic candidates
with lambda 0.001, 0.01, 0.1 and 1.0. Minimize raw log loss on that fold's tuning
period, then refit on train+tune and calibrate on its separate calibration period.
Compare with the existing fixed 0.01 model on identical next-season validation
games. The objective is mean binary log loss plus lambda times the sum of squared
standardized slopes; the intercept is unpenalized. Higher lambda means stronger
shrinkage; these are not sklearn C values. Scaling is always fitted on the
appropriate training rows. Exact tuning ties prefer the larger penalty.

No features are removed, availability is unchanged, and no final-holdout metrics
are computed. Calibration can partially undo shrinkage, so both raw and calibrated
metrics are reported. Trial scores, selected penalties, refit models/calibrators,
data/code hashes and validation predictions are saved. Existing training defaults
remain 0.01; this experiment does not automatically promote a tuned model.

This is a small development comparison informed by previous experiments, not
independent evidence of improvement. Paired weekly-block intervals exclude
training/selection uncertainty and multiplicity. Do not expand the grid because
a validation result is disappointing or assume global shrinkage specifically
solves sparse neutral-site estimation. Neutral counts are reported for context.

## Final-holdout freeze and one-use evaluation

The 2025-26 season is scored exactly once, against a protocol frozen first.
Full specification and the decisions behind it: `docs/FINAL_PROTOCOL.md`.

```bash
sports freeze-final --data data/normalized/nba-v3 --out runs/final-v1
sports evaluate-final --run runs/final-v1 --dry-run --threads 2
sports evaluate-final --run runs/final-v1 --yes-consume-final-holdout --threads 2
sports report --path runs/final-v1/holdout
```

`freeze-final` writes only `freeze.json`: candidate specification, boundaries,
metric plan, data and code hashes, dependency versions. It computes no
prediction and no metric. `evaluate-final --dry-run` fits the whole pipeline and
writes holdout predictions with no outcomes read and no metrics computed, so a
failure costs nothing. The scored run refuses without the explicit flag, refuses
on any code or data drift from the freeze record, claims `HOLDOUT_CONSUMED.json`
before reading a single label, and cannot be repeated in the same run directory.

The frozen candidate is the full-feature logistic model at lambda 0.01 with
sigmoid calibration; home-rate and Elo are comparators and boosted trees are a
declared secondary. Training runs through 2024-07-01, tree tuning through
2025-01-01, refit on train plus tune, calibration 2025-01-01 to 2025-07-01 —
the same shape as the three rolling development folds. Extra availability delays
of 24h and 48h are exploratory and run inside the same single evaluation.

One confirmatory comparison is declared in advance: calibrated logistic minus
Elo paired log-loss difference with a weekly-block interval. Everything else is
secondary or exploratory. Nothing produced here is evidence of a betting edge;
that still requires timestamped, executable multi-book prices at the prediction
cutoff, which this project does not have.
