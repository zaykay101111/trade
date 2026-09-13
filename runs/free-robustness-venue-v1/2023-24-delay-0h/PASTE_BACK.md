# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 4770, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 2310, 'tune': 528, 'calibration': 688, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2022-07-01', 'tune': '2023-01-01', 'calibration': '2023-07-01', 'validation': '2024-07-01'}
Extra result-availability delay: 0 hours (added to imported availability).
Labels excluded at fitting cutoffs: 14

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689805; Brier=0.248329; accuracy=54.31%
- elo: log loss=0.616256; Brier=0.214709; accuracy=64.31%
- logistic: log loss=0.609683; Brier=0.210956; accuracy=65.77%
- boosted: log loss=0.625116; Brier=0.217608; accuracy=64.88%
- logistic_raw: log loss=0.611575; Brier=0.211698; accuracy=65.85%
- boosted_raw: log loss=0.625495; Brier=0.217734; accuracy=64.88%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.006573; 95% block interval [-0.014840, 0.001605]
- boosted: 0.008860; 95% block interval [-0.003740, 0.020464]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6952; elo=0.6920; logistic=0.6751; boosted=0.6876
- 2023-11, n=216: home_rate=0.6817; elo=0.6070; logistic=0.6092; boosted=0.6338
- 2023-12, n=210: home_rate=0.6823; elo=0.5752; logistic=0.5677; boosted=0.5793
- 2024-01, n=227: home_rate=0.6821; elo=0.6161; logistic=0.6227; boosted=0.6372
- 2024-02, n=176: home_rate=0.7022; elo=0.6225; logistic=0.6232; boosted=0.6399
- 2024-03, n=233: home_rate=0.7030; elo=0.6358; logistic=0.6068; boosted=0.6248
- 2024-04, n=116: home_rate=0.6859; elo=0.6253; logistic=0.6170; boosted=0.6185

Calibration bins: count / mean predicted / observed home-win rate
- elo: 4 / 0.093 / 0.000; 32 / 0.156 / 0.188; 95 / 0.251 / 0.232; 102 / 0.349 / 0.353; 174 / 0.449 / 0.448; 224 / 0.551 / 0.513; 221 / 0.644 / 0.525; 207 / 0.748 / 0.720; 140 / 0.846 / 0.836; 31 / 0.928 / 0.935
- logistic: 7 / 0.072 / 0.286; 39 / 0.161 / 0.231; 112 / 0.257 / 0.214; 142 / 0.351 / 0.408; 177 / 0.457 / 0.424; 248 / 0.548 / 0.516; 203 / 0.649 / 0.606; 171 / 0.753 / 0.784; 117 / 0.838 / 0.872; 14 / 0.926 / 0.929
- boosted: 252 / 0.350 / 0.313; 248 / 0.450 / 0.427; 213 / 0.545 / 0.516; 197 / 0.654 / 0.599; 320 / 0.744 / 0.797

Full metrics: report.json. Model and data provenance: bundle.json.
