# Rolling-season and delayed-data checks

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Expanding training; prior-season tune/calibration; next-season validation. Each delay scenario rebuilds features and refits/tunes/calibrates all models. Extra 0/24/48h means assumed total 24/48/72h availability for this imported dataset. Not a fixed-model outage test or a test of schedule revisions. Seasons have disjoint validation games but overlapping training; not independent trials. 2024-25 was already inspected; these are development robustness checks, not fresh confirmation.

Final holdout: NOT SCORED.

Log loss by season and extra availability delay (lower is better):
- 2022-23, +0h, n=1230: home_rate=0.682937; elo=0.652719; logistic=0.647001; boosted=0.649647
  logistic minus Elo: -0.005718, 95% block interval [-0.011434, 0.000493]
  boosted minus Elo: -0.003072, 95% block interval [-0.013164, 0.007600]
- 2022-23, +24h, n=1230: home_rate=0.682905; elo=0.653390; logistic=0.647595; boosted=0.661945
  logistic minus Elo: -0.005794, 95% block interval [-0.011503, 0.000371]
  boosted minus Elo: 0.008555, 95% block interval [-0.004833, 0.022775]
- 2022-23, +48h, n=1230: home_rate=0.682779; elo=0.653676; logistic=0.648187; boosted=0.658537
  logistic minus Elo: -0.005489, 95% block interval [-0.011461, 0.001116]
  boosted minus Elo: 0.004861, 95% block interval [-0.008098, 0.017321]
- 2023-24, +0h, n=1230: home_rate=0.689805; elo=0.616441; logistic=0.607681; boosted=0.625436
  logistic minus Elo: -0.008760, 95% block interval [-0.015762, -0.001775]
  boosted minus Elo: 0.008994, 95% block interval [-0.003584, 0.020559]
- 2023-24, +24h, n=1230: home_rate=0.689774; elo=0.616687; logistic=0.608185; boosted=0.623367
  logistic minus Elo: -0.008503, 95% block interval [-0.016282, -0.000803]
  boosted minus Elo: 0.006680, 95% block interval [-0.005666, 0.017610]
- 2023-24, +48h, n=1230: home_rate=0.689728; elo=0.616425; logistic=0.608999; boosted=0.624562
  logistic minus Elo: -0.007426, 95% block interval [-0.015526, 0.000507]
  boosted minus Elo: 0.008137, 95% block interval [-0.004520, 0.018697]
- 2024-25, +0h, n=1230: home_rate=0.689695; elo=0.621281; logistic=0.606957; boosted=0.613644
  logistic minus Elo: -0.014324, 95% block interval [-0.021765, -0.006246]
  boosted minus Elo: -0.007637, 95% block interval [-0.015533, 0.000475]
- 2024-25, +24h, n=1230: home_rate=0.689677; elo=0.622797; logistic=0.609073; boosted=0.614085
  logistic minus Elo: -0.013724, 95% block interval [-0.021333, -0.005609]
  boosted minus Elo: -0.008712, 95% block interval [-0.017489, -0.000089]
- 2024-25, +48h, n=1230: home_rate=0.689669; elo=0.624004; logistic=0.610483; boosted=0.614834
  logistic minus Elo: -0.013521, 95% block interval [-0.021156, -0.005367]
  boosted minus Elo: -0.009170, 95% block interval [-0.017481, -0.000566]

Pooled descriptive metrics (no independent-fold significance claim):
- +0h home_rate: n=3690, log loss=0.687479, Brier=0.247170, accuracy=55.58%
- +0h elo: n=3690, log loss=0.630147, Brier=0.220109, accuracy=64.01%
- +0h logistic: n=3690, log loss=0.620546, Brier=0.215840, accuracy=65.28%
- +0h boosted: n=3690, log loss=0.629575, Brier=0.219711, accuracy=64.93%
- +24h home_rate: n=3690, log loss=0.687452, Brier=0.247156, accuracy=55.58%
- +24h elo: n=3690, log loss=0.630958, Brier=0.220438, accuracy=63.96%
- +24h logistic: n=3690, log loss=0.621618, Brier=0.216334, accuracy=65.23%
- +24h boosted: n=3690, log loss=0.633132, Brier=0.221371, accuracy=63.77%
- +48h home_rate: n=3690, log loss=0.687392, Brier=0.247126, accuracy=55.58%
- +48h elo: n=3690, log loss=0.631369, Brier=0.220619, accuracy=64.12%
- +48h logistic: n=3690, log loss=0.622556, Brier=0.216755, accuracy=65.15%
- +48h boosted: n=3690, log loss=0.632645, Brier=0.221114, accuracy=63.88%

Delay sensitivity vs matching no-extra-delay fold:
- 2022-23 +24h logistic: log-loss change=+0.000594; mean |probability change|=0.010791
- 2022-23 +24h boosted: log-loss change=+0.012298; mean |probability change|=0.044041
- 2022-23 +48h logistic: log-loss change=+0.001186; mean |probability change|=0.017507
- 2022-23 +48h boosted: log-loss change=+0.008890; mean |probability change|=0.042771
- 2023-24 +24h logistic: log-loss change=+0.000503; mean |probability change|=0.011037
- 2023-24 +24h boosted: log-loss change=-0.002068; mean |probability change|=0.024300
- 2023-24 +48h logistic: log-loss change=+0.001318; mean |probability change|=0.017176
- 2023-24 +48h boosted: log-loss change=-0.000873; mean |probability change|=0.028108
- 2024-25 +24h logistic: log-loss change=+0.002116; mean |probability change|=0.010604
- 2024-25 +24h boosted: log-loss change=+0.000441; mean |probability change|=0.027181
- 2024-25 +48h logistic: log-loss change=+0.003527; mean |probability change|=0.014830
- 2024-25 +48h boosted: log-loss change=+0.001190; mean |probability change|=0.029027

No automatic pass/fail or final model promotion. Intervals exclude training/selection uncertainty.
Full calibration bins and counts: report.json; each fold contains its models, hashes and predictions.
