# Official NBA injury reports: coverage, access and caveats

Verified 2026-09-13 by direct retrieval. This corrects an earlier assumption in
DATA_SOURCING.md that injury history could only be captured forward.

## What is available

The NBA publishes an injury report as a PDF at

```
https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HHAM|PM.pdf
```

roughly hourly, and **files for past dates remain retrievable**. Probed coverage:

| Date probed | Result |
|---|---|
| 2018-10-20, 2018-12-01 | 403 (absent) |
| 2019-01-15 onward | 200 |
| 2020-12-26, 2021-03-01, 2022-03-01, 2023-03-01 | 200 |
| 2024-03-01, 2025-03-01, 2025-11-01, 2025-12-15 | 200 |
| 2026-01-15 onward, all hours swept | 403 (absent) |

So the archive spans roughly **2019-01 to 2025-12**. That covers 2020-21 through
2024-25 in full - the entire training window - plus the first half of 2025-26.
January to April 2026 is NOT retrievable at this path, so 2025-26 availability
data is only half covered. The 2026-27 season can be captured live from opening
night, which closes the gap permanently going forward.

Successive files on one day genuinely differ and grow (2025-12-01: 77,504 bytes
at 01AM rising to 91,952 by 08PM), so these are real revisions, which is what
§15 of the blueprint asks to archive rather than only final status.

## Content

Machine-readable, structured columns:

```
Injury Report: 11/05/25 05:30 PM
GameDate GameTime Matchup Team PlayerName CurrentStatus Reason
11/05/2025 07:00(ET) BKN@IND BrooklynNets Highsmith,Haywood Out  Injury/Illness-RightKnee;Surgery
                                          Dennis,RayJ      Probable ...
```

`CurrentStatus` carries the Out / Doubtful / Questionable / Probable distinction
the blueprint requires, rather than the actual-absence proxy that would leak.
The header line carries a finer report time (05:30 PM) than the filename slot.

## Archiving

```bash
python scripts/archive_injury_reports.py --start 2025-10-21 --end 2025-12-31 \
  --out data/injury-archive --hours 11AM,01PM,05PM,06PM,07PM,08PM \
  --max-files 200 --sleep 1.0
```

Stores PDFs verbatim with a JSONL index recording URL, report date and hour,
retrieval time, byte count and SHA-256. It never parses, so later parsing changes
can be re-run against an unchanged record. Existing files are never refetched, so
the command is safe to repeat and resume; `--max-files` bounds each run. Be
polite with `--sleep`: a full backfill is tens of thousands of files, so archive
the slots and seasons you actually need rather than everything.

Add `--prospective` when capturing near real time; the index then marks those
files as prospective rather than backfilled.

## Parsing

Parsing needs `pdfplumber`, which is an optional extra rather than a core
dependency, since archiving and modelling do not require it:

```bash
python -m pip install -e '.[pdf]'
sports parse-injuries --archive data/injury-archive --out data/injury-archive/parsed.csv
```

Resumable: already-parsed reports are skipped, so an interrupted run continues
and a repeat run is a no-op. A malformed PDF is recorded in `failures` and never
loses the work already written. Delete the CSV to reparse everything after a
parser change. `--limit` and `--time-budget` bound a single run.

Parsing roughly 1,200 reports takes about ten minutes.

## The caveat that decides what this data can support

A file fetched today for a game in 2023 proves the report **exists**, not that it
was **visible before that game**. The filename hour is the NBA's nominal slot and
the header carries a report time, but neither is a verified publication timestamp
observed by this project, and the CDN may serve a later revision under an earlier
name. So:

- **Backfilled reports support research**: feature development, ablations, and
  building the annotated corpus the evidence agents need.
- **Only prospectively captured reports support an availability-at-cutoff claim**,
  because only then did we observe the file before the game.

The index records which mode each file came from so the two can never be silently
mixed. Treat backfilled availability features the same way this project treats
closing odds: useful for development, not evidence about what was obtainable.

Confirm the NBA's terms of use before large-scale or repeated retrieval.

## What this changes

Availability is the model's largest omission and the most plausible source of the
market's advantage over it. It is now buildable retrospectively across the
training window, and the annotated extraction corpus that §14 requires for the
evidence agents already exists rather than needing a season to accumulate. Both
were previously blocked on data that turns out to be free.

## Development result: availability counts DO help

Archived 1,203 daily reports (the 05:30 PM ET slot, Dec 2020 - Jun 2025), parsed
into 98,514 typed rows, and compared base features against base plus five
declared-availability differentials (out, doubtful, questionable, probable, not
submitted) and a coverage indicator, on the three existing development folds.

| Feature set | Log loss | Brier | Accuracy |
|---|---|---|---|
| base (11) | 0.621258 | 0.216074 | 65.26% |
| base + availability (17) | 0.617948 | 0.214537 | **66.12%** |

Pooled **-0.003311**, improving in all three folds:

| Fold | Base | Extended | Difference | 95% block interval |
|---|---|---|---|---|
| 2022-23 | 0.647034 | 0.645326 | -0.001708 | [-0.009326, +0.005578] |
| 2023-24 | 0.609683 | 0.606388 | -0.003295 | [-0.008565, +0.002054] |
| 2024-25 | 0.607059 | 0.602131 | -0.004928 | [-0.010097, -0.000384] excludes zero |

For scale, the entire calibrated-logistic advantage over Elo was -0.008525 on the
2025-26 holdout. Availability counts add roughly another third of that. Unlike the
box-score extension, log loss and accuracy improve together, and the effect grows
across folds rather than wandering.

Coverage is 99.98% of development games, and unweighted counts ignore player
impact entirely - a star and a two-way contract count the same - so this is a
floor on what availability information is worth, not a ceiling.

Two parser defects were found and fixed while producing this, both of which had
silently corrupted the first run:

1. Reports before roughly 2023 space their fields; later ones squash them.
   Matching is now anchored on the comma-bearing player name and the status
   keyword, so both layouts parse identically.
2. A spaced surname suffix ("Porter Jr., Michael") was splitting, leaving "Porter"
   as the team. That mismapped 10,413 of 98,514 rows; after the fix, 31 remain
   (0.03%), almost all the legitimate "Non-NBA Team" designation.

## What this does not yet justify

These reports were BACKFILLED. They support development, and they do not
establish what was visible before a past game. Adopting availability features for
2026-27 therefore requires prospective capture from opening night - the same
report, fetched before each cutoff and marked `prospective` in the index - and a
NEW frozen release, since the forecast surface changes.
