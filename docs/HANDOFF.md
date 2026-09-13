# Session handoff — 2026-09-13

## State in one paragraph

The odds-free NBA forecasting track is complete and its single reserved holdout
has been spent: the frozen logistic candidate beat Elo on 2025-26 by 0.008525 log
loss with an interval excluding zero. The project now has a prospective
collection workflow ready for the 2026-27 season (opens 2026-10-20), a verified
free source of historical injury reports, and a development result showing
availability features help. No odds data exists in the project, no edge has been
measured against any market, and nothing has been wagered or paid for.

## What was done this session

### 1. Final holdout protocol, then the holdout itself
- `docs/FINAL_PROTOCOL.md` — pre-registration: frozen candidate, chronology,
  metric plan, freeze/one-use rules, and the four decisions taken.
- `free_final.py` + `freeze-final` / `evaluate-final`. Guards: explicit
  confirmation flag, code/data drift refusal, consumption marker claimed before
  any label is read, no directory reuse, saved-model replay check, and a
  `--dry-run` that fits everything and writes predictions with no outcome read.
- **Result (one use, consumed):** calibrated logistic 0.606802 vs Elo 0.615328;
  logistic − Elo −0.008525, 95% block interval [−0.016040, −0.001502], excludes
  zero. Boosted − Elo includes zero. Replay difference 0.00e+00.
- Development had predicted −0.0088; the holdout delivered −0.008525. The
  method's own forecast of its out-of-sample performance held.

### 2. External replication (Walsh & Joshi, arXiv:2303.06021)
- `free_external.py` + `replicate-external`; `docs/PAPER_ERA_COMPARISON.md`.
- New dataset `nba-paper-era-v2` (2014-15…2018-19, 6,150 games) built from
  nba_api, with scores from the schedule payload after verifying equivalence to
  team logs on nba-v3 at 7,230/7,230, zero mismatches.
- **Findings:** the constant home-rate predictor has the *lowest* ECE of any
  model in both evaluated seasons (0.0103 and 0.0006) while being the worst
  forecaster — the paper's selection metric would pick a useless model, which is
  why they needed an admittedly arbitrary constraint. Log loss, already used
  here, is the principled alternative. Their headline also fails their own
  significance test (p=0.153). In their era our features add nothing over Elo.

### 3. Prospective collection (the October 20 deadline)
- `collect.py` + `collect-init` / `collect-refresh` / `collect-poll` /
  `collect-status`, and `freeze-release` to produce a deployment bundle.
- Records per poll: model probability, every book's two-sided price, de-vigged
  probability and overround, a median reference excluding the execution book, the
  raw payload, quota headers, and **each book's own `last_update` stored
  separately from our retrieval time** — the distinction that makes a T−60 claim
  defensible at all.
- Collection only: no EV, stake, admission or wager is computed, asserted by test.
- Guards: pending placeholder scores cannot reach features (year-2200
  availability sentinel), polls keyed to the cutoff they serve so a scheduler
  firing repeatedly costs one request, late polls collect nothing, thin book
  coverage abstains, forecast-surface drift halts forecasting.
- `settle.py` + `merge-settled` folds newly completed games into a new dataset so
  Elo and rolling windows keep advancing through the season.
- **2026-27 plan:** 1,200 games collectible, 6 Cup rows held back pending team
  assignment, 773 poll times, peak 162 credits/month against a 500 free cap.

### 4. Data sourcing costs
- `docs/DATA_SOURCING.md`, priced from measured volume (4,457 distinct tip times
  across six seasons, not an estimate).
- Prospective collection is free. A one-month historical backfill is $59 for US
  books at T−60, or $119 for the three-region paired-snapshot design already in
  `data/odds-plan.json`. One-off; the data may be kept after cancelling.
- Free historical closing odds exist (2007-08…2022-23) but are single-source and
  untimestamped: literature comparison only.

### 5. Features tested
- **Box-score extension (9 possession-adjusted features): rejected.** Pooled
  +0.000789 log loss (worse) over 3,690 development games, every fold interval
  including zero, while accuracy rose 65.26% → 65.50%. Selecting on accuracy would
  have adopted a worse forecaster.
- **Availability (declared injury status): helps.** See below.

### 6. Injury reports — the significant finding
- Official NBA injury report PDFs are retrievable **for past dates**, hourly,
  roughly 2019-01 to 2025-12 (2026 dates return 403 at every hour swept). This
  corrects an earlier assumption that injury history could only be captured
  forward. Structured, machine-readable, with Out/Doubtful/Questionable/Probable
  rather than the actual-absence proxy that would leak.
- `scripts/archive_injury_reports.py` stores PDFs verbatim with a hashed index and
  records whether each file was backfilled or captured prospectively.
- `injury.py` + `parse-injuries` / `compare-availability`.
- **Development result (pending re-run, see below):** base 0.621258 vs 0.617948
  with availability, pooled −0.003311, improving in all three folds, 2024-25
  excluding zero. Accuracy 65.26% → 66.12%. Counts are unweighted — no player
  impact data — so this is a floor on the feature group's value.

## Bugs found and fixed this session

| Bug | Consequence | Status |
|---|---|---|
| `postponedStatus='A'` on four whole seasons of 2014-19 schedules | 4 of 5 seasons dropped; only 1,230 of 6,150 games downloaded | diagnosed season by season, `--include-postponed` used with evidence |
| Year-2999 availability sentinel | pandas cannot represent it; collector crashed | moved to 2200 |
| Polls keyed by wall-clock time | a cron firing every 5 min would buy the same snapshot repeatedly | keyed to the cutoff served |
| Drift gate covering the whole package | an unrelated research edit would halt a nine-month collection | gated on the forecast surface only |
| `collect-init` planning polls for NBA Cup rows with team id 0 | would forecast games with no teams | held back in `pending_assignment.csv`; `collect-refresh` added |
| Mixed ISO/space timestamps across merged CSVs | strict parsing failed | normalised on write; loader untouched |
| Injury parser: two report layouts | pre-2023 reports parsed to zero rows | anchored on player + status, both layouts |
| Injury parser: spaced surname suffixes | "Porter Jr., Michael" left "Porter" as the team; 10,413 of 98,514 rows mismapped | fixed, 31 remain (legitimate "Non-NBA Team") |
| `pdfplumber` undeclared, ImportError caught per file | one missing module reported 1,215 times | declared as `[pdf]` extra, fail-fast |
| **`parse_lines` refactor reset state per page** | matchup lost at every page break; 98,514 rows → 81,605; availability result weakened −0.0033 → −0.0024 | fixed, single-pass parse, regression test added |

The last one is the important one: a refactor done for testability silently
changed a headline result. It was caught only because Kyler's run disagreed with
mine on the same files. **Both numbers were reported before the disagreement was
understood — the −0.0024 figure is from the broken parser and should be discarded.**

## Immediate next step

Re-run the availability comparison with the fixed parser:

```bash
source .venv/bin/activate
python -m pytest -q                       # expect 88
rm data/injury-archive/parsed.csv
sports parse-injuries --archive data/injury-archive --out data/injury-archive/parsed.csv
sports compare-availability --data data/normalized/nba-v3 --reports data/injury-archive/parsed.csv \
  --team-log data/raw/nba-team-games.csv --out runs/avail-v2 --threads 2
```

Expect roughly 98,500 rows and pooled ≈ −0.0033. Confirm before adopting.

## Open decisions (all blocking)

1. **Adopt availability into the frozen candidate?** Recommended yes, pending the
   re-run. Requires a NEW frozen release and prospective capture from opening
   night, because backfilled reports cannot establish what was visible before a
   game.
2. **Free Odds API key** (the-odds-api.com, no card) — only Kyler can create it.
3. **Execution book** — whichever he would actually bet at.
4. **$59/$119 odds backfill** — not authorised. Would make the market-residual
   model trainable before opening night and answer Gate B retrospectively.
5. **GitHub** — 19 commits, still local only, no remote.

## Deadline

**2026-10-20.** Required before it: results-refresh loop wired, collector live
with cron, and a candidate frozen. Anything not frozen before opening night
cannot count for the 2026-27 season.

## What is still NOT established

No market edge, no ROI, no executable price, nothing wagered, nothing paid. The
2025-26 holdout is spent and cannot be reused. The paper-era and development
folds have been inspected repeatedly and are development evidence only. The next
clean confirmatory season is 2026-27, and only if a candidate is frozen first.
