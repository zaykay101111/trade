# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 3540, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 1080, 'tune': 506, 'calibration': 707, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2021-07-01', 'tune': '2022-01-01', 'calibration': '2022-07-01', 'validation': '2023-07-01'}
Extra result-availability delay: 24 hours (added to imported availability).
Labels excluded at fitting cutoffs: 17

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.682905; Brier=0.244889; accuracy=58.05%
- elo: log loss=0.653223; Brier=0.229624; accuracy=62.20%
- logistic: log loss=0.647629; Brier=0.227519; accuracy=62.85%
- boosted: log loss=0.661858; Brier=0.234423; accuracy=60.65%
- logistic_raw: log loss=0.648344; Brier=0.227993; accuracy=62.44%
- boosted_raw: log loss=0.659245; Brier=0.233362; accuracy=60.65%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005594; 95% block interval [-0.011305, 0.000581]
- boosted: 0.008635; 95% block interval [-0.004640, 0.022806]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2022-10, n=100: home_rate=0.6760; elo=0.6488; logistic=0.6539; boosted=0.6482
- 2022-11, n=216: home_rate=0.6776; elo=0.6573; logistic=0.6517; boosted=0.6508
- 2022-12, n=226: home_rate=0.6776; elo=0.6861; logistic=0.6831; boosted=0.6796
- 2023-01, n=223: home_rate=0.6864; elo=0.6540; logistic=0.6497; boosted=0.6788
- 2023-02, n=160: home_rate=0.6784; elo=0.5922; logistic=0.5997; boosted=0.6440
- 2023-03, n=232: home_rate=0.6939; elo=0.6528; logistic=0.6360; boosted=0.6609
- 2023-04, n=73: home_rate=0.6886; elo=0.6784; logistic=0.6530; boosted=0.6491

Calibration bins: count / mean predicted / observed home-win rate
- elo: 11 / 0.165 / 0.545; 70 / 0.259 / 0.314; 113 / 0.349 / 0.345; 193 / 0.452 / 0.523; 246 / 0.550 / 0.565; 262 / 0.649 / 0.603; 205 / 0.745 / 0.722; 117 / 0.841 / 0.786; 13 / 0.910 / 0.692
- logistic: 11 / 0.167 / 0.455; 88 / 0.260 / 0.330; 124 / 0.353 / 0.371; 238 / 0.452 / 0.508; 289 / 0.548 / 0.574; 243 / 0.649 / 0.704; 173 / 0.744 / 0.723; 62 / 0.835 / 0.790; 2 / 0.914 / 1.000
- boosted: 122 / 0.268 / 0.385; 158 / 0.358 / 0.411; 224 / 0.458 / 0.554; 215 / 0.553 / 0.563; 184 / 0.645 / 0.679; 323 / 0.756 / 0.709; 4 / 0.803 / 0.750

Full metrics: report.json. Model and data provenance: bundle.json.
