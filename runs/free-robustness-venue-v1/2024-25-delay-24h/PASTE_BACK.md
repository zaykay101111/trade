# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 6000, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 3540, 'tune': 458, 'calibration': 752, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2023-07-01', 'tune': '2024-01-01', 'calibration': '2024-07-01', 'validation': '2025-07-01'}
Extra result-availability delay: 24 hours (added to imported availability).
Labels excluded at fitting cutoffs: 20

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689677; Brier=0.248265; accuracy=54.39%
- elo: log loss=0.622766; Brier=0.216814; accuracy=65.61%
- logistic: log loss=0.609192; Brier=0.211089; accuracy=66.91%
- boosted: log loss=0.613607; Brier=0.212565; accuracy=65.61%
- logistic_raw: log loss=0.609066; Brier=0.210964; accuracy=66.83%
- boosted_raw: log loss=0.613584; Brier=0.212418; accuracy=67.32%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.013574; 95% block interval [-0.021543, -0.005142]
- boosted: -0.009158; 95% block interval [-0.017521, -0.000419]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6982; elo=0.6609; logistic=0.6634; boosted=0.6527
- 2024-11, n=221: home_rate=0.6783; elo=0.6368; logistic=0.6327; boosted=0.6339
- 2024-12, n=191: home_rate=0.6968; elo=0.6242; logistic=0.6018; boosted=0.6065
- 2025-01, n=227: home_rate=0.6912; elo=0.6474; logistic=0.6310; boosted=0.6419
- 2025-02, n=173: home_rate=0.6898; elo=0.6109; logistic=0.5949; boosted=0.6002
- 2025-03, n=243: home_rate=0.6870; elo=0.6012; logistic=0.5912; boosted=0.5986
- 2025-04, n=106: home_rate=0.6977; elo=0.5823; logistic=0.5562; boosted=0.5545

Calibration bins: count / mean predicted / observed home-win rate
- elo: 6 / 0.086 / 0.000; 33 / 0.159 / 0.121; 99 / 0.257 / 0.313; 135 / 0.355 / 0.370; 151 / 0.451 / 0.384; 198 / 0.551 / 0.500; 227 / 0.648 / 0.643; 184 / 0.749 / 0.663; 165 / 0.845 / 0.782; 32 / 0.924 / 0.938
- logistic: 7 / 0.081 / 0.000; 45 / 0.157 / 0.156; 122 / 0.256 / 0.279; 169 / 0.353 / 0.367; 201 / 0.454 / 0.458; 225 / 0.548 / 0.573; 187 / 0.644 / 0.695; 177 / 0.746 / 0.746; 86 / 0.840 / 0.837; 11 / 0.918 / 1.000
- boosted: 12 / 0.180 / 0.167; 171 / 0.252 / 0.228; 174 / 0.352 / 0.397; 207 / 0.454 / 0.498; 206 / 0.548 / 0.568; 161 / 0.654 / 0.671; 221 / 0.752 / 0.733; 78 / 0.826 / 0.885

Full metrics: report.json. Model and data provenance: bundle.json.
