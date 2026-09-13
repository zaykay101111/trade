# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 6000, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 3540, 'tune': 470, 'calibration': 752, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2023-07-01', 'tune': '2024-01-01', 'calibration': '2024-07-01', 'validation': '2025-07-01'}
Extra result-availability delay: 0 hours (added to imported availability).
Labels excluded at fitting cutoffs: 8

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689695; Brier=0.248274; accuracy=54.39%
- elo: log loss=0.621251; Brier=0.216202; accuracy=65.53%
- logistic: log loss=0.607059; Brier=0.210083; accuracy=66.67%
- boosted: log loss=0.614177; Brier=0.212835; accuracy=66.10%
- logistic_raw: log loss=0.607044; Brier=0.210011; accuracy=67.24%
- boosted_raw: log loss=0.613758; Brier=0.212625; accuracy=67.40%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.014192; 95% block interval [-0.022098, -0.005966]
- boosted: -0.007074; 95% block interval [-0.014920, 0.000893]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6983; elo=0.6619; logistic=0.6628; boosted=0.6652
- 2024-11, n=221: home_rate=0.6783; elo=0.6356; logistic=0.6281; boosted=0.6336
- 2024-12, n=191: home_rate=0.6969; elo=0.6229; logistic=0.6016; boosted=0.6070
- 2025-01, n=227: home_rate=0.6912; elo=0.6460; logistic=0.6302; boosted=0.6420
- 2025-02, n=173: home_rate=0.6898; elo=0.6102; logistic=0.5921; boosted=0.5979
- 2025-03, n=243: home_rate=0.6870; elo=0.5978; logistic=0.5877; boosted=0.5944
- 2025-04, n=106: home_rate=0.6977; elo=0.5807; logistic=0.5559; boosted=0.5655

Calibration bins: count / mean predicted / observed home-win rate
- elo: 7 / 0.087 / 0.000; 34 / 0.165 / 0.118; 95 / 0.257 / 0.326; 132 / 0.350 / 0.386; 153 / 0.450 / 0.366; 197 / 0.549 / 0.472; 236 / 0.648 / 0.653; 174 / 0.750 / 0.672; 168 / 0.843 / 0.780; 34 / 0.924 / 0.941
- logistic: 7 / 0.081 / 0.000; 45 / 0.161 / 0.111; 116 / 0.256 / 0.293; 176 / 0.352 / 0.364; 193 / 0.454 / 0.466; 234 / 0.549 / 0.564; 192 / 0.645 / 0.682; 173 / 0.749 / 0.786; 83 / 0.842 / 0.795; 11 / 0.917 / 1.000
- boosted: 8 / 0.187 / 0.250; 155 / 0.256 / 0.239; 186 / 0.350 / 0.371; 231 / 0.453 / 0.476; 181 / 0.548 / 0.597; 169 / 0.652 / 0.645; 250 / 0.746 / 0.756; 50 / 0.818 / 0.900

Full metrics: report.json. Model and data provenance: bundle.json.
