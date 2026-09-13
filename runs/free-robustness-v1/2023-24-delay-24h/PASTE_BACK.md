# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 4770, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 2310, 'tune': 522, 'calibration': 688, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2022-07-01', 'tune': '2023-01-01', 'calibration': '2023-07-01', 'validation': '2024-07-01'}
Extra result-availability delay: 24 hours (added to imported availability).
Labels excluded at fitting cutoffs: 20

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689774; Brier=0.248314; accuracy=54.31%
- elo: log loss=0.616687; Brier=0.214787; accuracy=64.07%
- logistic: log loss=0.608185; Brier=0.210529; accuracy=65.77%
- boosted: log loss=0.623367; Brier=0.216846; accuracy=64.96%
- logistic_raw: log loss=0.610839; Brier=0.211458; accuracy=66.02%
- boosted_raw: log loss=0.624485; Brier=0.217285; accuracy=65.12%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.008503; 95% block interval [-0.016282, -0.000803]
- boosted: 0.006680; 95% block interval [-0.005666, 0.017610]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6952; elo=0.6873; logistic=0.6723; boosted=0.6952
- 2023-11, n=216: home_rate=0.6817; elo=0.6142; logistic=0.6183; boosted=0.6399
- 2023-12, n=210: home_rate=0.6823; elo=0.5744; logistic=0.5592; boosted=0.5776
- 2024-01, n=227: home_rate=0.6821; elo=0.6139; logistic=0.6130; boosted=0.6293
- 2024-02, n=176: home_rate=0.7021; elo=0.6238; logistic=0.6264; boosted=0.6444
- 2024-03, n=233: home_rate=0.7029; elo=0.6335; logistic=0.6051; boosted=0.6137
- 2024-04, n=116: home_rate=0.6859; elo=0.6270; logistic=0.6183; boosted=0.6192

Calibration bins: count / mean predicted / observed home-win rate
- elo: 4 / 0.094 / 0.000; 30 / 0.154 / 0.167; 93 / 0.249 / 0.258; 103 / 0.346 / 0.301; 182 / 0.451 / 0.473; 218 / 0.553 / 0.518; 228 / 0.645 / 0.518; 201 / 0.750 / 0.726; 141 / 0.846 / 0.830; 30 / 0.929 / 0.933
- logistic: 4 / 0.076 / 0.250; 39 / 0.158 / 0.179; 113 / 0.257 / 0.248; 141 / 0.351 / 0.383; 180 / 0.456 / 0.433; 244 / 0.549 / 0.512; 210 / 0.651 / 0.600; 163 / 0.755 / 0.816; 119 / 0.837 / 0.840; 17 / 0.923 / 0.941
- boosted: 18 / 0.289 / 0.167; 275 / 0.349 / 0.327; 230 / 0.457 / 0.448; 178 / 0.550 / 0.551; 209 / 0.645 / 0.550; 320 / 0.743 / 0.809

Full metrics: report.json. Model and data provenance: bundle.json.
