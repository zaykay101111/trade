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
- elo: log loss=0.616441; Brier=0.214768; accuracy=64.07%
- logistic: log loss=0.607681; Brier=0.210376; accuracy=65.93%
- boosted: log loss=0.625436; Brier=0.217759; accuracy=64.96%
- logistic_raw: log loss=0.610158; Brier=0.211218; accuracy=65.93%
- boosted_raw: log loss=0.625849; Brier=0.217900; accuracy=64.96%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.008760; 95% block interval [-0.015762, -0.001775]
- boosted: 0.008994; 95% block interval [-0.003584, 0.020559]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2023-10, n=52: home_rate=0.6952; elo=0.6921; logistic=0.6753; boosted=0.6876
- 2023-11, n=216: home_rate=0.6817; elo=0.6081; logistic=0.6119; boosted=0.6346
- 2023-12, n=210: home_rate=0.6823; elo=0.5758; logistic=0.5620; boosted=0.5795
- 2024-01, n=227: home_rate=0.6821; elo=0.6156; logistic=0.6147; boosted=0.6374
- 2024-02, n=176: home_rate=0.7022; elo=0.6226; logistic=0.6231; boosted=0.6404
- 2024-03, n=233: home_rate=0.7030; elo=0.6358; logistic=0.6067; boosted=0.6250
- 2024-04, n=116: home_rate=0.6859; elo=0.6252; logistic=0.6171; boosted=0.6185

Calibration bins: count / mean predicted / observed home-win rate
- elo: 4 / 0.093 / 0.000; 32 / 0.156 / 0.188; 95 / 0.251 / 0.232; 102 / 0.349 / 0.353; 175 / 0.450 / 0.457; 225 / 0.552 / 0.502; 218 / 0.644 / 0.528; 207 / 0.748 / 0.725; 140 / 0.845 / 0.829; 32 / 0.927 / 0.938
- logistic: 5 / 0.081 / 0.200; 37 / 0.163 / 0.216; 113 / 0.256 / 0.212; 142 / 0.351 / 0.408; 178 / 0.457 / 0.421; 249 / 0.548 / 0.518; 204 / 0.650 / 0.603; 171 / 0.753 / 0.789; 117 / 0.838 / 0.872; 14 / 0.926 / 0.929
- boosted: 251 / 0.349 / 0.315; 248 / 0.450 / 0.423; 213 / 0.544 / 0.521; 198 / 0.654 / 0.596; 320 / 0.744 / 0.797

Full metrics: report.json. Model and data provenance: bundle.json.
