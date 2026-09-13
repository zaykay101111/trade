# Player-impact research candidate (impact-v1)

Separate research track. Nothing here is in the frozen baseline, the injury
challenger pair, or any prospective record.

## Data

`scripts/download_player_logs.py` fetched 154,346 player-game rows
(2020-21…2025-26) from the free nba_api LeagueGameLog player endpoint into
`data/raw/player-logs/`. Cached per season; reruns rebuild the CSV from caches.

## Feature construction (`player_impact.py`)

For each game side whose injury snapshot is usable, every listed
Out/Doubtful/Questionable/Probable player contributes their mean minutes over
their last 10 games — counting only games whose RESULTS were available before
the cutoff (joined by game id to the dataset's `available_at`, so the previous
night's minutes are excluded when not yet available). Features are home-minus-
away sums per status, Out scoring, and an unmatched-listed-player count.
Availability remains declared-status only; actual absence is never used. Names
match via normalization ("Porter Jr., Michael" → "michael porter jr") plus the
report team's id; listed-player match rate 84.2% (45,479 matched, 8,562
unmatched — unmatched players contribute zero minutes and are counted).

## Development result (`runs/impact-v1`) — NOT confirmation

Impact minus availability-extended log loss, same folds as avail-v3:

| Fold | Extended | +Impact | Difference |
|---|---|---|---|
| 2022-23 | 0.642964 | 0.639225 | −0.003738 (includes zero) |
| 2023-24 | 0.606161 | 0.602526 | −0.003635 (includes zero) |
| 2024-25 | 0.602443 | 0.594424 | −0.008019 (excludes zero) |
| pooled | — | — | **−0.005131** |

This stacks on top of availability's own −0.0041 (avail-v3), i.e. weighting
declared statuses by historical minutes roughly doubles the feature group's
development value. Backfilled reports, repeatedly inspected folds: development
evidence only. Adoption would require a new frozen release, prospective injury
capture, and prospective player-log refresh discipline — none of which is
implied by this run. The consumed 2025-26 holdout must not be used to confirm
it.

## Known weaknesses

- 15.8% of listed players don't match a log row (rookies with no games,
  two-way players, name variants, mid-season trades restricting team-scoped
  history). They contribute zero minutes plus an unmatched count.
- Minutes are a crude impact proxy; no on/off or lineup data.
- One window (last 10 available games) was chosen a priori and not tuned;
  tuning it on these folds would be overfitting.
