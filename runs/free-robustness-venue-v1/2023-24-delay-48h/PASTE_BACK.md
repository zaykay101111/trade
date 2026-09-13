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
- elo: log loss=0.616245; Brier=0.214586; accuracy=64.72%
- logistic: log loss=0.611229; Brier=0.211519; accuracy=66.10%
- boosted: log loss=0.624495; Brier=0.217385; accuracy=63.90%
- logistic_raw: log loss=0.613009; Brier=0.212275; accuracy=66.18%
- boosted_raw: log loss=0.625844; Brier=0.217903; accuracy=64.15%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005016; 95% block interval [-0.014164, 0.004421]
- boosted: 0.008250; 95% block interval [-0.004291, 0.018838]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6950; elo=0.6902; logistic=0.6713; boosted=0.6913
- 2023-11, n=216: home_rate=0.6818; elo=0.6118; logistic=0.6160; boosted=0.6367
- 2023-12, n=210: home_rate=0.6824; elo=0.5737; logistic=0.5671; boosted=0.5795
- 2024-01, n=227: home_rate=0.6822; elo=0.6134; logistic=0.6221; boosted=0.6336
- 2024-02, n=176: home_rate=0.7018; elo=0.6238; logistic=0.6281; boosted=0.6476
- 2024-03, n=233: home_rate=0.7026; elo=0.6332; logistic=0.6067; boosted=0.6173
- 2024-04, n=116: home_rate=0.6859; elo=0.6284; logistic=0.6177; boosted=0.6148

Calibration bins: count / mean predicted / observed home-win rate
- elo: 5 / 0.095 / 0.000; 28 / 0.155 / 0.179; 93 / 0.249 / 0.258; 110 / 0.350 / 0.291; 172 / 0.451 / 0.459; 224 / 0.553 / 0.531; 233 / 0.646 / 0.528; 198 / 0.752 / 0.722; 136 / 0.847 / 0.838; 31 / 0.927 / 0.935
- logistic: 9 / 0.075 / 0.333; 38 / 0.158 / 0.184; 111 / 0.255 / 0.252; 138 / 0.348 / 0.355; 171 / 0.452 / 0.433; 258 / 0.548 / 0.535; 203 / 0.650 / 0.571; 166 / 0.755 / 0.831; 120 / 0.838 / 0.833; 16 / 0.927 / 0.938
- boosted: 17 / 0.297 / 0.176; 279 / 0.351 / 0.326; 250 / 0.453 / 0.480; 167 / 0.560 / 0.491; 206 / 0.653 / 0.592; 311 / 0.743 / 0.804

Full metrics: report.json. Model and data provenance: bundle.json.
