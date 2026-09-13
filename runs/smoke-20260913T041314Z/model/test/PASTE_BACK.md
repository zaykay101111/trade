# PASTE BACK — TEST

Copy this entire file into the chat.

Status: synthetic; paper evaluation; no execution claim.

```json
{
  "schema_version": 1,
  "created_at": "2026-09-13T04:13:22.748940+00:00",
  "split": "test",
  "mode": "synthetic",
  "run": "model",
  "dataset_sha256": "4f62ce10593893f0bbb31da9972fab3bf53aa59892312672f71c3a479f0418f8",
  "code_sha256": "cccf39217fbadd9474e79e53d0aad3b08f363c29734bb161c4fe0225e1f13bcc",
  "n_games": 179,
  "start": "2022-10-18T19:00:00+00:00",
  "end": "2023-04-14T19:00:00+00:00",
  "metrics": {
    "market": {
      "log_loss": 0.5863014073515509,
      "brier": 0.20036111369600432,
      "calibration_diagnostic": {
        "intercept": 0.1574321981170258,
        "slope": 0.8841490902531223
      }
    },
    "market_cal": {
      "log_loss": 0.5839357454728233,
      "brier": 0.19971889771853174,
      "calibration_diagnostic": {
        "intercept": 0.07296492898919299,
        "slope": 1.0887603401337798
      }
    },
    "logistic": {
      "log_loss": 0.581296346552577,
      "brier": 0.19888585827157707,
      "calibration_diagnostic": {
        "intercept": 0.04424588807744487,
        "slope": 1.1322476097525984
      }
    },
    "residual": {
      "log_loss": 0.5881979195093525,
      "brier": 0.20142386535312728,
      "calibration_diagnostic": {
        "intercept": 0.05243956020788953,
        "slope": 1.128501791175543
      }
    }
  },
  "relative_log_loss_improvement": -0.007299046289892781,
  "paired_log_loss_improvement_ci95": [
    -0.00980974859760705,
    0.0014080972677911203
  ],
  "paired_ci95_28day_sensitivity": null,
  "reliability_bins": [
    {
      "lower": 0.1,
      "n": 9,
      "mean_p": 0.16574053231400362,
      "observed": 0.1111111111111111
    },
    { b
      "lower": 0.2,
      "n": 11,
      "mean_p": 0.25630744383645837,
      "observed": 0.36363636363636365
    },
    {
      "lower": 0.3,
      "n": 27,
      "mean_p": 0.3488262366164129,
      "observed": 0.4074074074074074
    },
    {
      "lower": 0.4,
      "n": 31,
      "mean_p": 0.4497553496665583,
      "observed": 0.3548387096774194
    },
    {
      "lower": 0.5,
      "n": 23,
      "mean_p": 0.544401358516668,
      "observed": 0.5217391304347826
    },
    {
      "lower": 0.6,
      "n": 32,
      "mean_p": 0.6541229377386181,
      "observed": 0.6875
    },
    {
      "lower": 0.7,
      "n": 28,
      "mean_p": 0.7485450415243672,
      "observed": 0.8571428571428571
    },
    {
      "lower": 0.8,
      "n": 18,
      "mean_p": 0.8512059762985804,
      "observed": 0.8333333333333334
    }
  ],
  "paper_policy": {
    "bets": 121,
    "turnover": 2938,
    "pnl": 146.4801060512582,
    "flat_yield": 0.07668400653608852,
    "weighted_yield": 0.04985708170566991,
    "bankroll_return": 0.014648010605125819,
    "max_drawdown": 0.05436008900391398
  },
  "market_only_policy": {
    "bets": 96,
    "turnover": 2427,
    "pnl": 516.0565414474313,
    "flat_yield": 0.21838389105522962,
    "weighted_yield": 0.2126314550669268,
    "bankroll_return": 0.05160565414474313,
    "max_drawdown": 0.05108745579633178
  },
  "flat_yield_ci95": [
    -0.19239691422403488,
    0.4778652027493951
  ],
  "selected_probability_metrics": {
    "n": 121,
    "brier": 0.1878151827675584,
    "log_loss": 0.5584522059831822
  },
  "profit_odds_1pct_worse": {
    "bets": 117,
    "turnover": 2846,
    "pnl": 114.7812956957423,
    "flat_yield": 0.044963560480789054,
    "weighted_yield": 0.040330743392741494,
    "bankroll_return": 0.01147812956957423,
    "max_drawdown": 0.052363103004933076
  },
  "outlier_sensitivity": {
    "remove_top_5_profit_bets_pnl": -687.1565503540533,
    "remaining_bets": 116
  },
  "gate_forecast": false,
  "gate_economic_evidence": false,
  "execution_evidence": "NOT MEASURED: displayed historical quotes; paper stakes only",
  "delayed_price_test": {
    "original_bets": 121,
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
