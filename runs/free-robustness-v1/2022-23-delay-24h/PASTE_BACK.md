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
- elo: log loss=0.653390; Brier=0.229700; accuracy=62.20%
- logistic: log loss=0.647595; Brier=0.227505; accuracy=62.93%
- boosted: log loss=0.661945; Brier=0.234468; accuracy=60.65%
- logistic_raw: log loss=0.648310; Brier=0.227979; accuracy=62.44%
- boosted_raw: log loss=0.659322; Brier=0.233402; accuracy=60.65%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005794; 95% block interval [-0.011503, 0.000371]
- boosted: 0.008555; 95% block interval [-0.004833, 0.022775]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2022-10, n=100: home_rate=0.6760; elo=0.6488; logistic=0.6539; boosted=0.6482
- 2022-11, n=216: home_rate=0.6776; elo=0.6573; logistic=0.6517; boosted=0.6508
- 2022-12, n=226: home_rate=0.6776; elo=0.6867; logistic=0.6831; boosted=0.6796
- 2023-01, n=223: home_rate=0.6864; elo=0.6543; logistic=0.6495; boosted=0.6788
- 2023-02, n=160: home_rate=0.6784; elo=0.5922; logistic=0.5997; boosted=0.6436
- 2023-03, n=232: home_rate=0.6939; elo=0.6527; logistic=0.6359; boosted=0.6617
- 2023-04, n=73: home_rate=0.6886; elo=0.6784; logistic=0.6530; boosted=0.6491

Calibration bins: count / mean predicted / observed home-win rate
- elo: 11 / 0.164 / 0.545; 69 / 0.258 / 0.319; 115 / 0.350 / 0.339; 192 / 0.452 / 0.526; 246 / 0.550 / 0.565; 262 / 0.649 / 0.603; 205 / 0.745 / 0.722; 117 / 0.841 / 0.786; 13 / 0.911 / 0.692
- logistic: 11 / 0.167 / 0.455; 88 / 0.260 / 0.330; 124 / 0.353 / 0.371; 239 / 0.452 / 0.506; 288 / 0.549 / 0.576; 243 / 0.649 / 0.704; 172 / 0.743 / 0.727; 63 / 0.835 / 0.778; 2 / 0.914 / 1.000
- boosted: 122 / 0.268 / 0.385; 159 / 0.358 / 0.415; 223 / 0.458 / 0.552; 215 / 0.553 / 0.563; 184 / 0.645 / 0.679; 323 / 0.756 / 0.709; 4 / 0.803 / 0.750

Full metrics: report.json. Model and data provenance: bundle.json.
