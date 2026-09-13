# PASTE BACK — VALIDATION

Copy this entire file into the chat.

Status: synthetic; paper evaluation; no execution claim.

```json
{
  "schema_version": 1,
  "created_at": "2026-09-13T01:40:34.826352+00:00",
  "split": "validation",
  "mode": "synthetic",
  "run": "model",
  "dataset_sha256": "7ebfd3922ea87aa8f6e4f8507f391fb3cb186ccd4c622077f8e4f9e23f23903c",
  "code_sha256": "27a6b314c6f38dd2757b63e644b03cdfa261b4aeb3b1f79556f42f16b7a6fc69",
  "n_games": 180,
  "start": "2022-04-21T19:00:00+00:00",
  "end": "2022-10-17T19:00:00+00:00",
  "metrics": {
    "market": {
      "log_loss": 0.46540590720827246,
      "brier": 0.14880787982402566,
      "calibration_diagnostic": {
        "intercept": -0.2204441468656153,
        "slope": 1.5008274504293613
      }
    },
    "market_cal": {
      "log_loss": 0.4875767916216726,
      "brier": 0.1566975215326662,
      "calibration_diagnostic": {
        "intercept": -0.36319172963537805,
        "slope": 1.849056554675064
      }
    },
    "logistic": {
      "log_loss": 0.49313323446712254,
      "brier": 0.15834751182792486,
      "calibration_diagnostic": {
        "intercept": -0.37955611922861454,
        "slope": 1.8656256867352823
      }
    },
    "residual": {
      "log_loss": 0.4962210382614894,
      "brier": 0.16021687920549865,
      "calibration_diagnostic": {
        "intercept": -0.3753315456485613,
        "slope": 1.8771256781269336
      }
    }
  },
  "relative_log_loss_improvement": -0.017728995285165732,
  "paired_log_loss_improvement_ci95": [
    -0.014676986781902815,
    -0.002772428396501948
  ],
  "paired_ci95_28day_sensitivity": null,
  "reliability_bins": [
    {
      "lower": 0.1,
      "n": 10,
      "mean_p": 0.16867140130833508,
      "observed": 0.0
    },
    {
      "lower": 0.2,
      "n": 24,
      "mean_p": 0.2725536271961038,
      "observed": 0.125
    },
    {
      "lower": 0.3,
      "n": 26,
      "mean_p": 0.35935959665744066,
      "observed": 0.19230769230769232
    },
    {
      "lower": 0.4,
      "n": 27,
      "mean_p": 0.44851091006328025,
      "observed": 0.25925925925925924
    },
    {
      "lower": 0.5,
      "n": 17,
      "mean_p": 0.5598105079068566,
      "observed": 0.5882352941176471
    },
    {
      "lower": 0.6,
      "n": 23,
      "mean_p": 0.647698386583019,
      "observed": 0.6521739130434783
    },
    {
      "lower": 0.7,
      "n": 27,
      "mean_p": 0.7506569693424502,
      "observed": 0.8888888888888888
    },
    {
      "lower": 0.8,
      "n": 26,
      "mean_p": 0.8511381193029643,
      "observed": 0.9230769230769231
    }
  ],
  "paper_policy": {
    "bets": 112,
    "turnover": 2513,
    "pnl": -1458.7027924355043,
    "flat_yield": -0.5283489384675525,
    "weighted_yield": -0.580462710877638,
    "bankroll_return": -0.14587027924355042,
    "max_drawdown": 0.15453353558363936
  },
  "market_only_policy": {
    "bets": 109,
    "turnover": 2517,
    "pnl": -1188.2082850935458,
    "flat_yield": -0.4630099835487186,
    "weighted_yield": -0.47207321616747944,
    "bankroll_return": -0.11882082850935458,
    "max_drawdown": 0.12775844168292472
  },
  "flat_yield_ci95": [
    -0.7708692989641159,
    -0.2660668421177981
  ],
  "profit_odds_1pct_worse": {
    "bets": 111,
    "turnover": 2472,
    "pnl": -1475.7727453719654,
    "flat_yield": -0.6119487745661297,
    "weighted_yield": -0.5969954471569439,
    "bankroll_return": -0.14757727453719655,
    "max_drawdown": 0.1561375215948516
  },
  "outlier_sensitivity": {
    "remove_top_5_profit_bets_pnl": -1994.0881181123113,
    "remaining_bets": 107
  },
  "gate_forecast": false,
  "gate_economic_evidence": false,
  "execution_evidence": "NOT MEASURED: displayed historical quotes; paper stakes only",
  "delayed_price_test": "NOT MEASURED: use prospective checks.csv or add archived execution-time quotes",
  "limitations": [
    "Synthetic mode never provides market evidence",
    "Haircut is a fixed policy stress, not a confidence bound",
    "Calibration diagnostic is fitted on this evaluation slice for diagnosis only, never used to change forecasts",
    "Reported bootstrap intervals do not correct an undisclosed strategy search"
  ],
  "versions": {
    "python": "3.12.14",
    "numpy": "2.5.3",
    "pandas": "2.3.3",
    "scipy": "1.18.1",
    "sklearn": "1.9.1",
    "xgboost": "3.4.1"
  }
}
```
