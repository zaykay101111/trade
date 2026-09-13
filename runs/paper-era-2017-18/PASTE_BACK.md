# External-era replication: paper test season 2017-18

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Frozen candidate recipe applied to paper test season 2017-18. Same eleven features, lambda 0.01, sigmoid calibration, fixed Elo, constant home rate and secondary boosted trees as the 2020-2026 work. Elo starts at 1500 with no prior history, so the first season of any era is a burn-in period. These seasons were never used to design the recipe, but this is a retrospective comparison across a different era, not a prospective test; era differences in pace, scoring and home advantage are real.

Data span: 2014-10-28 23:00:00+00:00 to 2019-04-11 01:30:00+00:00
Era boundaries (exclusive UTC): {'start': '2014-07-01', 'train': '2016-07-01', 'tune': '2017-01-01', 'calibration': '2017-07-01', 'evaluation': '2018-07-01'}
Split counts: {'train': 2460, 'tune': 491, 'calibration': 727, 'evaluation': 1230}
Refit games: 2951

Evaluation-season metrics (lower log loss/Brier better; ECE for comparability only):
- home_rate: log loss=0.680657; Brier=0.243781; accuracy=57.89%; ECE=0.0006; classwise-ECE=0.0006
- elo: log loss=0.620445; Brier=0.215560; accuracy=65.28%; ECE=0.0335; classwise-ECE=0.0335
- logistic: log loss=0.621833; Brier=0.216284; accuracy=64.96%; ECE=0.0335; classwise-ECE=0.0335
- boosted: log loss=0.627116; Brier=0.218531; accuracy=65.28%; ECE=0.0540; classwise-ECE=0.0540
- logistic_raw: log loss=0.621066; Brier=0.215985; accuracy=65.85%; ECE=0.0422; classwise-ECE=0.0422
- boosted_raw: log loss=0.627289; Brier=0.218687; accuracy=64.63%; ECE=0.0540; classwise-ECE=0.0540

Paired log-loss differences (negative favors the first model):
- logistic minus elo: +0.001388; 95% block interval [-0.008039, +0.010367]
- boosted minus elo: +0.006671; 95% block interval [-0.005043, +0.017435]
- elo minus home_rate: -0.060213; 95% block interval [-0.089320, -0.028334]
- logistic minus home_rate: -0.058824; 95% block interval [-0.080586, -0.036024]
- boosted minus home_rate: -0.053542; 95% block interval [-0.074215, -0.031492]

Reliability bins: count / mean predicted / observed
- elo: 27 / 0.163 / 0.111; 73 / 0.256 / 0.274; 146 / 0.350 / 0.377; 171 / 0.448 / 0.497; 208 / 0.551 / 0.572; 226 / 0.647 / 0.619; 205 / 0.748 / 0.717; 148 / 0.842 / 0.824; 26 / 0.923 / 0.808
- logistic: 1 / 0.193 / 0.000; 27 / 0.260 / 0.074; 105 / 0.354 / 0.286; 204 / 0.452 / 0.456; 278 / 0.552 / 0.543; 294 / 0.650 / 0.633; 227 / 0.750 / 0.753; 90 / 0.838 / 0.844; 4 / 0.914 / 0.750
- boosted: 17 / 0.286 / 0.176; 138 / 0.360 / 0.268; 210 / 0.453 / 0.462; 201 / 0.529 / 0.552; 349 / 0.653 / 0.622; 230 / 0.747 / 0.761; 85 / 0.834 / 0.847

Monthly log loss:
- 2017-10, n=103: home_rate=0.6919; elo=0.7069; logistic=0.6859; boosted=0.6776
- 2017-11, n=211: home_rate=0.6778; elo=0.6334; logistic=0.6397; boosted=0.6464
- 2017-12, n=229: home_rate=0.6758; elo=0.6373; logistic=0.6335; boosted=0.6407
- 2018-01, n=214: home_rate=0.6745; elo=0.6333; logistic=0.6380; boosted=0.6381
- 2018-02, n=158: home_rate=0.6856; elo=0.5593; logistic=0.5812; boosted=0.5844
- 2018-03, n=226: home_rate=0.6861; elo=0.5612; logistic=0.5679; boosted=0.5784
- 2018-04, n=89: home_rate=0.6789; elo=0.6744; logistic=0.6456; boosted=0.6613

No odds, stake sizing, ROI or profitability is computed here. Accuracy and ECE
are reported for comparison with published work only; selection in this project
uses log loss, a strictly proper scoring rule that already penalizes miscalibration.
A different era is not an independent replication of the 2020-2026 result: team
quality, pace and home advantage differ, and Elo needs a burn-in season.
