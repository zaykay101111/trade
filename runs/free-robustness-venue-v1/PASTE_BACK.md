# Rolling-season and delayed-data checks

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Expanding training; prior-season tune/calibration; next-season validation. Each delay scenario rebuilds features and refits/tunes/calibrates all models. Extra 0/24/48h means assumed total 24/48/72h availability for this imported dataset. Not a fixed-model outage test or a test of schedule revisions. Seasons have disjoint validation games but overlapping training; not independent trials. 2024-25 was already inspected; these are development robustness checks, not fresh confirmation.

Final holdout: NOT SCORED.

Log loss by season and extra availability delay (lower is better):
- 2022-23, +0h, n=1230: home_rate=0.682937; elo=0.652554; logistic=0.647034; boosted=0.649602
  logistic minus Elo: -0.005520, 95% block interval [-0.011385, 0.000825]
  boosted minus Elo: -0.002952, 95% block interval [-0.013148, 0.007717]
- 2022-23, +24h, n=1230: home_rate=0.682905; elo=0.653223; logistic=0.647629; boosted=0.661858
  logistic minus Elo: -0.005594, 95% block interval [-0.011305, 0.000581]
  boosted minus Elo: 0.008635, 95% block interval [-0.004640, 0.022806]
- 2022-23, +48h, n=1230: home_rate=0.682779; elo=0.653506; logistic=0.648229; boosted=0.658575
  logistic minus Elo: -0.005277, 95% block interval [-0.011256, 0.001403]
  boosted minus Elo: 0.005070, 95% block interval [-0.007897, 0.017544]
- 2023-24, +0h, n=1230: home_rate=0.689805; elo=0.616256; logistic=0.609683; boosted=0.625116
  logistic minus Elo: -0.006573, 95% block interval [-0.014840, 0.001605]
  boosted minus Elo: 0.008860, 95% block interval [-0.003740, 0.020464]
- 2023-24, +24h, n=1230: home_rate=0.689774; elo=0.616516; logistic=0.610368; boosted=0.623316
  logistic minus Elo: -0.006148, 95% block interval [-0.014880, 0.002743]
  boosted minus Elo: 0.006800, 95% block interval [-0.005499, 0.017721]
- 2023-24, +48h, n=1230: home_rate=0.689728; elo=0.616245; logistic=0.611229; boosted=0.624495
  logistic minus Elo: -0.005016, 95% block interval [-0.014164, 0.004421]
  boosted minus Elo: 0.008250, 95% block interval [-0.004291, 0.018838]
- 2024-25, +0h, n=1230: home_rate=0.689695; elo=0.621251; logistic=0.607059; boosted=0.614177
  logistic minus Elo: -0.014192, 95% block interval [-0.022098, -0.005966]
  boosted minus Elo: -0.007074, 95% block interval [-0.014920, 0.000893]
- 2024-25, +24h, n=1230: home_rate=0.689677; elo=0.622766; logistic=0.609192; boosted=0.613607
  logistic minus Elo: -0.013574, 95% block interval [-0.021543, -0.005142]
  boosted minus Elo: -0.009158, 95% block interval [-0.017521, -0.000419]
- 2024-25, +48h, n=1230: home_rate=0.689669; elo=0.623973; logistic=0.610580; boosted=0.614978
  logistic minus Elo: -0.013393, 95% block interval [-0.021345, -0.004996]
  boosted minus Elo: -0.008995, 95% block interval [-0.017209, -0.000249]

Pooled descriptive metrics (no independent-fold significance claim):
- +0h home_rate: n=3690, log loss=0.687479, Brier=0.247170, accuracy=55.58%
- +0h elo: n=3690, log loss=0.630020, Brier=0.220059, accuracy=64.09%
- +0h logistic: n=3690, log loss=0.621258, Brier=0.216074, accuracy=65.26%
- +0h boosted: n=3690, log loss=0.629631, Brier=0.219740, accuracy=64.69%
- +24h home_rate: n=3690, log loss=0.687452, Brier=0.247156, accuracy=55.58%
- +24h elo: n=3690, log loss=0.630835, Brier=0.220390, accuracy=63.98%
- +24h logistic: n=3690, log loss=0.622396, Brier=0.216586, accuracy=65.18%
- +24h boosted: n=3690, log loss=0.632927, Brier=0.221272, accuracy=63.77%
- +48h home_rate: n=3690, log loss=0.687392, Brier=0.247126, accuracy=55.58%
- +48h elo: n=3690, log loss=0.631241, Brier=0.220569, accuracy=64.17%
- +48h logistic: n=3690, log loss=0.623346, Brier=0.217010, accuracy=65.18%
- +48h boosted: n=3690, log loss=0.632683, Brier=0.221129, accuracy=63.88%

Delay sensitivity vs matching no-extra-delay fold:
- 2022-23 +24h logistic: log-loss change=+0.000595; mean |probability change|=0.010793
- 2022-23 +24h boosted: log-loss change=+0.012256; mean |probability change|=0.044149
- 2022-23 +48h logistic: log-loss change=+0.001195; mean |probability change|=0.017510
- 2022-23 +48h boosted: log-loss change=+0.008973; mean |probability change|=0.042826
- 2023-24 +24h logistic: log-loss change=+0.000685; mean |probability change|=0.011001
- 2023-24 +24h boosted: log-loss change=-0.001800; mean |probability change|=0.024285
- 2023-24 +48h logistic: log-loss change=+0.001546; mean |probability change|=0.017143
- 2023-24 +48h boosted: log-loss change=-0.000621; mean |probability change|=0.028223
- 2024-25 +24h logistic: log-loss change=+0.002133; mean |probability change|=0.010527
- 2024-25 +24h boosted: log-loss change=-0.000569; mean |probability change|=0.027710
- 2024-25 +48h logistic: log-loss change=+0.003522; mean |probability change|=0.014714
- 2024-25 +48h boosted: log-loss change=+0.000802; mean |probability change|=0.029296

No automatic pass/fail or final model promotion. Intervals exclude training/selection uncertainty.
Full calibration bins and counts: report.json; each fold contains its models, hashes and predictions.
