# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 6000, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 3540, 'tune': 470, 'calibration': 752, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2023-07-01', 'tune': '2024-01-01', 'calibration': '2024-07-01', 'validation': '2025-07-01'}
Labels excluded at fitting cutoffs: 8

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689695; Brier=0.248274; accuracy=54.39%
- elo: log loss=0.621281; Brier=0.216215; accuracy=65.53%
- logistic: log loss=0.606957; Brier=0.209976; accuracy=66.59%
- boosted: log loss=0.613644; Brier=0.212574; accuracy=66.83%
- logistic_raw: log loss=0.607088; Brier=0.209966; accuracy=67.24%
- boosted_raw: log loss=0.613264; Brier=0.212360; accuracy=67.80%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.014324; 95% block interval [-0.021765, -0.006246]
- boosted: -0.007637; 95% block interval [-0.015533, 0.000475]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6983; elo=0.6620; logistic=0.6632; boosted=0.6609
- 2024-11, n=221: home_rate=0.6783; elo=0.6356; logistic=0.6294; boosted=0.6341
- 2024-12, n=191: home_rate=0.6969; elo=0.6230; logistic=0.5940; boosted=0.6051
- 2025-01, n=227: home_rate=0.6912; elo=0.6460; logistic=0.6352; boosted=0.6412
- 2025-02, n=173: home_rate=0.6898; elo=0.6102; logistic=0.5919; boosted=0.5983
- 2025-03, n=243: home_rate=0.6870; elo=0.5978; logistic=0.5875; boosted=0.5944
- 2025-04, n=106: home_rate=0.6977; elo=0.5807; logistic=0.5556; boosted=0.5658

Calibration bins: count / mean predicted / observed home-win rate
- elo: 7 / 0.087 / 0.000; 34 / 0.165 / 0.118; 95 / 0.257 / 0.326; 132 / 0.350 / 0.386; 153 / 0.450 / 0.366; 196 / 0.549 / 0.469; 237 / 0.647 / 0.654; 174 / 0.750 / 0.672; 168 / 0.843 / 0.780; 34 / 0.924 / 0.941
- logistic: 6 / 0.080 / 0.000; 45 / 0.160 / 0.133; 120 / 0.256 / 0.283; 174 / 0.353 / 0.356; 191 / 0.455 / 0.476; 232 / 0.549 / 0.556; 192 / 0.644 / 0.688; 175 / 0.749 / 0.783; 83 / 0.842 / 0.795; 12 / 0.916 / 1.000
- boosted: 6 / 0.185 / 0.167; 157 / 0.255 / 0.236; 186 / 0.349 / 0.366; 226 / 0.451 / 0.465; 188 / 0.547 / 0.622; 164 / 0.651 / 0.622; 249 / 0.747 / 0.763; 54 / 0.819 / 0.907

Full metrics: report.json. Model and data provenance: bundle.json.
