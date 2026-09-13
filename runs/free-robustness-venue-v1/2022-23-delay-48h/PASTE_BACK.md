# Odds-free validation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Final holdout: NOT SCORED.
Coverage: {'total_games': 7230, 'development_games': 3540, 'unscored_games_at_or_after_2025_07_01': 1230}
Splits: {'train': 1080, 'tune': 498, 'calibration': 707, 'validation': 1230}
Exclusive UTC boundaries: {'train': '2021-07-01', 'tune': '2022-01-01', 'calibration': '2022-07-01', 'validation': '2023-07-01'}
Extra result-availability delay: 48 hours (added to imported availability).
Labels excluded at fitting cutoffs: 25

Validation metrics (lower log loss/Brier is better):
- home_rate: log loss=0.682779; Brier=0.244827; accuracy=58.05%
- elo: log loss=0.653506; Brier=0.229799; accuracy=62.11%
- logistic: log loss=0.648229; Brier=0.227771; accuracy=62.28%
- boosted: log loss=0.658575; Brier=0.232909; accuracy=61.87%
- logistic_raw: log loss=0.648941; Brier=0.228246; accuracy=62.60%
- boosted_raw: log loss=0.655217; Brier=0.231516; accuracy=61.95%

Paired log-loss difference vs Elo (negative favors challenger):
- logistic: -0.005277; 95% block interval [-0.011256, 0.001403]
- boosted: 0.005070; 95% block interval [-0.007897, 0.017544]
Intervals exclude training/selection uncertainty.

Monthly validation log loss:
- 2022-10, n=100: home_rate=0.6757; elo=0.6464; logistic=0.6521; boosted=0.6272
- 2022-11, n=216: home_rate=0.6773; elo=0.6600; logistic=0.6558; boosted=0.6677
- 2022-12, n=226: home_rate=0.6774; elo=0.6866; logistic=0.6818; boosted=0.6779
- 2023-01, n=223: home_rate=0.6863; elo=0.6557; logistic=0.6516; boosted=0.6664
- 2023-02, n=160: home_rate=0.6782; elo=0.5904; logistic=0.5987; boosted=0.6288
- 2023-03, n=232: home_rate=0.6940; elo=0.6522; logistic=0.6349; boosted=0.6591
- 2023-04, n=73: home_rate=0.6886; elo=0.6774; logistic=0.6572; boosted=0.6546

Calibration bins: count / mean predicted / observed home-win rate
- elo: 14 / 0.169 / 0.500; 69 / 0.261 / 0.319; 114 / 0.354 / 0.377; 201 / 0.454 / 0.507; 237 / 0.553 / 0.561; 266 / 0.651 / 0.613; 196 / 0.746 / 0.714; 121 / 0.840 / 0.793; 12 / 0.911 / 0.667
- logistic: 15 / 0.173 / 0.400; 77 / 0.262 / 0.338; 136 / 0.357 / 0.368; 230 / 0.454 / 0.526; 287 / 0.548 / 0.561; 254 / 0.648 / 0.701; 165 / 0.743 / 0.721; 63 / 0.833 / 0.794; 3 / 0.909 / 1.000
- boosted: 143 / 0.268 / 0.371; 135 / 0.355 / 0.481; 223 / 0.452 / 0.489; 206 / 0.554 / 0.583; 193 / 0.651 / 0.679; 304 / 0.751 / 0.711; 26 / 0.808 / 0.769

Full metrics: report.json. Model and data provenance: bundle.json.
