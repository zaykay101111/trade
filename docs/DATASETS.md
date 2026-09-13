# Data download manifest

The executable core requires three normalized CSVs. Several source downloads feed them. Begin with 2020–21 through 2025–26 regular seasons, plus earlier results for rolling-history warmup where available. Use all and only seasons whose odds coverage you can establish. Older game results without contemporaneous odds are not additional market-residual training examples.

## 1. Timestamped moneyline odds — required

Provider candidate: [The Odds API historical endpoint](https://the-odds-api.com/historical-odds-data/). This is **the-odds-api.com**, not the similarly named theoddsapi.com. The vendor documents paid historical snapshots; featured markets began in June 2020 and moved to five-minute snapshots in September 2022. NBA-specific start/individual bookmaker coverage must be checked in the coverage list and actual samples.

Request `basketball_nba`, `markets=h2h`, `oddsFormat=decimal`. Collect snapshots at or before the 60-minute cutoff and again approximately five minutes later for price-delay evaluation. Archive full responses, requested time, returned snapshot time and acquisition time. Do not substitute closing odds into the earlier forecast.

Need at least three complete reference-book pairs and one execution-book pair per eligible game. The configuration's reference books are provisional examples. Inspect returned bookmaker keys and confirm comparable rules. Reference books and execution books are disjoint in this version; this prevents the purchased quote from serving as its own reference. Exchange reference prices may require commission adjustment and do not reveal traded liquidity.

A multi-year archive is typically obtained through API requests, not one download button. The project includes a bounded request planner and resumable fetcher:

```bash
sports plan-odds --games data/normalized/nba-v1/games.csv --out data/odds-plan.json
sports fetch-odds --plan data/odds-plan.json --out data/raw/odds
```

The second command is a dry run. It prints request and estimated credit counts without fetching. The planner uses US, UK and EU regions to cover the example reference books and budgets conservatively at 30 credits per requested timestamp for one market. Compare with current provider terms before executing. Two timestamps for 6,000 games can approach 12,000 requests before deduplication; review the plan before purchasing capacity.

After you choose a plan and put your key into the local `ODDS_API_KEY` environment variable:

```bash
sports fetch-odds --plan data/odds-plan.json --out data/raw/odds --execute --max-requests 10
```

This explicitly caps new requests at ten. Repeating resumes after existing files. Inspect the sample first, then increase the cap deliberately. The API key is neither written to raw files nor included in reports.

## 2. Schedule history and event identity — required

Acquire NBA schedules with game IDs, teams, tip-off timestamps, season type, neutral/special-format flags and schedule revisions. [Sportradar historical NBA documentation](https://developer.sportradar.com/basketball/docs/nba-ig-historical-data) is one provider candidate. Archived odds responses also contain event IDs, names and scheduled times and can corroborate a schedule.

For the canonical table, choose the schedule revision known at the decision time. A present-day schedule file does not establish what was known historically. Include only audited regular-season games under the selected contract. Treat unusual neutral-site/special-format and postponed games explicitly before admission.

`games.csv` requires:
- `game_id`: canonical NBA GAME_ID as a string, preserving zeros.
- `home_id`, `away_id`: NBA team IDs as strings.
- `scheduled_at`: full timestamp with offset.
- `schedule_observed_at`: when the chosen schedule revision was available.
- `decision_at`: exactly scheduled_at minus 60 minutes.
- `season_type`: `regular`.
- `contract`: `nba_regular_fullgame_moneyline_ot`.

Each game has one audited decision row in this release. Preserve the raw revision history separately. Rescheduling resolution is not automated by guessing from final schedules.

Prepare `event_map.csv` with `provider_event_id,game_id,home_name,away_name`. Exact names refer to the odds response. This adapter requires explicit mappings and refuses name mismatches. Never join solely on team pair without game identity/date verification.

Normalize downloaded odds:

```bash
sports normalize-odds --raw data/raw/odds --mapping data/normalized/nba-v1/event_map.csv --out data/normalized/nba-v1/odds.csv
```

The output has paired decimal odds, bookmaker, source quote time, archive availability, contract, raw-file hash and actual retrieval time. Unmapped events are listed; daily snapshots contain unrelated games, so audit expected coverage rather than assuming every listed event belongs to this experiment.

## 3. Historical final team results — required

Download NBA team game logs for the same seasons and warmup history. The [nba_api project](https://github.com/swar/nba_api) provides a client for NBA.com; it is community maintained, and historical downloads can time out or change. Its [LeagueGameFinder schema](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamefinder.md) includes game/team IDs, game date and points.

An optional downloader is included:

```bash
python -m pip install -e '.[nba]'
python scripts/download_nba.py --seasons 2020-21,2021-22,2022-23,2023-24,2024-25,2025-26 --out data/raw/nba-team-games.csv
sports import-nba-results --raw data/raw/nba-team-games.csv --games data/normalized/nba-v1/games.csv --out data/normalized/nba-v1/results.csv
```

The core consumes final points, not possession statistics. A richer feature release can retain FGA, FTA, OREB, TOV, minutes and roster information from the raw logs.

`results.csv` requires `game_id,home_score,away_score,available_at`. Future games can be absent. Final scores must be unequal nonnegative integers because the contract includes overtime.

The convenience adapter marks results available **24 hours after scheduled start** as a conservative research convention. It cannot certify actual publication time and is unsuitable for suspended/delayed games without audit. Replace that convention with genuine observed result timestamps for prospective collection. Final corrected box scores can still introduce reconstruction uncertainty; disclose that limitation.

## 4. Archived injury/status revisions — optional next release

Obtain official timestamped reports, roster IDs, publication time, statuses and later corrections. [Official NBA injury reports](https://official.nba.com/nba-injury-report-2025-26-season/) and a licensed historical injury feed are candidates. Verify that a vendor retains intraday revisions; a date-based “injuries” endpoint alone does not establish this.

A final DNP label cannot replace a pregame status. The current model does not ingest injuries and will not treat a missing report as a healthy roster. No injury dataset is required to execute the reduced core.

## 5. Prospective execution evidence — required for operational conclusions

Collect fresh local ingestion times, decision issuance, manual quote checks, and verified settlements. This is generated going forward, not downloaded from a historical game-results repository.

The paper ledger records first manual price checks and whether they met the price floor before expiry. Historical displayed prices are never labeled accepted wagers. Book limits, account-specific availability and commission rules need separate records before any execution claim.

## Data audit before full backfill

Inspect 100 games, including changed start times, late injuries, missing books and suspicious odds. Confirm IDs, timezone offsets, paired markets, timestamps and source rights. Report missingness by season and bookmaker. Start a new configuration if coverage forces a different book set.

Archive immutable originals and checksums. Normalized CSVs are an interface, not proof of provenance. The code rejects malformed timestamps and detectable leakage but cannot establish that an invented timestamp is true.

