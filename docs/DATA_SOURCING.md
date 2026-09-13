# Data sourcing: what each claim needs and what it costs

Researched 2026-09-13. Prices and terms change; re-verify before acting.
Nothing in this document has been purchased and no paid call has been made.

## 1. The binding constraint is provenance, not money

Three tiers of claim need three different datasets:

| Claim | Data required | Status |
|---|---|---|
| A. Forecast quality (log loss vs a baseline) | schedules + final scores | HAVE IT, free, complete |
| B. Market edge (beats a price you could have taken) | multi-book prices AT the prediction cutoff, plus a separate execution book | MISSING |
| C. Better features (injuries, pace, travel, referees) | per-game auxiliary data | PARTLY FREE |

Tier A is done and cost nothing. Tier B is the entire remaining question, and its
difficulty is not price: closing odds are free and abundant, but a closing price
is not a price you could have taken at T-60, and no amount of free closing data
fixes that. What costs money is *timestamped* history.

## 2. Measured request volume for this project

Counted from `data/normalized/nba-v3/games.csv` (not estimated). One API request
returns every game in a snapshot, so the unit of cost is a distinct tip time, not
a game.

| Season | Games | Distinct tip times | Game days | Snapshots/day |
|---|---|---|---|---|
| 2020-21 | 1,080 | 630 | 140 | 4.5 |
| 2021-22 | 1,230 | 763 | 168 | 4.5 |
| 2022-23 | 1,230 | 773 | 167 | 4.6 |
| 2023-24 | 1,230 | 735 | 163 | 4.5 |
| 2024-25 | 1,230 | 765 | 164 | 4.7 |
| 2025-26 | 1,230 | 791 | 166 | 4.8 |
| **Total** | **7,230** | **4,457** | | |

A typical NBA season needs ~750 T-60 snapshots. That number drives everything below.

## 3. Sources and costs

### Schedules and results — free, unlimited
`nba_api` (ScheduleLeagueV2, LeagueGameFinder). Already in use, covers every
season back to the 1940s. No reason to pay anyone for this, ever. Known caveats
are documented in DATASETS.md: reconstructed `schedule_observed_at`, assumed +24h
result availability, and the postponed-status filter bug that cost two seasons.

### Timestamped multi-book odds, going forward — free
The Odds API free tier: 500 credits/month; cost is `markets x regions` per
request; one request returns all upcoming NBA games across every book in the
region. At ~750 snapshots per season spread over six months, h2h + us costs
**~124 credits/month against a 500 cap** — roughly 4x headroom, enough for a
second region, a closing snapshot, or retries. Per-bookmaker `last_update` fields
and `x-requests-remaining` headers are returned, so both the book's own update
time and our request time can be recorded. Terms permit storing data
indefinitely and publishing derived values including in research papers;
redistributing the raw feed as a product is prohibited, which does not apply here.

Backup/cross-check: SportsGameOdds free tier, 9 books, 2.5k objects/month,
10 req/min. Useful for verifying a second opinion on prices, not as the primary.

### Timestamped multi-book odds, historical — the only purchase worth considering
The Odds API historical endpoints: 5-minute snapshots back to 2020-06-27 for NBA,
at a **10x credit multiplier**, available on the $59/month 100k plan and above.

Backfilling T-60 for every season already in `nba-v3`:

- 4,457 snapshots x 10 credits x 1 region = **44,570 credits**
- Both US regions (more books): **89,140 credits**, still inside one month of 100k

So **one month at $59 buys the complete T-60 price history for all six seasons we
already model**, with both US regions, and the data may be kept forever after
cancelling. That is the single highest-value dollar available to this project: it
converts six seasons of finished forecasting work into an immediate, testable
edge question instead of a twelve-month wait.

Trade-off inside the same budget: two regions at T-60, or one region at T-60 plus
a closing snapshot for comparison. Both fit; doing all three does not.

### Correction: costed against the existing plan file

The figures above assume one snapshot per tip time and one region. The project's
own `data/odds-plan.json` is more ambitious: 5,918 planned timestamps (paired
snapshots five minutes apart, for the same-book stress test) across regions
`us,uk,eu` - a 3x multiplier. Costed properly:

| Scope | Credits | Cheapest tier that fits |
|---|---|---|
| us only, paired snapshots | 59,180 | 100k, $59 |
| us + us2, paired snapshots | 118,360 | 5M, $119 |
| us,uk,eu as already planned | 177,540 | 5M, $119 |

So the existing plan, executed in full at 5-minute paired resolution across three
regions, is **$119 for one month**, not $59. Both numbers are one-off: the data
may be retained after cancelling. The $59 option buys US books only and drops the
paired-snapshot stress test; the $119 option buys the plan as designed. Neither
is authorized, and neither should be bought before the free prospective collector
proves the storage format.

### Historical closing odds — free but provenance-poor
sportsbookreviewsonline.com publishes season archives for 2007-08 through
2022-23 (moneyline, opening and closing spreads/totals). Free, no timestamps, one
unnamed source book, and the archive is frozen and no longer updated. It is
enough to reproduce published academic results, which overwhelmingly use closing
odds, and it is NOT enough for any claim about a price this project could have
taken. Treat it as a literature-comparison tool, not as evidence.

### Injuries — the expensive gap
Official NBA injury reports have been published since 2017, but as per-day PDFs
with no clean archive; scraping them forward is free, reconstructing them
backward is the hard part. Commercial historical injury feeds are the costly
tier, and this is where money would actually be required if the project ever
needs Tier C. Recommendation: start archiving the daily report now (free,
forward-only) rather than buying history.

### Pace, possessions, referees, travel — free
`nba_api` boxscore and team-dashboard endpoints cover possession-adjusted
efficiency and officials; travel and rest derive from the schedule we already
have plus static arena coordinates. All free, all rate-limited, none urgent.

## 4. Recommended sequence

1. **Now, free, time-sensitive.** Stand up prospective T-60 collection before the
   2026-27 opener on 2026-10-20. It costs nothing, fits the free tier four times
   over, and it is the only way to obtain prices whose availability we observed
   ourselves rather than assumed. Missing the opener cannot be undone later.
2. **Free, any time.** Extend schedules/results backward with `nba_api` for
   era-replication work (see FINAL_PROTOCOL.md and the external-era command).
3. **Optional, $59 once, needs explicit authorization.** Historical T-60 backfill
   for 2020-2026. Do this only after step 1 proves the collector and storage
   format work, so the purchased month is spent on data and not on debugging.
4. **Do not buy** closing-odds products, per-sport "premium" feeds, or injury
   history until a genuine edge signal exists at T-60. Nothing observed so far
   justifies recurring spend.

## 5. What no amount of data buys

A historical price snapshot does not prove this account could have placed that
bet at that price for that stake. Line shopping, limits, account restriction and
vig all sit between a favourable probability estimate and realised profit, and
none of them appear in any dataset above. The honest ceiling of the paid path is
"the model disagreed with the market in a way that would have been profitable on
recorded prices" — which is worth establishing, and is still not proof of a
deployable edge.
