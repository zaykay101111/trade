# External-era replication: Walsh & Joshi era 2014-15..2018-19

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Frozen candidate recipe applied to Walsh & Joshi era 2014-15..2018-19. Same eleven features, lambda 0.01, sigmoid calibration, fixed Elo, constant home rate and secondary boosted trees as the 2020-2026 work. Elo starts at 1500 with no prior history, so the first season of any era is a burn-in period. These seasons were never used to design the recipe, but this is a retrospective comparison across a different era, not a prospective test; era differences in pace, scoring and home advantage are real.

Data span: 2014-10-28 23:00:00+00:00 to 2019-04-11 01:30:00+00:00
Era boundaries (exclusive UTC): {'start': '2014-07-01', 'train': '2017-07-01', 'tune': '2018-01-01', 'calibration': '2018-07-01', 'evaluation': '2019-07-01'}
Split counts: {'train': 3690, 'tune': 529, 'calibration': 687, 'evaluation': 1230}
Refit games: 4219

Evaluation-season metrics (lower log loss/Brier better; ECE for comparability only):
- home_rate: log loss=0.676087; Brier=0.241516; accuracy=59.27%; ECE=0.0103; classwise-ECE=0.0103
- elo: log loss=0.620843; Brier=0.215670; accuracy=65.69%; ECE=0.0391; classwise-ECE=0.0391
- logistic: log loss=0.618900; Brier=0.214425; accuracy=65.20%; ECE=0.0523; classwise-ECE=0.0523
- boosted: log loss=0.620616; Brier=0.215332; accuracy=64.72%; ECE=0.0481; classwise-ECE=0.0481
- logistic_raw: log loss=0.614883; Brier=0.212967; accuracy=66.18%; ECE=0.0470; classwise-ECE=0.0470
- boosted_raw: log loss=0.617214; Brier=0.214060; accuracy=65.12%; ECE=0.0402; classwise-ECE=0.0402

Paired log-loss differences (negative favors the first model):
- logistic minus elo: -0.001943; 95% block interval [-0.009094, +0.005335]
- boosted minus elo: -0.000228; 95% block interval [-0.008546, +0.007300]
- elo minus home_rate: -0.055243; 95% block interval [-0.082696, -0.027060]
- logistic minus home_rate: -0.057186; 95% block interval [-0.085804, -0.028518]
- boosted minus home_rate: -0.055471; 95% block interval [-0.084281, -0.027035]

Reliability bins: count / mean predicted / observed
- elo: 28 / 0.165 / 0.214; 101 / 0.253 / 0.327; 132 / 0.355 / 0.409; 180 / 0.450 / 0.489; 199 / 0.554 / 0.548; 202 / 0.651 / 0.693; 209 / 0.748 / 0.713; 160 / 0.847 / 0.831; 19 / 0.915 / 0.895
- logistic: 3 / 0.085 / 0.333; 42 / 0.166 / 0.167; 101 / 0.253 / 0.356; 140 / 0.350 / 0.357; 169 / 0.454 / 0.574; 190 / 0.552 / 0.532; 194 / 0.648 / 0.686; 192 / 0.748 / 0.755; 166 / 0.848 / 0.783; 33 / 0.917 / 0.879
- boosted: 19 / 0.186 / 0.158; 120 / 0.247 / 0.317; 153 / 0.348 / 0.412; 215 / 0.460 / 0.540; 95 / 0.539 / 0.484; 227 / 0.658 / 0.670; 189 / 0.736 / 0.741; 179 / 0.845 / 0.793; 33 / 0.909 / 0.879

Monthly log loss:
- 2018-10, n=107: home_rate=0.6650; elo=0.6229; logistic=0.6318; boosted=0.6421
- 2018-11, n=216: home_rate=0.6746; elo=0.6637; logistic=0.6567; boosted=0.6633
- 2018-12, n=222: home_rate=0.6680; elo=0.6436; logistic=0.6396; boosted=0.6375
- 2019-01, n=220: home_rate=0.6797; elo=0.5570; logistic=0.5550; boosted=0.5486
- 2019-02, n=159: home_rate=0.6849; elo=0.6256; logistic=0.6183; boosted=0.6280
- 2019-03, n=226: home_rate=0.6760; elo=0.6218; logistic=0.6165; boosted=0.6180
- 2019-04, n=80: home_rate=0.6903; elo=0.6022; logistic=0.6258; boosted=0.6204

No odds, stake sizing, ROI or profitability is computed here. Accuracy and ECE
are reported for comparison with published work only; selection in this project
uses log loss, a strictly proper scoring rule that already penalizes miscalibration.
A different era is not an independent replication of the 2020-2026 result: team
quality, pace and home advantage differ, and Elo needs a burn-in season.
