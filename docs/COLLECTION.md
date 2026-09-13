# Prospective T-60 collection

Records what the model forecast and what prices existed at the moment of the
forecast, for the 2026-27 season. **Collection only.** No expected value, stake,
admission decision or wager is computed or stored anywhere in this workflow;
`test_collect.py` asserts that no such column is ever written.

Why now: the 2026-27 schedule was released 2026-08-13 and the season opens
2026-10-20. Prices observed as they arrive are the only kind that support a claim
about what was obtainable; a backfill can only ever support research.

## One-time setup

```bash
# 1. Schedule (needs NBA access; free)
python scripts/download_schedule.py --seasons 2026-27 --out data/normalized/nba-2026-27
python -c "import pandas as pd;d=pd.read_csv('data/normalized/nba-2026-27/games.csv',dtype={'game_id':str});print(len(d),'games')"

# 2. Deployment bundle, frozen before opening night
sports freeze-release --data data/normalized/nba-v3 --out runs/release-2026-27 \
  --train-end 2025-07-01 --tune-end 2026-01-01 --calibration-end 2026-07-01 \
  --threads 2 --label "2026-27 prospective"

# 3. Collection directory
sports collect-init --schedule data/normalized/nba-2026-27/games.csv \
  --out collection/2026-27 --season 2026-27

# 4. Dry run: forecasts only, no request, no credit spent
sports collect-poll --collection collection/2026-27 --bundle runs/release-2026-27 \
  --data data/normalized/nba-v3 --at 2026-10-21T23:00:00Z
```

## Games the NBA has not assigned yet

The 2026-27 schedule was published with 1,206 regular-season rows, not 1,230.
Every team has exactly 80 of its 82 games assigned; the remainder depend on the
Emirates NBA Cup. Six of those rows are Cup knockout games published with
**team id 0 and no arena** (2026-12-04, 12-05 and 12-08), and roughly thirty
further games are not in the file at all until the bracket resolves.

`collect-init` holds any row without both teams in `pending_assignment.csv` and
plans no polls for it, because forecasting a game with no teams would corrupt
ratings. Once the NBA assigns them:

```bash
python scripts/download_schedule.py --seasons 2026-27 --out data/normalized/nba-2026-27-r2
sports collect-refresh --collection collection/2026-27 --schedule data/normalized/nba-2026-27-r2/games.csv
```

`collect-refresh` adds newly assigned games, records start-time changes and
withdrawals in `schedule_revisions.csv`, and bumps the collection revision. It
never edits an executed poll: recorded forecasts, quotes and ledger rows are
immutable, and a test asserts their bytes are unchanged across a refresh.

Note for December: game IDs ending 1229 and 1230 follow the pattern of the 2023
Las Vegas Cup semifinals, which `venues.py` had to correct by hand because the
provider's neutral flag was wrong. Review those rows when they are assigned
rather than trusting `is_neutral`.

`freeze-release` fits the same frozen recipe in the same fold shape used
everywhere else - train through 2025-07-01, tune through 2026-01-01, refit on
train+tune, calibrate on the first half of 2026 - and scores nothing. It is a
bundle to forecast with, not evidence.

## Running a poll

```bash
export ODDS_API_KEY=...        # free tier, 500 credits/month; never paste the key into a report
sports collect-poll --collection collection/2026-27 --bundle runs/release-2026-27 \
  --data data/normalized/nba-2026-27-settled --regions us \
  --execution-book draftkings --execute
sports collect-status --collection collection/2026-27
```

Without `--execute` nothing is requested and only a dry-run forecast file is
written. With it, one request costs `markets x regions` credits: at h2h and `us`
that is 1 credit for every game in the snapshot. A season of roughly 750 poll
times costs ~124 credits per month against the 500 free cap.

`--data` must point at a dataset of SETTLED games, refreshed as the season
progresses; pending games are forecast from it. Elo and rolling history continue
to update as results become available, exactly as in evaluation.

## What is recorded

| File | Contents |
|---|---|
| `raw/<poll>.json` | verbatim provider payload, regions, quota headers, retrieval time |
| `forecasts.csv` | model probability per game, issue time, bundle path, both code hashes, drift flag |
| `quotes.csv` | per book: both decimal prices, de-vigged home probability, overround, **the book's own `last_update`** and our `retrieved_at` |
| `reference.csv` | median de-vigged home probability across books, execution book excluded, book count, spread, abstention reason |
| `polls.csv` | ledger: planned/executed time, events returned, games matched, quarantined, credits used and remaining |
| `quarantine.csv` | provider events that could not be matched to a canonical game, with the reason |

Storing the book's update time separately from our retrieval time is the whole
point: it is what later distinguishes "this price existed at the cutoff" from
"we assumed it did".

## Guarantees

- **No outcome can leak.** Pending games carry placeholder scores whose
  availability is set to the year 2200, so the shared point-in-time feature
  builder can never reveal them. A test perturbs those placeholders and asserts
  no feature moves.
- **A poll cannot be repeated.** A second request at the same poll ID is refused;
  records are append-only and credits are not spent twice.
- **A late poll collects nothing.** Games are targeted only within the window
  around their T-60 cutoff, so a job that fires 45 minutes late records no
  forecast rather than a stale one.
- **Thin coverage abstains.** Fewer than three reference books (excluding the
  execution book) yields no reference and a recorded abstention reason.
- **The execution book is never in its own reference.**
- **Code drift halts forecasting** unless `--allow-code-drift` is passed, and the
  override is recorded on every row it produces, with both hashes.
- **The quota is watched.** Polls record credits remaining and warn below 25.

## What this does not do

It does not decide whether to bet, size anything, or place anything. Those belong
to later gates in FINAL_PROTOCOL.md and the blueprint, and only after a measured
comparison against the de-vigged market reference clears Gate B.
