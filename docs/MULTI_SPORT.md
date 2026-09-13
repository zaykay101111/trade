# Multi-sport architecture and roadmap

One pipeline, two sports. No separate project, no duplicated NBA system.

## The shared / sport-specific boundary

The governing constraint is `io.FORECAST_SURFACE = (free_data.py, model.py,
collect.py, io.py)`. A change to any of those four changes what a deployed NBA
forecast *means*, and the deployed baseline plus the injury-challenger release
both record the hash. **All NFL code therefore lives outside that surface**,
and `tests/test_surface_regression.py` pins it so no future multi-sport change
can move it silently.

Note the package-wide `code_hash()` is a different thing: it globs every module
and legitimately drifts as research modules are added. It was already stale on
every historical run before this work. It is provenance, not a gate.

| Layer | Status | Modules |
|---|---|---|
| Shared, reused unchanged | numerics and plumbing | `model.fit_logistic/fit_calibration/calibrate`, `io` (hashes, atomic dirs, timestamps), `evaluate.block_interval`, `policy` exposure caps |
| Shared, thin new seam | sport resolution only | `sports.py` — a 3-field registry (loader, features, contract). Not a framework; add an entry only when a second sport concretely needs the same call |
| NFL-specific | data, features, outcomes, money | `nfl_data.py`, `nfl_train.py`, `nfl_policy.py`, `scripts/download_nfl.py` |
| NBA-specific, untouched | frozen | `free_data.py`, `collect.py`, `challenger.py`, `injury.py` |

`sports.detect()` infers a sport from a dataset's own declared `sport`/
`contract` columns, never from its path. NFL datasets declare both; NBA
datasets predate the work and declare neither, so an absent declaration means
NBA — which keeps every existing NBA dataset valid without rewriting one byte.

## NBA preservation — proven, not asserted

- Full suite 128 passed (was 114 before NFL work; nothing removed or skipped).
- `runs/release-2026-27-v2` and `runs/injury-pair-v1` still match the live
  forecast surface hash.
- The NBA paired forecast replayed **byte-identical** after all NFL changes:
  `p_deployed 0.5629919337804358`, `p_control 0.5280366884276054`,
  `p_injury 0.39781088096307315`.
- `free_data.load_games` still refuses a tied game, asserted by an NFL test.

## Commands

```sh
# Data (resumable; raw cached, hashed, retrieval-stamped)
.venv/bin/python scripts/download_nfl.py --out data/normalized/nfl-v2
.venv/bin/python scripts/download_nfl_qb.py \
  --seasons 2020,2021,2022,2023,2024 --out data/raw/nfl-qb

# Development (2025 holdout untouched, 2026 prospective)
.venv/bin/python -m sports_method.cli nfl-train \
  --data data/normalized/nfl-v2 --out runs/nfl-dev-v1
.venv/bin/python -m sports_method.cli nfl-compare-qb \
  --data data/normalized/nfl-v2 --qb-weekly data/raw/nfl-qb/nfl-qb-weekly.csv \
  --out runs/nfl-qb-v1

# Freeze, then collect prospectively
.venv/bin/python -m sports_method.cli nfl-freeze \
  --data data/normalized/nfl-v1 --out runs/nfl-pair-v1
.venv/bin/python -m sports_method.cli nfl-collect-init \
  --data data/normalized/nfl-v1 --out collection/nfl-2026 --season 2026
.venv/bin/python -m sports_method.cli nfl-poll \
  --collection collection/nfl-2026 --pair runs/nfl-pair-v1 \
  --data data/normalized/nfl-v1 --out collection/nfl-pair-v1 --record

# Monitor and settle (ties/pushes/voids; sports reported separately)
.venv/bin/python -m sports_method.cli nfl-status \
  --collection collection/nfl-2026 --records collection/nfl-pair-v1
.venv/bin/python -m sports_method.cli nfl-settle \
  --records collection/nfl-pair-v1 --collection collection/nfl-2026 \
  --data data/normalized/nfl-v1 --out runs/nfl-settle-$(date -u +%Y%m%d)

# Automation: cron every 5 min, or a foreground watcher when cron is unavailable
sh scripts/install_automation.sh
sh scripts/nfl_watch.sh 2026-09-14T04:00:00Z

# NBA commands are unchanged, e.g.
.venv/bin/python -m sports_method.cli injury-pair-status \
  --collection collection/2026-27 --out collection/injury-pair-v1
```

## Current NFL result — criteria NOT met

`runs/nfl-dev-v1`, folds 2022/2023/2024, 6,447 games (14 ties), 2025 reserved:

| model | decided log loss | Brier | acc | 3-way log loss |
|---|---|---|---|---|
| home_rate | 0.688534 | 0.247695 | 0.5498 | 0.704061 |
| elo | 0.659247 | 0.232642 | 0.6285 | 0.674847 |
| logistic | 0.644140 | 0.226394 | 0.6322 | 0.659777 |

- logistic − home_rate: −0.044394, 95% week-block interval [−0.062161, −0.025827] (excludes zero)
- logistic − elo: −0.015107, 95% week-block interval [−0.030797, **+0.000159**] (includes zero)

The challenger beats the trivial baseline decisively but **not Elo**: it loses
the 2024 fold (0.632872 vs 0.622441) and the pooled interval against Elo
barely includes zero. The prespecified criteria required winning every fold
*and* an interval excluding zero, so **the criteria are not met and the 2025
holdout stays unspent.** The penalty was fixed a priori at L2 = 0.01 (the
NBA-selected value); it was not tuned to rescue this result, and it must not
be.

## Prospective NFL operation — live

`runs/nfl-pair-v1` is frozen (control = Elo, challenger = the logistic; fit
through 2023, calibrated on 2024, tie rate 0.0022472, **2025 reserved and
unread**). `collection/nfl-2026` holds all 272 games of the in-progress season.

Because development did **not** meet the advancement criteria, this pair is
collected as a prospective RESEARCH comparison, not a deployment. That is
recorded in the frozen bundle's own protocol string so it cannot be forgotten.

`scripts/nfl_tick.py` is one cron-safe tick: throttled schedule refresh (free
nflverse only, at most every 12h), then the recorded paired poll with retries,
then status. Retries stop immediately if T-60 is crossed, because a later
attempt could only backdate. `scripts/nfl_watch.sh` runs the same tick on a
60-second loop when cron is unavailable; both are safe together because
snapshots are exclusive-create.

### Verifying cron actually fires (macOS traps)

Two failure modes look identical from the outside — nothing happens — so check
for the artifact rather than assuming:

```sh
crontab -l | grep SPORTS_METHOD_AUTOMATION   # must print 3 lines
ls -la logs/cron.out                          # must exist within 5 minutes
```

1. **Wrong crontab.** `sudo crontab -e` edits *root's* crontab, not yours.
   The tick then runs as root or not at all, and `crontab -l` as your user
   stays empty. Install without sudo.
2. **Full Disk Access.** This project lives under `~/Documents`, which macOS
   protects. `/usr/sbin/cron` cannot write there until you add it under
   System Settings → Privacy & Security → Full Disk Access (add
   `/usr/sbin/cron` via ⌘⇧G). Until then cron runs but every tick fails
   silently — `logs/cron.out` never appears.

If neither is convenient, `scripts/nfl_watch.sh` is a complete substitute for a
day's games and needs no system permissions.

## Quarterback research candidate (`runs/nfl-qb-v1`)

Expected starter = the quarterback who started that team's most recent game
whose **result was already available** at the cutoff. The target game's own
`home_qb_id`/`away_qb_id` is never read as a pregame input — that column is
actual participation and would leak the lineup.

| fold | base | +QB |
|---|---|---|
| 2022 | 0.652487 | 0.649939 |
| 2023 | 0.647153 | 0.649529 |
| 2024 | 0.632872 | 0.619456 |

Pooled −0.004537, 95% week-block interval [−0.015701, +0.006485] — **includes
zero**, and 2023 is worse. A promising but unconfirmed candidate. Notably it
helps most in 2024, the exact fold where the base challenger lost to Elo.

## Agent boundary (`agents.py`)

Agents may annotate, never forecast. Annotations are additive artifacts that
must cite sources carrying a url and a retrieval time; any key resembling a
probability, price, stake, Kelly fraction or EV is rejected by construction
rather than by convention, and `adopted` cannot be self-asserted — adoption
requires a measured improvement on the pipeline's own paired metrics.

## Roadmap

**Next**
1. Accumulate prospective NFL pairs and settle weekly with `nfl-settle`.
   Precision will be poor for months; 272 games a season is the constraint.
2. Beat Elo before considering any deployment: opponent-adjusted EPA per play
   from the verified free play-by-play feed is the obvious missing signal,
   since the current feature set is raw points-based.
3. Self-captured, retrieval-stamped NFL injury snapshots (the NBA PDF-archiver
   pattern). Required before declared status can be a pregame input at all.

**Blocked on a real dependency**
4. Genuine prospective evidence for both sports — accruing for NFL from today,
   and from 2026-10-20 for NBA. Replay and synthetic tests cannot substitute.
5. NBA cron activation and keeping the machine awake through game windows.

**Deferred, with reasons**
6. Weather: the feed's `temp`/`wind` are post-hoc observations, not pregame
   forecasts, so they leak; excluded until a forecast source with retrieval
   timestamps is added.
7. Automated postponement handling; correlated same-week exposure is tested
   but not yet wired into a live staking path (there is no live staking path).
8. Multi-agent adoption, gated on measured incremental benefit.

**Paid-data dependencies (nothing authorised, nothing purchased)**
10. No odds source is connected for either sport. The source feed's closing
    moneylines are single-source and untimestamped, so they are excluded from
    the pipeline and are literature-comparison only. Real odds become
    necessary only to measure edge, and would require the retrieval timestamp,
    the book's own `last_update`, the two-sided price and evidence the stake
    was actually available — none of which the free closing data provides.
