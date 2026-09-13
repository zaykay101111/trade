# Box-score feature extension: development comparison

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Base eleven features versus the same set plus nine possession-adjusted box-score differentials, on the three existing chronological development folds. Same lambda 0.01, same sigmoid calibration, same fold shape. Rolling window of 20 settled games with the identical availability rule; previous-season win rate uses only completed prior-season games. Possession count is the standard estimate FGA-OREB+TOV+0.44*FTA, a convention rather than a measurement. These folds have been inspected many times: this is development evidence, not confirmation, and adopting these features requires a new frozen release before any season counts.

Base features (11): margin_diff, scored_diff, allowed_diff, win_rate_diff, history_count_diff, home_rest, away_rest, home_b2b, away_b2b, elo_diff, neutral
Added (9): off_rating_diff, def_rating_diff, net_rating_diff, pace_diff, efg_diff, tov_rate_diff, oreb_rate_diff, ft_rate_diff, prev_season_win_rate_diff

Per-fold calibrated log loss (lower is better):
- 2022-23, n=1230: base=0.647034; extended=0.648137
  extended minus base: +0.001103; 95% block interval [-0.004084, +0.005725]  (includes zero)
- 2023-24, n=1230: base=0.609683; extended=0.609588
  extended minus base: -0.000095; 95% block interval [-0.002936, +0.002727]  (includes zero)
- 2024-25, n=1230: base=0.607059; extended=0.608418
  extended minus base: +0.001360; 95% block interval [-0.002199, +0.004480]  (includes zero)

Pooled descriptive metrics:
- base: n=3690; log loss=0.621258; Brier=0.216074; accuracy=65.26%; raw log loss=0.622136
- extended: n=3690; log loss=0.622048; Brier=0.216358; accuracy=65.50%; raw log loss=0.622456
- pooled extended minus base: +0.000789

Negative favors the extended set. Pooled folds share training history and are
descriptive. Intervals exclude training and model-selection uncertainty and are not
multiplicity-corrected. No feature set is promoted by this command, and nothing here
is confirmation: these folds have been inspected repeatedly.
