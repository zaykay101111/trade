# Training protocol

## Actual first architecture

Canonical records → time-aware features → market reference → trained predictor → calibration → price threshold → capped paper stakes → evaluation report.

The market reference de-vigs each same-book pair: q_home=(1/d_home)/(1/d_home+1/d_away), then takes the median home probability across at least three eligible reference books. Model input excludes execution-book prices. Those prices enter selection afterward.

The twelve features are differences in recent margin, points scored and conceded, rest; home/away back-to-back flags; history counts; recent win rates; market disagreement and age. Features use at most ten previous games with results available before the prediction cutoff and require five prior games per team. Rest is elapsed days capped at 14; the back-to-back proxy is less than 1.5 days. These are declared simple proxies, not possession-adjusted efficiency or calendar-perfect schedule labels.

The model is p=sigmoid(logit(q)+f(X)). XGBoost receives the market logit as base_margin at both fit and prediction. The official [base-margin documentation](https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html) explains this offset interface.

Four tree configurations are considered, with depth 2/3 and 100/250 trees, learning rate 0.03, regularization and a minimum leaf weight. No early stopping or auxiliary-loss search occurs on calibration/test data. A penalized offset logistic model is fitted as a simpler comparator.

Each comparator receives a separate sigmoid calibration transform p_cal=sigmoid(a+b logit(p)), with b positive. Calibration is fitted on its dedicated later slice. Evaluation calibration slopes/intercepts are diagnostic fits and never fed back into that evaluation's predictions.

## Dates and data roles

Default boundaries, all UTC and end-exclusive:
- Train: before July 1, 2023.
- Tune: July 1, 2023 through December 31, 2023.
- Calibrate: January 1 through June 30, 2024.
- Development validation: July 1, 2024 through June 30, 2025.
- Final test: July 1, 2025 through June 30, 2026.

Use earlier eligible seasons for training. These are starting boundaries. If a period has already influenced your design, it is development data, and a later untouched period must become the final test. Do not blindly call an already-examined season untouched.

The learner selects its tree configuration using tune log loss. It then refits that configuration on train+tune games whose outcomes were available before the fitting boundary. The calibrator uses the subsequent calibration slice. That entire bundle remains fixed through validation and test. This evaluates one frozen historical release, not a periodic retraining policy.

## Before training

1. Archive raw data and reconcile IDs.
2. Review config dates, available books, cutoff and policy.
3. Build a new versioned dataset and inspect audit.json/excluded.csv.
4. Expect thousands of real games. The code's 30-per-fit-slice minimum is only an execution guard, not a statistical adequacy threshold.
5. Record each configuration change in an experiment log before viewing its results.

The data build refuses invalid timestamps, incompatible cutoff arithmetic, duplicate events/results, unknown game IDs, result timestamps preceding games, invalid prices and overlapping reference/execution books. Missing/stale books or short team history produce exclusions with reason counts.

## Run commands

```bash
sports build --data data/normalized/nba-v1 --config configs/first_model.json --out data/processed/nba-v1
sports train --dataset data/processed/nba-v1 --config configs/first_model.json --out runs/nba-v1
sports evaluate --run runs/nba-v1 --dataset data/processed/nba-v1 --split validation
sports report --path runs/nba-v1/validation
```

Inspect progress.json while fitting. trials.json contains every declared trial and its tune loss curve. bundle.json includes selected parameters, calibration, data/code hashes, split counts and library versions. residual.json stores the tree model in the native format; the logistic parameters are plain JSON.

After reviewing validation and selecting the experiment:

```bash
sports freeze --run runs/nba-v1
sports evaluate --run runs/nba-v1 --dataset data/processed/nba-v1 --split test
sports report --path runs/nba-v1/test
```

The final-test command requires freeze.json, verifies hashes, and creates TEST_CONSUMED.json before computing predictions. It refuses repeated evaluation into the same destination. This is local discipline and tamper detection; it cannot prevent a user from copying data or deleting files. If a run fails after consuming the test, preserve the marker and logs for review.

## Metrics and proposed gates

Compare residual forecasts with both the raw market and separately calibrated market. The primary target is >=0.25% relative log-loss improvement against calibrated market, with a paired seven-day block-bootstrap 95% interval above zero. The report includes a 28-day block sensitivity interval when at least ten blocks exist. Intervals are null when too few blocks exist. Brier score and calibration should be directionally consistent.

An economic evidence flag means the flat-yield interval excludes zero under the paper assumptions. It is not a production approval. A 2–5% yield is a research target, not a promise; compare the market-only policy, delay observations, worse-price stress and concentration in top profits. Synthetic data cannot pass the evidence flags.

The fixed paper policy requires at least 2% EV after a two-point probability haircut and 0.5%-of-stake extra cost. Bookmaker margin is already in the price. It uses quarter cost-adjusted Kelly capped at 0.25% per game, 1% open stake and 1% daily new stake, rounded down to whole dollars. The haircut is an initial conservative assumption to validate in development.

Five-minute stress uses a later observation from the same selected book, retains the original forecast, and checks its price floor. Missing later snapshots mean unknown availability. The 1% worse-profit-odds stress changes b=d−1 to 0.99b and reruns policy admission/allocation; it is a distinct synthetic stress, not measured execution delay.

## After a successful historical experiment

A new release needs fresh training and calibration and future confirmation. Do not continuously refit on the final test or paper results. Start with quarterly release review as a planning choice; compare that retraining procedure in its own historical experiment before changing production timing.

Add injury/availability features only after archives and label timing are audited. Adding features changes the data schema and requires retraining. Multiple losses, neural networks, sport expansion and LLM agents remain separate experiments.

