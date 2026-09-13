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
- elo: log loss=0.652554; Brier=0.229267; accuracy=62.44%
- logistic: log loss=0.647034; Brier=0.227182; accuracy=63.33%
- boosted: log loss=0.649602; Brier=0.228777; accuracy=63.09%
- logistic_raw: log loss=0.647790; Brier=0.227677; accuracy=63.01%
- boosted_raw: log loss=0.648595; Brier=0.228409; accuracy=62.76%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005520; 95% block interval [-0.011385, 0.000825]
- boosted: -0.002952; 95% block interval [-0.013148, 0.007717]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2022-10, n=100: home_rate=0.6761; elo=0.6491; logistic=0.6538; boosted=0.6497
- 2022-11, n=216: home_rate=0.6776; elo=0.6574; logistic=0.6520; boosted=0.6445
- 2022-12, n=226: home_rate=0.6777; elo=0.6799; logistic=0.6781; boosted=0.6643
- 2023-01, n=223: home_rate=0.6864; elo=0.6562; logistic=0.6519; boosted=0.6585
- 2023-02, n=160: home_rate=0.6785; elo=0.5921; logistic=0.5995; boosted=0.6228
- 2023-03, n=232: home_rate=0.6939; elo=0.6532; logistic=0.6359; boosted=0.6488
- 2023-04, n=73: home_rate=0.6886; elo=0.6775; logistic=0.6518; boosted=0.6531

Calibration bins: count / mean predicted / observed home-win rate
- elo: 13 / 0.167 / 0.538; 67 / 0.258 / 0.284; 117 / 0.350 / 0.376; 193 / 0.453 / 0.508; 236 / 0.550 / 0.568; 279 / 0.650 / 0.616; 201 / 0.747 / 0.721; 113 / 0.845 / 0.770; 11 / 0.913 / 0.727
- logistic: 11 / 0.167 / 0.455; 92 / 0.260 / 0.326; 132 / 0.357 / 0.348; 218 / 0.454 / 0.518; 302 / 0.550 / 0.579; 239 / 0.648 / 0.703; 169 / 0.744 / 0.734; 65 / 0.834 / 0.785; 2 / 0.916 / 1.000
- boosted: 114 / 0.270 / 0.360; 148 / 0.358 / 0.378; 246 / 0.451 / 0.512; 266 / 0.545 / 0.620; 151 / 0.643 / 0.675; 273 / 0.763 / 0.725; 32 / 0.804 / 0.812

Full metrics: report.json. Model and data provenance: bundle.json.
