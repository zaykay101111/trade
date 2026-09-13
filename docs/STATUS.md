# Scope and implementation status

## Implemented

- Canonical CSV contracts and audited event-map adapter.
- Bounded historical odds request planner/downloader; no API calls on import.
- Optional NBA team-log download script and results adapter.
- As-of feature building, paired de-vigged reference, separate execution books.
- A twelve-feature reduced first model with XGBoost residual and logistic comparator.
- Chronological tune selection, refit and separate calibration.
- Raw/recalibrated market comparisons, Brier/log loss, calibration and time-block intervals.
- Paper policy with price floor, haircut, exact cost-adjusted Kelly and exposure constraints.
- Five-minute same-book snapshot stress when observations exist, worse-price and profit-outlier tests.
- Immutable-by-convention run folders, source/data hashes, model freeze and one-use final-test marker.
- Transactional prospective paper issuance, manual price checks/settlement, pasteable monitoring.
- CPU Slurm templates and documented Hellbender workflow.
- Automated integrity tests and a complete synthetic smoke run.

## Not claimed or not yet connected

No real dataset, fitted NBA model, proven edge, subscription purchase, cluster login, Slurm submission or accepted wager is included.

Schedules and cross-vendor event mapping require audited source preparation. Generic normalized adapters cannot certify historical availability. The NBA convenience results adapter uses an explicit 24-hour delay assumption; actual revisions and delayed games require verification.

The core omits injuries, player metrics, possession-adjusted efficiency, travel and referees. The optional datasets in DATASETS.md are a roadmap for new feature versions. This release uses one fixed probability haircut, not a learned probability-uncertainty distribution.

There is no unattended live collector, scheduler, automatic official-result reconciler, exchange commission engine, sportsbook balance integration, learned portfolio optimizer, or automatic real wagering. The prospective ledger is a manual paper operations scaffold once fresh normalized data is supplied.

The final-test marker and hashes prevent accidental local reuse/modification, not deliberate experimentation in other folders. Report every research trial. Loading the full feature file during evaluation does not create extra independent samples.

Historical quote snapshots do not prove that a specific account could obtain a price or stake. Missing later observations remain unknown. Synthetic results are explicitly barred from passing evidence gates.

## Next concrete milestone

Download and normalize an audited 100-game sample, inspect its exclusions, verify book coverage and schedule/result timing, and paste audit.json here. Then procure the full archive and run the first real development evaluation.

