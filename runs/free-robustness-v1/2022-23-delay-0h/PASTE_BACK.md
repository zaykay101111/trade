# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 3540, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 1080, 'tune': 514, 'calibration': 707, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2021-07-01', 'tune': '2022-01-01', 'calibration': '2022-07-01', 'validation': '2023-07-01'}
Extra result-availability delay: 0 hours (added to imported availability).
Labels excluded at fitting cutoffs: 9

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.682937; Brier=0.244906; accuracy=58.05%
- elo: log loss=0.652719; Brier=0.229343; accuracy=62.44%
- logistic: log loss=0.647001; Brier=0.227169; accuracy=63.33%
- boosted: log loss=0.649647; Brier=0.228801; accuracy=63.01%
- logistic_raw: log loss=0.647757; Brier=0.227663; accuracy=63.17%
- boosted_raw: log loss=0.648636; Brier=0.228431; accuracy=62.68%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005718; 95% block interval [-0.011434, 0.000493]
- boosted: -0.003072; 95% block interval [-0.013164, 0.007600]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2022-10, n=100: home_rate=0.6761; elo=0.6491; logistic=0.6538; boosted=0.6497
- 2022-11, n=216: home_rate=0.6776; elo=0.6574; logistic=0.6520; boosted=0.6445
- 2022-12, n=226: home_rate=0.6777; elo=0.6806; logistic=0.6781; boosted=0.6643
- 2023-01, n=223: home_rate=0.6864; elo=0.6566; logistic=0.6518; boosted=0.6588
- 2023-02, n=160: home_rate=0.6785; elo=0.5921; logistic=0.5995; boosted=0.6228
- 2023-03, n=232: home_rate=0.6939; elo=0.6531; logistic=0.6358; boosted=0.6488
- 2023-04, n=73: home_rate=0.6886; elo=0.6776; logistic=0.6518; boosted=0.6531

Calibration bins: count / mean predicted / observed home-win rate
- elo: 13 / 0.167 / 0.538; 65 / 0.257 / 0.292; 120 / 0.350 / 0.367; 192 / 0.453 / 0.510; 235 / 0.550 / 0.570; 280 / 0.649 / 0.614; 201 / 0.747 / 0.721; 113 / 0.845 / 0.770; 11 / 0.913 / 0.727
- logistic: 11 / 0.167 / 0.455; 92 / 0.260 / 0.326; 132 / 0.357 / 0.348; 218 / 0.454 / 0.518; 302 / 0.550 / 0.579; 240 / 0.649 / 0.700; 168 / 0.745 / 0.738; 65 / 0.834 / 0.785; 2 / 0.916 / 1.000
- boosted: 114 / 0.270 / 0.360; 148 / 0.358 / 0.378; 247 / 0.451 / 0.514; 265 / 0.545 / 0.619; 151 / 0.643 / 0.675; 273 / 0.763 / 0.725; 32 / 0.804 / 0.812

Full metrics: report.json. Model and data provenance: bundle.json.
