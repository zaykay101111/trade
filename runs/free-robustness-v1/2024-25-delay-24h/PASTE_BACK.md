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
- elo: log loss=0.622797; Brier=0.216828; accuracy=65.61%
- logistic: log loss=0.609073; Brier=0.210968; accuracy=66.99%
- boosted: log loss=0.614085; Brier=0.212800; accuracy=65.69%
- logistic_raw: log loss=0.609079; Brier=0.210900; accuracy=66.83%
- boosted_raw: log loss=0.614067; Brier=0.212647; accuracy=67.07%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.013724; 95% block interval [-0.021333, -0.005609]
- boosted: -0.008712; 95% block interval [-0.017489, -0.000089]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6982; elo=0.6610; logistic=0.6638; boosted=0.6521
- 2024-11, n=221: home_rate=0.6783; elo=0.6369; logistic=0.6340; boosted=0.6353
- 2024-12, n=191: home_rate=0.6968; elo=0.6242; logistic=0.5942; boosted=0.6090
- 2025-01, n=227: home_rate=0.6912; elo=0.6475; logistic=0.6357; boosted=0.6423
- 2025-02, n=173: home_rate=0.6898; elo=0.6109; logistic=0.5947; boosted=0.6006
- 2025-03, n=243: home_rate=0.6870; elo=0.6012; logistic=0.5911; boosted=0.5980
- 2025-04, n=106: home_rate=0.6977; elo=0.5823; logistic=0.5558; boosted=0.5529

Calibration bins: count / mean predicted / observed home-win rate
- elo: 6 / 0.086 / 0.000; 33 / 0.159 / 0.121; 99 / 0.257 / 0.313; 135 / 0.355 / 0.370; 151 / 0.451 / 0.384; 197 / 0.551 / 0.497; 228 / 0.648 / 0.645; 183 / 0.749 / 0.661; 166 / 0.845 / 0.783; 32 / 0.924 / 0.938
- logistic: 6 / 0.080 / 0.000; 44 / 0.156 / 0.159; 125 / 0.255 / 0.264; 169 / 0.353 / 0.361; 197 / 0.454 / 0.467; 226 / 0.548 / 0.575; 188 / 0.644 / 0.697; 176 / 0.746 / 0.750; 88 / 0.840 / 0.818; 11 / 0.919 / 1.000
- boosted: 14 / 0.184 / 0.143; 163 / 0.250 / 0.233; 180 / 0.350 / 0.378; 206 / 0.453 / 0.505; 200 / 0.545 / 0.585; 165 / 0.652 / 0.648; 213 / 0.748 / 0.723; 89 / 0.825 / 0.888

Full metrics: report.json. Model and data provenance: bundle.json.
