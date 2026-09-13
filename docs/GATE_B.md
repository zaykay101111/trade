# Gate B pre-registration — model versus the market at the cutoff

Written 2026-09-13, **before any qualifying data exists**. The 2026-27 season
has not started, so no T-60 odds have been collected and no game can yet be
scored. Recording the rule now is the whole point: it cannot be tuned after
seeing the answer.

Nothing in this document establishes an edge, an ROI, an executable price or
profitability. Forecasting gains do not establish a betting edge.

## Question

On the same games, at the same cutoff, does the frozen model forecast the
outcome better than the recalibrated de-vigged market reference?

## Data admitted

A game enters Gate B only if all of the following hold. No exceptions, and no
post-hoc additions.

1. The forecast was issued by the frozen release strictly before T-60, recorded
   once, never backdated (`collect-poll`, immutable snapshot).
2. A market reference was built at that same cutoff from **at least three
   books, excluding the execution book from its own reference**, by
   proportional de-vig (`u = 1/d`, `q = u/Σu`), taking the median.
   Abstentions are excluded and counted, never imputed.
3. The provider event mapped to a canonical NBA game id with no ambiguity.
   Quarantined events are excluded and counted.
4. The result settled normally.

**Closing odds are not admissible.** An archived or later quote does not prove
a price was obtainable at the cutoff. Only quotes retrieved before T-60, with
the book's own `last_update` recorded alongside our retrieval time, qualify.

## Market recalibration

The de-vigged median is a probability estimate, not a calibrated forecast.
Before comparison it is recalibrated with the same one-parameter logistic
recalibration used elsewhere (`fit_calibration`), fitted on a **disjoint
earlier block** of admitted games and applied forward. Recalibrating on the
games being scored would leak.

If too few games exist for a disjoint fit, Gate B does not run. It does not
fall back to raw de-vigged probabilities.

## Metric and decision rule

- Primary: **paired per-game log-loss difference**, market minus model, over
  the identical admitted set.
- Uncertainty: **seven-day block bootstrap**, matching the odds-free track.
- **Advance only if the relative improvement is ≥ 0.25% AND the 95% interval
  lies entirely above zero.**

Relative improvement is `(market_log_loss − model_log_loss) / market_log_loss`.
Both conditions are required; either alone is insufficient.

Also reported, never as the decision criterion: Brier score, calibration curve
with ECE, admitted/abstained/quarantined counts, and the same comparison on
the raw (non-recalibrated) market as a sensitivity check.

## One use

Gate B is evaluated **once** on the first qualifying block of the 2026-27
season, against a candidate frozen before opening night. Re-running it after
seeing the result, on a longer window, or with a different candidate, is a new
experiment and must be labelled as such. Repeated evaluation of the same
question on accumulating data inflates the false-positive rate; the interval
above assumes a single look.

The 2025-26 holdout is spent and cannot be reused here.

## If Gate B fails

The market is not beaten. No selection policy is built, no stake is sized, and
no wager is paper-recorded. The honest outcome is that the forecasting
advantage over Elo does not survive contact with a price — which is the
expected result, since a bookmaker line already embeds injuries, lineups and
sharp money that the odds-free model never sees.

## If Gate B clears

Only then does blueprint section 16 apply: conservative probability, threshold
tau, minimum price, one position per game, as **paper records** with
block-bootstrap intervals. No stake sizing before that point, and no real
wager without explicit authorization.

## Status

**NOT RUN. No admissible data exists.** Blocked until the 2026-27 season
produces settled games with T-60 odds collected by the live collector.
