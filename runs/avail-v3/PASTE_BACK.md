# Declared-availability feature comparison

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Base eleven features versus status-count differences, both-usable coverage, and per-side missing/stale/not-submitted/invalid indicators on existing development folds. Reports match Eastern game date, away/home matchup, and team before timestamp selection. Latest nominal report time must strictly precede cutoff; age above 48 hours is stale. Only usable snapshots contribute player-status counts. No fallback to other games. Duplicate-player or multiple-source snapshots are invalid. Actual absence is never substituted for a declared status. Counts are unweighted: no player-impact or minutes data is available, so every listed player counts the same. Reports were BACKFILLED, which supports development but cannot establish what was visible before a past game. These folds have been inspected repeatedly; this is not confirmation.

Reports parsed: 1215 (99904 rows). Game coverage: 93.2%. Unmapped team rows: 16.
Coverage means both teams usable. States: {'home': {'usable': 5738, 'not_submitted': 227, 'missing': 35}, 'away': {'usable': 5726, 'not_submitted': 243, 'missing': 31}}
Rejected rows: 16. See selected_reports.csv and rejected_report_rows.csv.

Per-fold calibrated log loss (lower is better):
- 2022-23, n=1230, coverage=93.0%: base=0.647034; extended=0.642964
  extended minus base: -0.004070; 95% block interval [-0.011550, +0.002945]  (includes zero)
- 2023-24, n=1230, coverage=93.2%: base=0.609683; extended=0.606161
  extended minus base: -0.003522; 95% block interval [-0.009517, +0.003007]  (includes zero)
- 2024-25, n=1230, coverage=93.8%: base=0.607059; extended=0.602443
  extended minus base: -0.004616; 95% block interval [-0.010908, +0.001097]  (includes zero)

Pooled descriptive metrics:
- base: n=3690; log loss=0.621258; Brier=0.216074; accuracy=65.26%
- extended: n=3690; log loss=0.617189; Brier=0.214239; accuracy=65.88%
- pooled extended minus base: -0.004069

Negative favors availability features. Unweighted counts ignore player impact,
so a null result here does not show that availability is uninformative, only that
counts of listed players are. Backfilled reports cannot support a claim about what
was obtainable before a past game. No feature set is promoted by this command.
