# Logistic feature-ablation report

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Seven fixed logistic variants across three chronological development seasons. Remove one group at a time, refit scaler/coefficients and sigmoid calibration. Imported availability is unchanged (assumed +24h); no additional delay. Positive ablated-minus-full log-loss difference favors keeping the group. These are previously inspected development seasons; intervals are descriptive, not corrected for multiple comparisons and exclude training/selection uncertainty. Folds share training history; pooled metrics are descriptive. No automatic feature removal. Scoring columns are removed together because margin=scored-allowed. This measures conditional predictive contribution, not causal importance. Removing neutral removes only the direct input, not venue effects embedded in historical Elo.

Final holdout: NOT SCORED.

Pooled development results (3,690 games for complete NBA input):
- full: n=3690; log loss=0.620546; Brier=0.215840; change vs full=+0.000000; removal hurts in 0/3 seasons
- without_scoring: n=3690; log loss=0.623491; Brier=0.217249; change vs full=+0.002944; removal hurts in 3/3 seasons
- without_recent_wins: n=3690; log loss=0.620789; Brier=0.215967; change vs full=+0.000243; removal hurts in 3/3 seasons
- without_history_count: n=3690; log loss=0.620616; Brier=0.215871; change vs full=+0.000070; removal hurts in 1/3 seasons
- without_rest: n=3690; log loss=0.624398; Brier=0.217670; change vs full=+0.003851; removal hurts in 3/3 seasons
- without_elo: n=3690; log loss=0.627767; Brier=0.219032; change vs full=+0.007221; removal hurts in 3/3 seasons
- without_neutral: n=3690; log loss=0.620546; Brier=0.215840; change vs full=+0.000000; removal hurts in 2/3 seasons

Per-season ablated-minus-full log-loss differences; positive favors keeping group:
- 2022-23: constant training inputs=['neutral']
  without_scoring: +0.000424; 95% weekly-block interval [-0.002791, +0.003549]; raw change=+0.001443
  without_recent_wins: +0.000026; 95% weekly-block interval [-0.000503, +0.000484]; raw change=+0.000087
  without_history_count: +0.000222; 95% weekly-block interval [-0.000152, +0.000598]; raw change=+0.000222
  without_rest: +0.004550; 95% weekly-block interval [+0.000161, +0.008590]; raw change=+0.003562
  without_elo: +0.006304; 95% weekly-block interval [-0.001229, +0.013039]; raw change=+0.005466
  without_neutral: +0.000000; 95% weekly-block interval [-0.000000, +0.000000]; raw change=+0.000000
- 2023-24: constant training inputs=['neutral']
  without_scoring: +0.002493; 95% weekly-block interval [-0.001540, +0.005762]; raw change=+0.002711
  without_recent_wins: +0.000349; 95% weekly-block interval [-0.000432, +0.001117]; raw change=+0.000363
  without_history_count: -0.000000; 95% weekly-block interval [-0.000232, +0.000267]; raw change=-0.000115
  without_rest: +0.003389; 95% weekly-block interval [-0.001259, +0.007754]; raw change=+0.003003
  without_elo: +0.010141; 95% weekly-block interval [+0.002256, +0.017515]; raw change=+0.012314
  without_neutral: +0.000000; 95% weekly-block interval [-0.000000, +0.000000]; raw change=+0.000000
- 2024-25: constant training inputs=['neutral']
  without_scoring: +0.005917; 95% weekly-block interval [+0.001801, +0.009640]; raw change=+0.006099
  without_recent_wins: +0.000353; 95% weekly-block interval [-0.000260, +0.000891]; raw change=+0.000359
  without_history_count: -0.000013; 95% weekly-block interval [-0.000129, +0.000082]; raw change=-0.000057
  without_rest: +0.003615; 95% weekly-block interval [-0.000032, +0.006623]; raw change=+0.003642
  without_elo: +0.005217; 95% weekly-block interval [-0.000270, +0.010483]; raw change=+0.007137
  without_neutral: -0.000000; 95% weekly-block interval [-0.000000, +0.000000]; raw change=+0.000000

Do not treat an interval containing zero as proof of no contribution.
No combined subset is selected or tested by this command. Each child saves a refitted model and predictions.
