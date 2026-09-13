# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 6000, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 3540, 'tune': 450, 'calibration': 752, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2023-07-01', 'tune': '2024-01-01', 'calibration': '2024-07-01', 'validation': '2025-07-01'}
Extra result-availability delay: 48 hours (added to imported availability).
Labels excluded at fitting cutoffs: 28

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689669; Brier=0.248261; accuracy=54.39%
- elo: log loss=0.623973; Brier=0.217323; accuracy=65.69%
- logistic: log loss=0.610580; Brier=0.211740; accuracy=67.15%
- boosted: log loss=0.614978; Brier=0.213092; accuracy=65.85%
- logistic_raw: log loss=0.610347; Brier=0.211578; accuracy=66.50%
- boosted_raw: log loss=0.614887; Brier=0.212963; accuracy=67.40%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.013393; 95% block interval [-0.021345, -0.004996]
- boosted: -0.008995; 95% block interval [-0.017209, -0.000249]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6982; elo=0.6609; logistic=0.6627; boosted=0.6579
- 2024-11, n=221: home_rate=0.6784; elo=0.6370; logistic=0.6328; boosted=0.6348
- 2024-12, n=191: home_rate=0.6968; elo=0.6242; logistic=0.6030; boosted=0.6099
- 2025-01, n=227: home_rate=0.6912; elo=0.6493; logistic=0.6326; boosted=0.6379
- 2025-02, n=173: home_rate=0.6898; elo=0.6116; logistic=0.5965; boosted=0.6005
- 2025-03, n=243: home_rate=0.6870; elo=0.6048; logistic=0.5948; boosted=0.6058
- 2025-04, n=106: home_rate=0.6977; elo=0.5822; logistic=0.5560; boosted=0.5506

Calibration bins: count / mean predicted / observed home-win rate
- elo: 6 / 0.088 / 0.000; 33 / 0.159 / 0.121; 102 / 0.258 / 0.314; 131 / 0.355 / 0.382; 151 / 0.453 / 0.371; 192 / 0.550 / 0.500; 236 / 0.646 / 0.644; 184 / 0.751 / 0.663; 159 / 0.844 / 0.774; 36 / 0.921 / 0.944
- logistic: 7 / 0.081 / 0.000; 47 / 0.159 / 0.128; 114 / 0.256 / 0.298; 182 / 0.354 / 0.357; 191 / 0.456 / 0.455; 229 / 0.548 / 0.607; 188 / 0.643 / 0.660; 176 / 0.746 / 0.750; 86 / 0.841 / 0.837; 10 / 0.917 / 1.000
- boosted: 9 / 0.190 / 0.111; 165 / 0.261 / 0.248; 196 / 0.351 / 0.378; 207 / 0.452 / 0.493; 168 / 0.551 / 0.595; 183 / 0.654 / 0.656; 241 / 0.747 / 0.739; 61 / 0.817 / 0.869

Full metrics: report.json. Model and data provenance: bundle.json.
