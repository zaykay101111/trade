# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 4770, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 2310, 'tune': 514, 'calibration': 688, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2022-07-01', 'tune': '2023-01-01', 'calibration': '2023-07-01', 'validation': '2024-07-01'}
Extra result-availability delay: 48 hours (added to imported availability).
Labels excluded at fitting cutoffs: 28

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689728; Brier=0.248291; accuracy=54.31%
- elo: log loss=0.616425; Brier=0.214642; accuracy=64.63%
- logistic: log loss=0.608999; Brier=0.210885; accuracy=65.93%
- boosted: log loss=0.624562; Brier=0.217416; accuracy=63.90%
- logistic_raw: log loss=0.611481; Brier=0.211756; accuracy=66.26%
- boosted_raw: log loss=0.625850; Brier=0.217910; accuracy=64.15%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.007426; 95% block interval [-0.015526, 0.000507]
- boosted: 0.008137; 95% block interval [-0.004520, 0.018697]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6950; elo=0.6903; logistic=0.6714; boosted=0.6926
- 2023-11, n=216: home_rate=0.6818; elo=0.6127; logistic=0.6186; boosted=0.6366
- 2023-12, n=210: home_rate=0.6824; elo=0.5744; logistic=0.5607; boosted=0.5795
- 2024-01, n=227: home_rate=0.6822; elo=0.6129; logistic=0.6134; boosted=0.6335
- 2024-02, n=176: home_rate=0.7018; elo=0.6239; logistic=0.6281; boosted=0.6478
- 2024-03, n=233: home_rate=0.7026; elo=0.6331; logistic=0.6065; boosted=0.6174
- 2024-04, n=116: home_rate=0.6859; elo=0.6283; logistic=0.6178; boosted=0.6149

Calibration bins: count / mean predicted / observed home-win rate
- elo: 5 / 0.095 / 0.000; 29 / 0.156 / 0.172; 92 / 0.249 / 0.261; 109 / 0.349 / 0.294; 172 / 0.451 / 0.459; 222 / 0.553 / 0.527; 234 / 0.645 / 0.526; 199 / 0.751 / 0.729; 137 / 0.847 / 0.832; 31 / 0.927 / 0.935
- logistic: 5 / 0.080 / 0.200; 39 / 0.158 / 0.179; 112 / 0.255 / 0.250; 137 / 0.348 / 0.358; 174 / 0.453 / 0.443; 257 / 0.548 / 0.533; 202 / 0.651 / 0.569; 167 / 0.754 / 0.826; 121 / 0.838 / 0.835; 16 / 0.927 / 0.938
- boosted: 7 / 0.294 / 0.143; 289 / 0.350 / 0.322; 250 / 0.453 / 0.480; 166 / 0.560 / 0.494; 208 / 0.653 / 0.591; 310 / 0.742 / 0.803

Full metrics: report.json. Model and data provenance: bundle.json.
