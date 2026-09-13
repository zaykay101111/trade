"""NFL point-in-time features and the tie-aware outcome contract.

Deliberately OUTSIDE the NBA forecast surface (free_data/model/collect/io). NFL
work must never change what a deployed NBA forecast means, so this module owns
its own loader, features and outcome definition rather than widening the NBA
ones. Shared numerics are imported from model.py, not copied.

## Outcome contract (the part that is NOT the NBA's)

NBA asserts final games cannot be tied. NFL regular-season games can: 15 of
6,969 played games (0.215%) across 12 seasons in the verified feed. A binary
home-win model is therefore not a valid description of the outcome space.

We model the three-outcome distribution as a product of two pieces:

    P(tie)                    - a shrunk base rate estimated on training games
    P(home win | not a tie)   - the fitted binary model
    P(home) = (1 - P(tie)) * P(home win | not a tie)
    P(away) = (1 - P(tie)) * (1 - P(home win | not a tie))

This keeps the three probabilities summing to one while letting the binary
model do the work it is actually able to do. Fitting a three-class model
directly on 15 positive examples would estimate the tie class from noise.

The market being forecast is the two-way moneyline, where US books settle a
tie as a PUSH (stake returned). So the tie probability is not a nuisance to be
dropped: it scales the stake at risk and belongs in the EV calculation.
"""
from collections import defaultdict, deque

import numpy as np
import pandas as pd

# Small and defensible, chosen a priori. div_game and neutral come free with the
# schedule; no weather, because the feed's temp/wind are post-hoc observations
# rather than pregame forecasts and would leak.
NFL_FEATURES = ["margin_diff", "scored_diff", "allowed_diff", "win_rate_diff",
                "history_count_diff", "home_rest", "away_rest", "elo_diff",
                "neutral", "div_game"]

# A priori Elo constants; not tuned on the development folds.
ELO_K = 20.
ELO_SCALE = 400.
ELO_HOME = 55.
HISTORY_WINDOW = 10
MAX_REST_DAYS = 21.
CONTRACT = "nfl_regular_fullgame_moneyline_ot_tie_push"


def load_nfl_games(data):
    """Load and validate an NFL dataset. Unplayed games are excluded here."""
    from pathlib import Path
    data = Path(data)
    games = pd.read_csv(data/"games.csv", dtype={"game_id": str, "home_id": str, "away_id": str})
    results = pd.read_csv(data/"results.csv", dtype={"game_id": str})
    for frame in (games, results):
        if frame.game_id.isna().any() or frame.game_id.duplicated().any():
            raise ValueError("Missing or duplicate game IDs")
    if not set(results.game_id).issubset(set(games.game_id)):
        raise ValueError("Results contain games absent from the schedule")
    df = games.merge(results, on="game_id", validate="one_to_one", how="inner")
    for col in ("scheduled_at", "decision_at", "available_at", "schedule_observed_at"):
        df[col] = pd.to_datetime(df[col], utc=True, errors="raise")
        if df[col].isna().any():
            raise ValueError(f"Missing timestamp: {col}")
    if (df.decision_at >= df.scheduled_at).any() or (df.available_at <= df.scheduled_at).any():
        raise ValueError("Invalid decision/result availability ordering")
    if (df.schedule_observed_at > df.decision_at).any():
        raise ValueError("Schedule observed after decision cutoff")
    if df[["home_id", "away_id"]].isna().any().any() or (df.home_id == df.away_id).any():
        raise ValueError("Invalid team IDs")
    scores = df[["home_score", "away_score"]].to_numpy(dtype=float)
    if not np.isfinite(scores).all() or (scores < 0).any() or (scores != np.floor(scores)).any():
        raise ValueError("Scores must be finite nonnegative integers")
    if not df.season_type.eq("regular").all():
        raise ValueError("This track requires regular-season games")
    if not df.contract.eq(CONTRACT).all():
        raise ValueError(f"Every row must declare the {CONTRACT} contract")
    neutral = df.is_neutral.astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0})
    if neutral.isna().any():
        raise ValueError("Invalid neutral-site flag")
    df["neutral"] = neutral.astype(int)
    df["div_game"] = df.div_game.fillna(0).astype(int)
    # Ties are legal here; y is defined only for decided games and is_tie carries
    # the rest. Nothing downstream may assume y covers the whole outcome space.
    df["is_tie"] = (df.home_score == df.away_score).astype(int)
    df["y"] = (df.home_score > df.away_score).astype(int)
    df["elo_score"] = np.where(df.is_tie.eq(1), .5, df.y.astype(float))
    return df.sort_values(["decision_at", "game_id"]).reset_index(drop=True)


def build_nfl_features(df):
    """Reveal a result only strictly before a decision, in availability order.

    Elo K=20, scale=400, home advantage=55, ties scoring 0.5. Rolling window is
    the last 10 settled games per team with no season reset. Rest is elapsed
    days since that team's previous kickoff, capped at 21 (bye weeks).
    """
    decisions = df.sort_values(["decision_at", "game_id"])
    events = list(df.sort_values(["available_at", "game_id"]).itertuples())
    starts = list(df.sort_values(["scheduled_at", "game_id"]).itertuples())
    histories = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW))
    ratings = defaultdict(lambda: 1500.)
    last_start = {}
    output = []
    ei = si = 0
    for row in decisions.itertuples():
        while ei < len(events) and events[ei].available_at < row.decision_at:
            e = events[ei]
            expected = 1/(1+10**(-(ratings[e.home_id]-ratings[e.away_id]
                                   + ELO_HOME*(1-e.neutral))/ELO_SCALE))
            delta = ELO_K*(e.elo_score-expected)
            ratings[e.home_id] += delta
            ratings[e.away_id] -= delta
            histories[e.home_id].append((e.home_score, e.away_score, e.elo_score))
            histories[e.away_id].append((e.away_score, e.home_score, 1-e.elo_score))
            ei += 1
        while si < len(starts) and starts[si].scheduled_at < row.decision_at:
            e = starts[si]
            last_start[e.home_id] = last_start[e.away_id] = e.scheduled_at
            si += 1

        def stats(team):
            h = list(histories[team])
            if not h:
                return np.array([0., 0., 0., .5, 0.])
            a = np.array(h, dtype=float)
            return np.array([(a[:, 0]-a[:, 1]).mean(), a[:, 0].mean(), a[:, 1].mean(),
                             a[:, 2].mean(), len(h)])

        diff = stats(row.home_id)-stats(row.away_id)
        rests = [min(MAX_REST_DAYS, (row.scheduled_at-last_start[t]).total_seconds()/86400)
                 if t in last_start else MAX_REST_DAYS for t in (row.home_id, row.away_id)]
        elo_diff = ratings[row.home_id]-ratings[row.away_id]
        values = [*diff, *rests, elo_diff, row.neutral, row.div_game]
        output.append({"game_id": row.game_id, "season": row.season,
                       "decision_at": row.decision_at, "available_at": row.available_at,
                       "y": row.y, "is_tie": row.is_tie,
                       "p_elo": 1/(1+10**(-(elo_diff+ELO_HOME*(1-row.neutral))/ELO_SCALE)),
                       **dict(zip(NFL_FEATURES, values))})
    return pd.DataFrame(output)


def tie_rate(frame, prior_rate=.002, prior_weight=500.):
    """Shrunk tie base rate. Estimated on TRAINING rows only, never validation.

    With roughly two ties per thousand games, an unshrunk seasonal estimate is
    dominated by whether a rare event happened to land in the window. The prior
    is the long-run rate over the verified feed; prior_weight is deliberately
    large relative to a season so a tie-free training window cannot drive the
    probability to zero (which would make a tie infinitely surprising).
    """
    ties = float(frame.is_tie.sum())
    return float((ties+prior_rate*prior_weight)/(len(frame)+prior_weight))


def three_way(p_home_given_decided, p_tie):
    """Assemble the full outcome distribution; rows sum to one by construction."""
    p_home_given_decided = np.clip(np.asarray(p_home_given_decided, float), 1e-9, 1-1e-9)
    # p_tie may be a single frozen base rate or a per-game array.
    p_tie = np.broadcast_to(np.clip(np.asarray(p_tie, float), 0., .5),
                            p_home_given_decided.shape)
    decided = 1-p_tie
    return np.column_stack([decided*(1-p_home_given_decided), p_tie,
                            decided*p_home_given_decided])


def three_way_metrics(frame, p_home_given_decided, p_tie):
    """Metrics over the true three-outcome space, plus the decided-only view.

    Reporting only the binary number would quietly drop tied games and flatter
    the model; reporting only the three-way number would hide that essentially
    all of the signal lives in the decided games. Both are returned.
    """
    probabilities = three_way(p_home_given_decided, p_tie)
    is_tie = frame.is_tie.to_numpy().astype(bool)
    y = frame.y.to_numpy()
    index = np.where(is_tie, 1, np.where(y == 1, 2, 0))
    chosen = probabilities[np.arange(len(index)), index]
    onehot = np.zeros_like(probabilities)
    onehot[np.arange(len(index)), index] = 1.
    decided = ~is_tie
    binary = np.clip(np.asarray(p_home_given_decided, float)[decided], 1e-9, 1-1e-9)
    y_decided = y[decided]
    return {
        "games": int(len(frame)), "ties": int(is_tie.sum()),
        "three_way_log_loss": float(-np.log(np.clip(chosen, 1e-9, None)).mean()),
        "three_way_brier": float(((probabilities-onehot)**2).sum(axis=1).mean()),
        "decided_games": int(decided.sum()),
        "decided_log_loss": float(-(y_decided*np.log(binary)
                                    + (1-y_decided)*np.log1p(-binary)).mean()),
        "decided_brier": float(np.mean((binary-y_decided)**2)),
        "decided_accuracy": float(np.mean((binary >= .5) == y_decided)),
    }
