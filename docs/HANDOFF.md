# Handoff — current goal and state

Written 2026-09-13. The goal is first; the state a fresh session needs is below it.
The previous, narrative version is kept at `docs/HANDOFF_prior.md`.

---

# CURRENT GOAL — NFL first

The NFL season is live now; the NBA does not open until 2026-10-20. Get live
prices recorded beside the paired forecasts that are already being issued, so
the 2026 NFL season can answer which of control and challenger is better, and
whether either beats the market.

## Ordered work

1. **Audit the NFL track before trusting it.** It was written in one commit
   (`0d8d451`) and has not been independently reviewed. Verify no future
   information can reach a forecast, that recorded snapshots are immutable and
   never backdated, and that ties are handled correctly in both the probability
   and the push arithmetic. Report what you find, including anything wrong.
2. **Add odds capture to the NFL poll at the SAME cutoff as the forecast.**
   Store each book's own `last_update` separately from our retrieval time. One
   request costs markets x regions; 115 remaining kickoffs is ~115 credits for
   the season against a 500/month cap.
3. **Market reference.** Proportional de-vig (`u = 1/d`, `q = u/Σu`), median of
   at least three books, execution book excluded from its own reference, abstain
   below three and record why. NFL moneyline is two-way with a PUSH, so de-vig
   must not silently assume the two prices span the whole outcome space.
4. **Schedule the poll** so every remaining kickoff is covered. Prove one full
   game day end to end before relying on it.
5. **Weekly:** settle, then report control vs challenger vs market on decided
   games only, with week-block intervals. Report negative results as prominently
   as positive ones.

## Constraints

- Free tier only. No paid calls, subscriptions or betting without explicit
  authorisation. `ODDS_API_KEY` is in the environment: read from `os.environ`
  only, never print or commit it.
- Never place, recommend or simulate as real any wager. Paper records only.
- **Do not open the 2025 NFL holdout.** The criteria to do so were not met.
- **Do not change the NBA forecast surface** (`free_data`, `model`, `collect`,
  `io`). The frozen NBA release must stay valid for 2026-10-20.
- Preserve existing data and runs; always write to new output directories.
- Run `pytest` before and after. Add tests for leakage, ties, quota, duplicate
  polls, and immutability of recorded snapshots.

## Honest limit

272 NFL games a season against 1,230 NBA. One NFL season cannot establish an
edge — it can show the pipeline works live, and it can rule the model out. Say
so in every report.

---

# STATE

## NFL (verified 2026-09-13)

- 6,991 games, 2000–2027. Contract: `nfl_regular_fullgame_moneyline_ot_tie_push`
  — a tie returns the stake.
- Development folds 2022–24; **2025 RESERVED**; 2026 prospective.
- **The challenger FAILED its pre-registered advancement criteria.** Pooled
  decided log loss 0.644140 vs Elo 0.659247, but Elo wins the 2024 fold
  (0.622441 vs 0.632872) and the paired interval [−0.030797, +0.000159] includes
  zero. `Advancement criteria met: False (stronger baseline: elo)`. Elo is the
  stronger baseline. The challenger is not the deployed model.
- Paired prospective recording is LIVE: snapshots in
  `collection/nfl-pair-v1/recorded`, control and challenger three-way
  probabilities, issued at kickoff minus 60.
- 262 of 272 games remain, across 115 distinct kickoff times.
- Commands: `nfl-train`, `nfl-compare-qb`, `nfl-freeze`, `nfl-collect-init`,
  `nfl-collect-refresh`, `nfl-poll`, `nfl-status`, `nfl-settle`.

## NBA

- Odds-free forecaster complete. The single reserved holdout (2025-26) was
  pre-registered, frozen and **spent once**: calibrated logistic 0.606802 vs Elo
  0.615328, difference −0.008525, 95% block interval [−0.016040, −0.001502],
  excludes zero. Development had predicted −0.0088.
- 2025-26 is now development data. Next clean confirmatory season is 2026-27.
- Availability features (injury-report status counts) confirmed on two machines:
  pooled **−0.003311**, improving in all three folds, 2024-25 excluding zero.
  **Not yet adopted** — adoption needs a new frozen release and prospective
  capture from opening night, since backfilled reports cannot establish what was
  visible before a game. Counts are unweighted, so this is a floor;
  `player_impact.py` is the right next step.
- Box-score features tested and **REJECTED**: pooled +0.000789, worse.
- `runs/release-2026-27-v2` is VALID (forecast surface `393f959d…`).
  `runs/release-2026-27` is stale — delete it.
- `collection/2026-27`: 1,200 games, 6 Cup rows awaiting team assignment, 773
  planned polls, **0 executed**.
- Injury archive: 1,215 reports, ~2019-01 to 2025-12, retrievable for past dates.
- **Deadline 2026-10-20.** Anything frozen after opening night cannot count for
  the 2026-27 season.

## Shared

- One live odds payload captured: `data/raw/odds-live-20260913T193307Z`, 41 NBA
  events, h2h, 5 books. Ingestion path proven; **no prices collected at a
  decision cutoff yet**.
- Events in that sample carry 1–5 books. The reference rule needs ≥3 excluding
  the execution book, so thin events will abstain. Re-measure closer to the season.
- `docs/GATE_B.md` is the Gate B pre-registration, written before qualifying data
  existed. Commit it — an uncommitted pre-registration has no verifiable timestamp.
- Remote: github.com/zaykay101111/trade.

## Open decisions

1. Adopt availability into the NBA candidate? Recommended yes.
2. Execution book label — needed only as a string, no account required.
3. $59/$119 odds backfill — not authorised.
4. Commit the untracked work; delete the stale release.

## Bugs found and fixed (worth knowing)

Provider status codes marking four whole seasons as postponed; a year-2999
timestamp pandas cannot represent; polls keyed by wall-clock time that would
have double-charged the quota; a drift gate broad enough to halt a season;
NBA Cup rows with team id 0; mixed timestamp spellings; two injury-report
layouts; surname suffixes mismapping 10.6% of rows; an undeclared dependency
reported once per file; and a refactor that silently changed a headline result
from −0.0033 to −0.0024.

**That last one was caught only because two machines disagreed.** Reproduce
results independently before trusting them.

## What is NOT established

No market edge, no ROI, no executable price, no profitability, nothing wagered,
nothing paid for. Forecasting gains do not establish a betting edge.
