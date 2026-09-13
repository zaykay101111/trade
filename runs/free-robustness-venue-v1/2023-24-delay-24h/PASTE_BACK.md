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
- elo: log loss=0.616516; Brier=0.214732; accuracy=64.15%
- logistic: log loss=0.610368; Brier=0.211149; accuracy=65.77%
- boosted: log loss=0.623316; Brier=0.216829; accuracy=65.04%
- logistic_raw: log loss=0.612345; Brier=0.211966; accuracy=65.93%
- boosted_raw: log loss=0.624460; Brier=0.217277; accuracy=65.20%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.006148; 95% block interval [-0.014880, 0.002743]
- boosted: 0.006800; 95% block interval [-0.005499, 0.017721]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6952; elo=0.6871; logistic=0.6722; boosted=0.6952
- 2023-11, n=216: home_rate=0.6817; elo=0.6132; logistic=0.6156; boosted=0.6400
- 2023-12, n=210: home_rate=0.6823; elo=0.5739; logistic=0.5657; boosted=0.5772
- 2024-01, n=227: home_rate=0.6821; elo=0.6145; logistic=0.6214; boosted=0.6292
- 2024-02, n=176: home_rate=0.7021; elo=0.6237; logistic=0.6264; boosted=0.6446
- 2024-03, n=233: home_rate=0.7029; elo=0.6336; logistic=0.6052; boosted=0.6137
- 2024-04, n=116: home_rate=0.6859; elo=0.6270; logistic=0.6183; boosted=0.6192

Calibration bins: count / mean predicted / observed home-win rate
- elo: 4 / 0.094 / 0.000; 30 / 0.154 / 0.167; 94 / 0.250 / 0.255; 102 / 0.346 / 0.304; 183 / 0.451 / 0.470; 218 / 0.553 / 0.523; 229 / 0.646 / 0.520; 200 / 0.750 / 0.720; 140 / 0.847 / 0.836; 30 / 0.929 / 0.933
- logistic: 7 / 0.069 / 0.286; 40 / 0.158 / 0.200; 112 / 0.257 / 0.241; 141 / 0.351 / 0.390; 175 / 0.456 / 0.429; 248 / 0.549 / 0.512; 207 / 0.651 / 0.599; 165 / 0.755 / 0.818; 118 / 0.837 / 0.839; 17 / 0.923 / 0.941
- boosted: 25 / 0.292 / 0.160; 268 / 0.350 / 0.332; 231 / 0.457 / 0.446; 176 / 0.550 / 0.551; 210 / 0.645 / 0.552; 320 / 0.744 / 0.809

Full metrics: report.json. Model and data provenance: bundle.json.
