# Declared-availability feature comparison

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Base eleven features versus the same set plus five declared-availability differentials and a coverage indicator, on the three existing development folds. For each game the latest report whose own timestamp precedes the decision cutoff is used; a report published after the cutoff is never read, and actual absence is never substituted for a declared status. Counts are unweighted: no player-impact or minutes data is available, so every listed player counts the same. Reports were BACKFILLED, which supports development but cannot establish what was visible before a past game. These folds have been inspected repeatedly; this is not confirmation.

Reports parsed: 1215 (81605 rows). Game coverage: 100.0%. Unmapped team rows: 30.

Per-fold calibrated log loss (lower is better):
- 2022-23, n=1230, coverage=100.0%: base=0.647034; extended=0.645995
  extended minus base: -0.001039; 95% block interval [-0.006737, +0.004445]  (includes zero)
- 2023-24, n=1230, coverage=100.0%: base=0.609683; extended=0.604408
  extended minus base: -0.005275; 95% block interval [-0.008974, -0.001812]  (excludes zero)
- 2024-25, n=1230, coverage=100.0%: base=0.607059; extended=0.606204
  extended minus base: -0.000855; 95% block interval [-0.005218, +0.003702]  (includes zero)

Pooled descriptive metrics:
- base: n=3690; log loss=0.621258; Brier=0.216074; accuracy=65.26%
- extended: n=3690; log loss=0.618869; Brier=0.215112; accuracy=65.72%
- pooled extended minus base: -0.002390

Negative favors availability features. Unweighted counts ignore player impact,
so a null result here does not show that availability is uninformative, only that
counts of listed players are. Backfilled reports cannot support a claim about what
was obtainable before a past game. No feature set is promoted by this command.
