# Start here

## What has been built

The first usable implementation is a deliberately reduced core: time-valid odds, verified schedules, and lagged final team results. Its twelve features describe recent scoring/margins, rest, history, and market dispersion/age. This is sufficient to test the research machinery while injury archives are sourced. Possession-adjusted efficiency, travel, players and injuries are not silently approximated; they are subsequent feature releases.

A fixed two-percentage-point probability haircut is currently the conservative policy. It is explicitly a sensitivity rule, not a learned uncertainty model or confidence interval.

## Your immediate sequence

1. Read DATASETS.md. Obtain a small 100-game sample before a multi-season odds subscription/backfill.
2. Prepare canonical `games.csv` and the audited `event_map.csv`. Match NBA game IDs and provider event IDs; preserve leading zeros.
3. Download historical NBA team results and odds snapshots. Keep the original files.
4. Normalize them into the three required CSVs: `games.csv`, `results.csv`, `odds.csv`.
5. Edit the reference/execution book lists and temporal boundaries in a copied configuration. Coverage of the example books is not guaranteed.
6. Run the audit/build command. Paste the audit here before expensive research runs.
7. Run training plus validation locally or on Hellbender. Paste `PASTE_BACK.md`.
8. Freeze the chosen experiment and run the final test once after the development review.
9. Start prospective paper collection only when the historical research and live data preparation justify it.

## Local commands

```bash
cd "/Users/kylerzook2005/Documents/Personal Projects/Sports Betting Method"
source .venv/bin/activate

sports build --data data/normalized/nba-v1 --config configs/first_model.json --out data/processed/nba-v1
sports report --path data/processed/nba-v1/audit.json
sports train --dataset data/processed/nba-v1 --config configs/first_model.json --out runs/nba-v1
sports evaluate --run runs/nba-v1 --dataset data/processed/nba-v1 --split validation
sports report --path runs/nba-v1/validation
```

The directories are examples; use new names for new research versions. Commands reject overwriting an existing run or dataset. No real data directory is supplied under those example names.

To copy a report on your Mac:

```bash
sports report --path runs/nba-v1/validation | pbcopy
```

Paste the entire file here and say whether you changed any data source, feature, configuration, or policy since the prior report. It includes hashes, software versions, sample sizes, baselines, calibration, yield, uncertainty, stress tests and exclusions.

## What still requires your information

Data provider access and downloads; audited game mappings and schedule revisions; which sportsbooks are accessible to you; and your Hellbender account/allocation. No credentials, purchases, cluster logins or job submissions were performed. The project does not require an LLM API key.

