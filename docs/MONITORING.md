# Monitoring and copy/paste protocol

## During data preparation

Paste `data/processed/DATA_VERSION/audit.json`. I can inspect eligibility, exclusions, feature version, source hashes and configured books/dates.

Target: all admitted records have valid IDs, timing and contracts; no known leakage. Exclusion counts are part of the result. A high success rate on a tiny selectively surviving subset is not broad coverage.

## During training

Paste the last 60 lines of the job error/output logs plus progress.json if a job fails. Include Slurm state, elapsed time, MaxRSS and exit code. Never delete a failed run to hide its history.

A completed fit gives trials.json, bundle.json, residual.json and progress.json. Check that tune loss curves are finite and that a small subset of configurations was used. No particular training-loss number proves success.

## After validation or final test

Use:

```bash
sports report --path runs/nba-v1/validation
# macOS only, copy to clipboard:
sports report --path runs/nba-v1/validation | pbcopy
```

Paste all of PASTE_BACK.md. It contains:
- Synthetic/historical mode, split, dates and sample sizes.
- Raw market, calibrated market, logistic and residual probability metrics.
- Paired log-loss improvement intervals with time blocks.
- Calibration diagnostics and reliability-bin sample counts.
- Paper yield, turnover, P&L, drawdown and market-only policy comparison.
- Five-minute price observations, worse-odds and top-profit sensitivity.
- Dataset/code hashes, configuration, exclusions and environment versions.

The primary proposed forecast target is a relative log-loss gain >=0.25% with a paired 95% interval above zero. Treat an interval crossing zero as inconclusive. Calibration slope roughly 0.9–1.1 and intercept near zero are coarse diagnostics, not proof of a tiny edge. Small bins need caution.

The economic flag only checks a return interval under the paper assumptions. Require later replication and realistic execution before drawing a profit conclusion. A positive yield concentrated in five outliers or disappearing under small price deterioration needs investigation.

The software currently reports approximate bootstrap intervals, not corrections for every strategy you may have tried. Keep an experiment log and identify reused test periods.

## Start prospective paper operation

First arrange a fresh-data workflow that produces the same schemas and keeps true local availability/ingestion times. Copy the trained config into a prospective build config, changing only `mode` to `prospective`. Keep the same feature and book definitions. Capture results only after they are observed. Each new feature snapshot goes into a new directory.

The scaffold does not yet contain an unattended live feed scheduler or vendor-specific live schedule resolver. The historical downloader is not a live collector. Until that collector is connected and audited, paper commands are available but you must supply the fresh canonical snapshots.

At the declared cutoff, build and issue:

```bash
sports build --data data/normalized/live-snapshot --config configs/prospective.json --out data/processed/live-snapshot
sports paper-issue --run runs/nba-v1 --dataset data/processed/live-snapshot --ledger runs/paper-v1.sqlite
```

This requires a frozen non-synthetic model, prospective provenance, matching feature contract and a decision within the current ten-minute window. It transactionally prevents duplicate game issuance and enforces paper exposure limits. It records no-bet decisions too. The ten-minute window is an initial operational assumption; quotes can expire sooner under the quote-age limit.

To view newly issued decisions with game IDs, books, minimum prices and stakes, use a SQLite viewer on the ledger's decisions table, or:

```bash
python scripts/show_paper.py --ledger runs/paper-v1.sqlite
```

For each positive-stake candidate, manually check the same book and contract immediately:

```bash
sports paper-check --ledger runs/paper-v1.sqlite --game NBA_GAME_ID --available --price 1.95
# If unavailable:
sports paper-check --ledger runs/paper-v1.sqlite --game NBA_GAME_ID
```

The first recorded check determines the timely-availability statistic. Late checks count as failures; unchecked candidates remain visible. Check timestamps are generated now to prevent casual backdating. These checks do not place or accept real wagers.

After verifying the official result, record win/loss for the **selected side**, or void according to the contract:

```bash
sports paper-settle --ledger runs/paper-v1.sqlite --game NBA_GAME_ID --outcome win
sports monitor --ledger runs/paper-v1.sqlite --out runs/monitor-YYYY-MM-DD
sports report --path runs/monitor-YYYY-MM-DD
```

Settlement is manual and duplicate settlement is rejected. Correcting an entered settlement requires a future explicit correction workflow; preserve the error and ask for a reviewed correction rather than editing history. A void refunds the paper stake and extra cost under this release's declared assumption.

Paper P&L uses the original displayed price, even when the later check fails. Always interpret it together with check coverage and availability; it is not executable P&L.

## Review cadence and action rules

Daily: data freshness, mapping failures, missing books, expiry, duplicate protection and settlement reconciliation. Pause new issuance on known integrity failures.

Weekly: quote-check coverage, timely price availability, candidate volume, missing-data patterns and open positions. Proposed operational goals: >=99% scheduled jobs completed and >=90% checked alerts still meeting the price floor. The current ledger measures price checks; scheduler uptime requires the future collector's logs.

Monthly on predeclared dates: forecasting metrics, selected-bet calibration, yield intervals and model/market comparisons. Do not tune after each losing streak or keep testing significance until it turns positive.

After >=90 days and >=300 settled candidates: assess operational readiness. This alone does not establish a small financial edge. For illustration, independent constant-price bets at -110 with a true 55% win chance require roughly 2,848 bets for 80% power against break-even in a two-sided 5% normal approximation. Your variable prices and dependence require their own analysis.

Paste each dated report here along with changes made since the previous report. I can then distinguish software/data problems, uncertain evidence, and justified next experiments.

