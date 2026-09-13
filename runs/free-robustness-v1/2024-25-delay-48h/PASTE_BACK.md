# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 6000, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 3540, 'tune': 450, 'calibration': 752, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2023-07-01', 'tune': '2024-01-01', 'calibration': '2024-07-01', 'validation': '2025-07-01'}
Extra result-availability delay: 48 hours (added to imported availability).
Labels excluded at fitting cutoffs: 28

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.689669; Brier=0.248261; accuracy=54.39%
- elo: log loss=0.624004; Brier=0.217337; accuracy=65.69%
- logistic: log loss=0.610483; Brier=0.211627; accuracy=67.24%
- boosted: log loss=0.614834; Brier=0.213031; accuracy=65.85%
- logistic_raw: log loss=0.610374; Brier=0.211520; accuracy=66.50%
- boosted_raw: log loss=0.614933; Brier=0.212977; accuracy=67.24%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.013521; 95% block interval [-0.021156, -0.005367]
- boosted: -0.009170; 95% block interval [-0.017481, -0.000566]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2024-10, n=69: home_rate=0.6982; elo=0.6610; logistic=0.6631; boosted=0.6603
- 2024-11, n=221: home_rate=0.6784; elo=0.6371; logistic=0.6342; boosted=0.6344
- 2024-12, n=191: home_rate=0.6968; elo=0.6243; logistic=0.5954; boosted=0.6107
- 2025-01, n=227: home_rate=0.6912; elo=0.6493; logistic=0.6374; boosted=0.6370
- 2025-02, n=173: home_rate=0.6898; elo=0.6116; logistic=0.5963; boosted=0.6009
- 2025-03, n=243: home_rate=0.6870; elo=0.6048; logistic=0.5947; boosted=0.6037
- 2025-04, n=106: home_rate=0.6977; elo=0.5823; logistic=0.5557; boosted=0.5524

Calibration bins: count / mean predicted / observed home-win rate
- elo: 6 / 0.088 / 0.000; 33 / 0.159 / 0.121; 102 / 0.258 / 0.314; 131 / 0.355 / 0.382; 151 / 0.453 / 0.371; 192 / 0.550 / 0.500; 236 / 0.646 / 0.644; 184 / 0.751 / 0.663; 159 / 0.844 / 0.774; 36 / 0.921 / 0.944
- logistic: 6 / 0.080 / 0.000; 46 / 0.158 / 0.130; 117 / 0.255 / 0.308; 180 / 0.353 / 0.339; 189 / 0.455 / 0.460; 228 / 0.547 / 0.605; 190 / 0.643 / 0.663; 177 / 0.746 / 0.746; 86 / 0.841 / 0.837; 11 / 0.917 / 1.000
- boosted: 8 / 0.187 / 0.125; 166 / 0.261 / 0.259; 197 / 0.351 / 0.371; 204 / 0.453 / 0.490; 173 / 0.551 / 0.590; 173 / 0.653 / 0.636; 238 / 0.746 / 0.748; 71 / 0.818 / 0.873

Full metrics: report.json. Model and data provenance: bundle.json.
