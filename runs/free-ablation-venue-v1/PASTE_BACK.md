# Logistic feature-ablation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Seven fixed logistic variants across three chronological development seasons. Remove one group at a time, refit scaler/coefficients and sigmoid calibration. Imported availability is unchanged (assumed +24h); no additional delay. Positive ablated-minus-full log-loss difference favors keeping the group. These are previously inspected development seasons; intervals are descriptive, not corrected for multiple comparisons and exclude training/selection uncertainty. Folds share training history; pooled metrics are descriptive. No automatic feature removal. Scoring columns are removed together because margin=scored-allowed. This measures conditional predictive contribution, not causal importance. Removing neutral removes only the direct input, not venue effects embedded in historical Elo.

Final holdout: NOT SCORED.

Pooled development results (3,690 games for complete NBA input):
- full: n=3690; log loss=0.621258; Brier=0.216074; change vs full=+0.000000; removal hurts in 0/3 seasons
- without_scoring: n=3690; log loss=0.624152; Brier=0.217476; change vs full=+0.002893; removal hurts in 3/3 seasons
- without_recent_wins: n=3690; log loss=0.621483; Brier=0.216202; change vs full=+0.000225; removal hurts in 3/3 seasons
- without_history_count: n=3690; log loss=0.621310; Brier=0.216102; change vs full=+0.000051; removal hurts in 1/3 seasons
- without_rest: n=3690; log loss=0.625049; Brier=0.217894; change vs full=+0.003790; removal hurts in 3/3 seasons
- without_elo: n=3690; log loss=0.628673; Brier=0.219325; change vs full=+0.007415; removal hurts in 3/3 seasons
- without_neutral: n=3690; log loss=0.620545; Brier=0.215839; change vs full=-0.000713; removal hurts in 1/3 seasons

Per-season ablated-minus-full log-loss differences; positive favors keeping group:
- 2022-23: constant training inputs=['neutral']
  without_scoring: +0.000427; 95% weekly-block interval [-0.002788, +0.003553]; raw change=+0.001446
  without_recent_wins: +0.000025; 95% weekly-block interval [-0.000503, +0.000482]; raw change=+0.000086
  without_history_count: +0.000221; 95% weekly-block interval [-0.000152, +0.000596]; raw change=+0.000221
  without_rest: +0.004548; 95% weekly-block interval [+0.000155, +0.008588]; raw change=+0.003560
  without_elo: +0.006272; 95% weekly-block interval [-0.001240, +0.013014]; raw change=+0.005432
  without_neutral: +0.000000; 95% weekly-block interval [-0.000000, +0.000000]; raw change=+0.000000
- 2023-24: constant training inputs=[]
  without_scoring: +0.002211; 95% weekly-block interval [-0.001825, +0.005568]; raw change=+0.002545
  without_recent_wins: +0.000288; 95% weekly-block interval [-0.000555, +0.001073]; raw change=+0.000337
  without_history_count: -0.000054; 95% weekly-block interval [-0.000298, +0.000224]; raw change=-0.000135
  without_rest: +0.003185; 95% weekly-block interval [-0.001382, +0.007626]; raw change=+0.002913
  without_elo: +0.010713; 95% weekly-block interval [+0.003137, +0.018040]; raw change=+0.012542
  without_neutral: -0.002023; 95% weekly-block interval [-0.005982, +0.000918]; raw change=-0.001435
- 2024-25: constant training inputs=[]
  without_scoring: +0.006042; 95% weekly-block interval [+0.001948, +0.009821]; raw change=+0.006167
  without_recent_wins: +0.000361; 95% weekly-block interval [-0.000241, +0.000892]; raw change=+0.000365
  without_history_count: -0.000013; 95% weekly-block interval [-0.000129, +0.000083]; raw change=-0.000055
  without_rest: +0.003638; 95% weekly-block interval [+0.000046, +0.006656]; raw change=+0.003663
  without_elo: +0.005260; 95% weekly-block interval [-0.000193, +0.010472]; raw change=+0.007140
  without_neutral: -0.000117; 95% weekly-block interval [-0.003447, +0.002528]; raw change=+0.000025

Do not treat an interval containing zero as proof of no contribution.
No combined subset is selected or tested by this command. Each child saves a refitted model and predictions.
