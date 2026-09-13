# NFL prediction and settlement contract

Contract id: `nfl_regular_fullgame_moneyline_ot_tie_push`. Every NFL row
declares it and `load_nfl_games` refuses a dataset that does not.

## Market and scope

Two-way, full-game moneyline, regular season only, overtime included. College,
preseason, playoffs, spreads, totals and props are excluded at download time,
in `download_nfl.py`, so they cannot leak into a dataset downstream.

## Cutoff

`decision_at` = kickoff − 60 minutes, matching the NBA track so the two sports
share one collection cadence. Kickoff is converted from the feed's US Eastern
`gameday`/`gametime` to UTC by us; the feed carries no timezone column, so the
conversion is our assumption. Ambiguous and non-existent local times (DST
transitions) resolve to the first occurrence and shift forward respectively.

## Outcome space — ties are real

Regular-season NFL games can end level: 15 of 6,969 played games (0.215%) in
the verified feed, across 12 seasons including 2022 and 2025. The NBA
invariant "final games cannot be tied" is therefore invalid here, and
`free_data.load_games` correctly refuses an NFL dataset (asserted by test).

Overtime does **not** guarantee a winner in the regular season, so `overtime`
is recorded but is not a tie-breaker.

The three-outcome distribution is factored rather than fitted directly:

```
P(tie)                  shrunk base rate, fitted data only
P(home | not a tie)     the binary logistic model
P(home) = (1 - P(tie)) * P(home | not a tie)
P(away) = (1 - P(tie)) * (1 - P(home | not a tie))
```

Fitting a three-class model on 15 positive examples would estimate the tie
class from noise. The tie rate is shrunk toward a 0.002 prior with weight 500,
so a tie-free fitting window cannot drive the probability to zero and make an
actual tie infinitely surprising. Elo scores a tie as 0.5.

Metrics are reported **both** ways, and neither alone is sufficient:
three-way log loss and Brier over all games (drops nothing), and decided-only
log loss, Brier and accuracy over non-tied games (comparable with the NBA
numbers). Reporting only the decided figures would quietly discard tied games.

## Settlement rules

| Event | Moneyline settlement | Implemented |
|---|---|---|
| Home/away win (incl. OT) | Win or lose normally | `nfl_policy.settle` |
| **Tie** | **Push — stake returned, profit 0** | `settle("tie", …) == 0` |
| Cancellation | Void — settles exactly as a push | `settle("void", …) == 0` |
| Postponement inside the book's action window | Bet stands to the replayed game | not automated |
| Postponement beyond the window | Void | treat as `"void"` |
| Neutral site | Normal settlement; home/away labels retained | `is_neutral` feature |

Per-stake transaction cost is charged even on a push or void, because the cost
is incurred on placement rather than on the result.

**Cancellations vanish from the feed rather than appearing with a null
result.** Verified: 2022 has 271 regular-season rows, all with results, and the
cancelled Bills–Bengals game is simply absent. A disappearing game id is
therefore the cancellation signal, and a settlement pass must treat an
issued forecast whose game id later vanishes as a void, not as a missing
result to wait on.

## Push-aware betting arithmetic

Reusing the NBA arithmetic unchanged would be wrong, because it assumes every
settled game pays out or loses:

```
EV  = p_win*(d-1) - p_lose - cost      with p_win + p_lose + p_push = 1
f*  = (p_win*(d-1) - p_lose) / (d-1)
```

Since `p_lose < 1 - p_win` whenever a push is possible, ignoring ties
understates EV and mis-sizes Kelly. The break-even price is
`d = (p_lose + cost)/p_win + 1`, verified exactly by test, and the Kelly
formula reduces to the familiar binary form when `p_push = 0`, also tested.

The probability haircut is applied to the winning probability only. The push
probability is not a claim about our edge, so it is not shaved.

## What this contract does not yet cover

Correlated exposure across same-game or same-week NFL bets, and automated
postponement handling, are not implemented. No odds source is connected, so no
NFL price has been observed and nothing has been staked.
