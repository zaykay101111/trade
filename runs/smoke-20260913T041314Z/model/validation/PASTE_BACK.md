# PASTE BACK — VALIDATION

Copy this entire file into the chat.

Status: synthetic; paper evaluation; no execution claim.

```json
{
  "schema_version": 1,
  "created_at": "2026-09-13T04:13:21.198856+00:00",
  "split": "validation",
  "mode": "synthetic",
  "run": "model",
  "dataset_sha256": "4f62ce10593893f0bbb31da9972fab3bf53aa59892312672f71c3a479f0418f8",
  "code_sha256": "cccf39217fbadd9474e79e53d0aad3b08f363c29734bb161c4fe0225e1f13bcc",
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
  "selected_probability_metrics": {
    "n": 112,
    "brier": 0.12405659692889315,
    "log_loss": 0.41604894178631185
  },
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
  "delayed_price_test": {
    "original_bets": 112,
    "same_book_later_snapshot_observed": 0,
    "still_clears_price_floor": 0,
    "flat_yield_if_taken_at_delayed_price": null,
    "qualification": "Missing later snapshots are unknown availability. Same contract/book; original forecasts fixed."
  },
  "data_audit": {
    "schema_version": 1,
    "mode": "synthetic",
    "games": 1200,
    "eligible": 1167,
    "excluded": 33,
    "exclusion_reasons": {
      "insufficient_prior_games": 33
    },
    "features": [
      "margin_diff",
      "points_for_diff",
      "points_against_diff",
      "rest_diff",
      "home_back_to_back",
      "away_back_to_back",
      "home_history",
      "away_history",
      "home_win_rate",
      "away_win_rate",
      "reference_dispersion",
      "reference_age_minutes"
    ],
    "input_hashes": {
      "games": "1ca950616e854c2889fbb7e45c256f7e60881447000900441600ecdbb8ab0304",
      "results": "f026a8de36c73c736c3c1da8824dc6755bdc97fcd65d010ac9f7b1fa1a0a83ab",
      "odds": "d80f26326b3f33c24b3f9fb653e98040a25c8c4901bf0b204f8a270ae08d5008"
    },
    "features_sha256": "4f62ce10593893f0bbb31da9972fab3bf53aa59892312672f71c3a479f0418f8",
    "config": {
      "schema_version": 1,
      "mode": "synthetic",
      "cutoff_minutes": 60,
      "max_quote_age_minutes": 10,
      "min_reference_books": 3,
      "reference_books": [
        "pinnacle",
        "betfair_ex_eu",
        "williamhill"
      ],
      "execution_books": [
        "draftkings",
        "fanduel"
      ],
      "contract": "nba_regular_fullgame_moneyline_ot",
      "rolling_games": 10,
      "min_history": 5,
      "train_end": "2021-04-25T20:00:00+00:00",
      "tune_end": "2021-10-22T20:00:00+00:00",
      "calibration_end": "2022-04-20T20:00:00+00:00",
      "validation_end": "2022-10-17T20:00:00+00:00",
      "test_end": "2023-04-15T20:00:00+00:00",
      "seed": 42,
      "threads": 4,
      "bootstrap_repeats": 200,
      "block_days": 7,
      "policy": {
        "bankroll": 10000,
        "cost_per_stake": 0.005,
        "min_ev": 0.02,
        "probability_haircut": 0.02,
        "kelly_fraction": 0.25,
        "max_game_fraction": 0.0025,
        "max_open_fraction": 0.01,
        "max_daily_fraction": 0.01,
        "stake_increment": 1
      },
      "grid": [
        {
          "max_depth": 2,
          "n_estimators": 30,
          "learning_rate": 0.05
        },
        {
          "max_depth": 3,
          "n_estimators": 30,
          "learning_rate": 0.05
        }
      ]
    },
    "lineage_limit": "Timestamp assertions validate declared availability; archive provenance must be audited separately."
  },
  "limitations": [
    "Synthetic mode never provides market evidence",
    "Haircut is a fixed policy stress, not a confidence bound",
    "Calibration diagnostic is fitted on this evaluation slice for diagnosis only, never used to change forecasts",
    "Reported bootstrap intervals do not correct an undisclosed strategy search"
  ],
  "versions": {
    "python": "3.12.14",
    "numpy": "2.2.6",
    "pandas": "2.3.3",
    "scipy": "1.18.1",
    "sklearn": "1.9.1",
    "xgboost": "3.4.1"
  }
}
```
