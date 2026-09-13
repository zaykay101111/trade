# NFL free data source inventory

Verified by direct request on 2026-09-13. No paid source is used anywhere below.

## Primary: nflverse

License **CC-BY-4.0** (confirmed via the GitHub repository metadata API for
`nflverse/nflverse-data`; note there is no `LICENSE` file at either data repo
root, so attribution terms come from the repo metadata and project docs).
nflverse is a volunteer-maintained aggregation of NFL/NGS/PFR sources, not an
official NFL feed. It can be revised or withdrawn without notice, which is why
every download below is cached raw and hashed.

| Feed | URL | Verified |
|---|---|---|
| Schedules + results | `nfldata/raw/master/data/games.csv` | 7,548 rows, 1999–2026 |
| Injuries | `nflverse-data/releases/download/injuries/injuries_{season}.csv` | 6,068 rows for 2025 |
| Weekly rosters | `.../weekly_rosters/roster_weekly_{season}.csv` | HTTP 200 |
| Snap counts | `.../snap_counts/snap_counts_{season}.csv` | HTTP 200 |
| Play-by-play | `.../pbp/play_by_play_{season}.csv` | HTTP 200 |

### games.csv — what it actually contains

Regular season: 7,239 rows, of which 6,969 are played and 270 are the
unplayed remainder of 2026. Per-season counts are 256 (pre-2021) then 272.
Columns include `gameday`, `gametime`, `location`, `result`, `overtime`,
`div_game`, `roof`, `surface`, `temp`, `wind`, `home_rest`/`away_rest`,
`home_qb_id`/`away_qb_id`, and closing moneylines.

Verified properties that drive design decisions:

- **Ties are real: 15 of 6,969 regular-season games (0.215%)**, occurring in 12
  distinct seasons including 2022 (2) and 2025 (1). The NBA path's
  "final games cannot be tied" invariant is therefore invalid for NFL.
- **Neutral sites: 74 regular-season games** (`location == "Neutral"`).
- **Cancellations disappear rather than appearing unplayed.** 2022 has 271
  regular-season rows, all with results; the cancelled Bills–Bengals game is
  absent. So a missing game id is the cancellation signal, not a null result.
- **Sample size is the binding constraint.** 272 games per NFL season against
  ~1,230 for NBA — roughly 4.5× fewer per season.
- `temp`/`wind` are populated for 4,983 regular-season games only (outdoor
  venues); `roof` distinguishes dome/closed/open/outdoors.

### Timestamp limitations (the important caveat)

`games.csv` gives `gameday` + `gametime` in **US Eastern local time with no
timezone column and no revision history**. There is no publication or
retrieval timestamp in the file. Therefore:

- Kickoff is converted from `America/New_York` to UTC by us, and the
  conversion is our assumption, not a provider-attested instant.
- `schedule_observed_at` must be **reconstructed** exactly as on the NBA side
  (declared assumption, not evidence), so a backfilled NFL schedule can never
  establish what was visible before a past game.
- Because the file is refreshed in place, a backfill retrieved today reflects
  today's corrections, not the contemporaneous state.

### Injuries — no timestamp at all

`injuries_2025.csv` has 16 columns and **no `date_modified` or any other
timestamp**. Data is week-scoped only (`season`, `week`, `team`, `gsis_id`,
`report_status`, `practice_status`). Status values are `Out` (1,382),
`Questionable` (1,283), `Doubtful` (120), and null (3,283 — practice-report
rows carrying no game-status designation).

This is materially weaker than the NBA injury PDFs, which carry a nominal
report time per file. Consequences, which must not be papered over:

- Backfilled NFL injuries **cannot** support an "available before cutoff"
  claim for any past game. They are week-granular development inputs only.
- For prospective use the pipeline must capture the feed itself and stamp its
  own retrieval time, exactly as the NBA PDF archiver does. Only those
  self-captured, hash-verified snapshots are eligible as pregame inputs.
- Within a week, a Thursday game and a Sunday game share a week label, so
  week-scoped rows are not safely attributable to the earlier kickoff.

### Closing moneylines are present but unusable as evidence

`home_moneyline`/`away_moneyline` are populated for 5,081 regular-season
games. They are single-source, **untimestamped closing** prices — the same
category the NBA track already classifies as literature-comparison only. They
must never be treated as an obtainable price, and they are excluded from the
prediction pipeline entirely.

## Prospective-collection advantage over NBA

The 2026 NFL regular season is **already in progress** (Week 1 played
2026-09-09/10, remaining Week 1 games kicking off 2026-09-13). Weeks 1–18 are
scheduled. Genuine prospective NFL evidence can begin accruing immediately,
whereas the NBA track cannot start before 2026-10-20.

## Not adopted

- ESPN's undocumented JSON endpoints: no stability or licensing guarantee.
- Weather APIs: deferred; `temp`/`wind`/`roof` in games.csv are backfilled
  observations, not forecasts, so they leak and are excluded from features.
