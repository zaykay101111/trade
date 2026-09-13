# Prospective injury challenger

`runs/injury-pair-v1` is the frozen release (2026-09-13). Monitoring and
settlement code (`injury-pair-status`, `injury-pair-settle`) lives in
`pair_monitor.py`, deliberately OUTSIDE the challenger surface hash, so that
monitoring improvements during the season never force a refreeze. A transient
v2 was frozen and discarded the same day, before any issuance, when monitoring
briefly lived inside `challenger.py`; its weights were verified identical to
v1. Do not add code to `challenger.py` or `injury.py` after issuance begins —
that would invalidate the release.

The deployed baseline remains unchanged. The new release contains a matched
11-input control and 25-input injury challenger. Both fit on decisions and
available labels before 2025-01-01 UTC, and calibrate on later decisions with
labels available before 2025-07-01 UTC. Lambda remains .01. No new tuning or
retrospective evaluation is performed. The archive does not cover the deployed
baseline's full 2025-26 fitting/calibration period, so comparing only to that
newer baseline would confound injury inputs with training vintage.

The paired poll records three probabilities for identical games: matched control,
injury challenger, and deployed baseline. The primary future contrast is injury
minus matched-control log loss. The deployed baseline is a secondary operational
benchmark. ALL successfully recorded pairs, including missing-report games, enter
the primary comparison. Covered-only results are secondary; never select games
by the observed outcome. No stakes, odds requests or automatic promotion.

## Freeze once

```sh
sports freeze-injury-pair \
  --data data/normalized/nba-v3 \
  --reports data/injury-archive/parsed-v3.csv \
  --team-log data/raw/nba-team-games.csv \
  --baseline runs/release-2026-27-v2 \
  --out runs/injury-pair-v1
sports report --path runs/injury-pair-v1
```

Refuses an existing output. Preserve the bundle and its reported SHA-256 before
first issuance. Source changes require a new release, not a drift override.
Historical injury inputs are backfilled development data, not prospective proof.

## Offline rehearsal now

```sh
sports injury-pair-poll \
  --collection collection/2026-27 --pair runs/injury-pair-v1 \
  --baseline runs/release-2026-27-v2 --data data/normalized/nba-v3 \
  --out collection/injury-pair-v1 --at 2026-10-20T17:58:00Z
```

This uses the current schedule, not a verified future schedule. It writes only
`simulated/` records. Omitting an archive means explicit missing-report states,
not healthy rosters. Repeated games are skipped. No network request is made.

## Capture on actual game days, before T-60

Use the existing free NBA PDF archiver in a SEPARATE prospective archive:

```sh
REPORT_DAY=$(TZ=America/New_York date +%F)
python scripts/archive_injury_reports.py \
  --start "$REPORT_DAY" --end "$REPORT_DAY" \
  --out data/injury-prospective --prospective \
  --hours 11AM,12PM,01PM,02PM,03PM,04PM,05PM,06PM,07PM,08PM \
  --max-files 10
```

That command makes public NBA PDF requests, not paid odds requests. Slots may be
absent; inspect its failure count. Capture periodically before games if desired;
no scheduler has been installed. Store PDFs and the append-only index together.
The paired poll parses captured PDFs directly, avoiding a stale parsed CSV.
Only prospective-marked, hash-verified PDFs retrieved strictly before the actual
input observation time and within 48 hours are eligible. Nominal report time must
not exceed retrieval time. Game/date/matchup/team matching still applies. Locally
recorded timestamps are evidence of this collector's operation, not independent
attestation; the prospective flag alone is insufficient.

## Record during the five minutes BEFORE each T-60 cutoff

Keep the schedule refreshed and use the latest merged settled dataset (the
`--data` path below must be updated as new games settle). Stale result history can
degrade forecasts; this command does not download outcomes automatically.

```sh
sports injury-pair-poll \
  --collection collection/2026-27 --pair runs/injury-pair-v1 \
  --baseline runs/release-2026-27-v2 --data data/normalized/nba-v3 \
  --archive data/injury-prospective --out collection/injury-pair-v1 --record
```

`--record` forbids `--at`. Late completion refuses issuance. Features use the
actual input-observation time, not the still-future cutoff. Recorded and simulated
files are separate; each game has one exclusive-create JSON snapshot. Never edit
recorded files. A failed/partial write requires inspection, not deletion and
backdating. Each snapshot includes all 25 input values, three probabilities,
source hashes, selected report provenance and timestamps. The data hashes identify
the dataset version; preserve each version for replay.

## Monitoring and decision rules

During initial operation, paste the poll JSON here. Check paired game count,
both-usable count, missing/stale/not-submitted/invalid states and source timestamp
ordering. A zero-game result outside the pre-cutoff window is normal. Log missed
scheduled games separately; recorded forecasts alone do not establish coverage.

Keep weights frozen for the first prospective season. Monthly checks are for
pipeline errors and descriptive calibration, not model promotion. After that
season, compare paired log loss with weekly-block uncertainty, Brier score and
calibration; report missingness and excluded/missed games. A negative difference
with an interval below zero would support this feature set on that prospective
sample, not bookmaker profitability. The sample size is not guaranteed to give
enough precision. Do not use the consumed 2025-26 holdout as confirmation.

Settlement is wired: `sports injury-pair-settle --records collection/injury-pair-v1
--collection collection/2026-27 --data <latest merged dataset> --out runs/<new>`
scores every recorded snapshot whose game exists in the settled dataset. It
reports per-model log loss, Brier, accuracy, 10-bin calibration with ECE, the
three paired contrasts with weekly-block intervals (None below ten blocks),
coverage (past cutoffs, recorded, missed), games still awaiting results, and a
covered-only secondary split. It verifies each snapshot filename against its
game id, never modifies a record, refuses an existing output directory, and
computes no promotion decision. `--include-simulated` scores rehearsal records
and labels them never-evidence.

## Automation — 2026-09-13

`scripts/prospective_tick.py` is one cron-safe tick that does everything above:
on a game day it captures today's injury PDFs prospectively (throttled to one
attempt per 30 minutes, free public requests only), then runs the recorded
paired poll (a no-op outside any five-minute pre-cutoff window), then runs
`injury-pair-status`. Every tick appends one JSON line to
`logs/prospective.jsonl`; failures append to `logs/alerts.log` and raise a
macOS notification. Newly missed T-60 windows alert once each and are listed in
`logs/missed_games_alerted.txt`; `sports injury-pair-status` enumerates them
all at any time.

The rolling dataset path lives in `configs/rolling-dataset.txt`. After each
`merge-settled`, update that one line to the new dataset directory; cron needs
no editing. A broken pointer is a CRITICAL alert, not a silent fallback.

`scripts/refresh_results.sh` is the weekly results-refresh loop: fresh schedule
payload download, `merge-settled` into a new dated dataset, pointer advance
(only after the merge validates), and `collect-refresh` of the plan. It never
touches recorded snapshots and alerts on any failure.

Install both with `scripts/install_automation.sh` (idempotent, tagged crontab
lines: tick every 5 minutes, refresh Mondays 10:00 local). Remove with
`crontab -l | grep -v SPORTS_METHOD_AUTOMATION | crontab -`. The Mac must be
awake at poll times. Not installed automatically; run it before 2026-10-20.

### Before opening night (2026-10-20) checklist

1. Run `scripts/install_automation.sh` and confirm two tagged crontab lines.
2. Run `scripts/refresh_results.sh` once by hand; confirm the pointer advanced
   and `collect-refresh` assigned any NBA Cup rows.
3. Run one manual `prospective_tick.py`; expect a healthy heartbeat in
   `logs/prospective.jsonl` and nothing in `logs/alerts.log`.
4. Keep the Mac awake through game windows (pmset schedule or Amphetamine).
5. After the first game day, paste `sports injury-pair-status` output and the
   first recorded snapshot here for review.

Everything a prospective evidence claim needs is frozen and rehearsed now;
what remains is operational (arming cron and keeping the machine awake).
Evidence itself can only accrue from 2026-10-20 onward.

## Audit — 2026-09-13

Independent audit of the frozen pair and the offline rehearsal record:

- **Reproducibility.** Re-running the simulated poll at the same `--at` into a
  fresh directory produced a byte-identical payload, including all provenance
  hashes. 102 tests pass, covering backdating refusal, drift refusal, archive
  hash/timestamp gates, T-60 crossing refusal, and schedule-observation ordering.
- **Timestamps.** In the rehearsal snapshot: schedule observed ≤ issuance <
  cutoff, scheduled − cutoff = 60 minutes, and simulated issuance equals the
  requested `--at`. Archive eligibility enforces prospective flag, 48-hour
  window, nominal ≤ retrieved, and per-file SHA-256.
- **Matching.** `parsed-v3.csv` matches its manifest and the manifest matches
  the current parser hash. avail-v3 report: 1,215 reports, 99,904 rows, 16
  rejected rows, 16 unmapped team rows, coverage 93.25%.
- **Missing reports.** States are explicit (missing/stale/not_submitted/invalid)
  and never imputed as healthy. **Known frozen-model property:** `home_missing`
  was rare in training (0.67%), so its standardized value at a missing-report
  game contributes about −0.53 to the injury challenger's logit, while
  `away_missing` was shrunk to ~0 by L2. A game with no captured report can
  shift the injury forecast by >0.1 probability relative to the matched control,
  asymmetrically by side. This is frozen behaviour, not a pipeline bug; the
  primary all-recorded-pairs contrast charges the challenger for it, which is
  the intended accountability. Track missing-report frequency in monitoring —
  if live capture fails often, this term, not injury signal, will dominate the
  contrast.
