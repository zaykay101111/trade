"""Point-in-time team features for the odds-free research track."""
from collections import defaultdict, deque
import numpy as np
import pandas as pd

FEATURES = ["margin_diff", "scored_diff", "allowed_diff", "win_rate_diff",
            "history_count_diff", "home_rest", "away_rest", "home_b2b",
            "away_b2b", "elo_diff", "neutral"]


def load_games(data):
    from pathlib import Path
    data = Path(data)
    games = pd.read_csv(data / "games.csv", dtype={"game_id": str, "home_id": str, "away_id": str})
    results = pd.read_csv(data / "results.csv", dtype={"game_id": str})
    for frame in (games, results):
        if frame.game_id.isna().any() or frame.game_id.duplicated().any():
            raise ValueError("Missing or duplicate game IDs")
    if set(games.game_id) != set(results.game_id):
        raise ValueError("Schedule and result IDs must match exactly")
    df = games.merge(results, on="game_id", validate="one_to_one")
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
    if (df.home_score == df.away_score).any():
        raise ValueError("Final NBA games cannot be tied")
    if not df.season_type.eq("regular").all() or not df.source_status.str.strip().str.startswith("Final").all():
        raise ValueError("This track requires completed regular-season games")
    neutral = df.is_neutral.astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0})
    if neutral.isna().any():
        raise ValueError("Invalid neutral-site flag")
    df["neutral"] = neutral.astype(int)
    df["y"] = (df.home_score > df.away_score).astype(int)
    return df.sort_values(["decision_at", "game_id"]).reset_index(drop=True)


def build_features(df):
    """Only reveal results strictly before a decision, in availability order.

    Elo K=20, scale=400, home advantage=65. Rolling window=20 settled
    games; no season reset. Rest is elapsed time since a previous start,
    capped at 14 days. Scores are points/game, not possession ratings.
    """
    decisions = df.sort_values(["decision_at", "game_id"])
    events = list(df.sort_values(["available_at", "game_id"]).itertuples())
    starts = list(df.sort_values(["scheduled_at", "game_id"]).itertuples())
    histories = defaultdict(lambda: deque(maxlen=20))
    ratings = defaultdict(lambda: 1500.)
    last_start = {}
    output = []
    ei = si = 0
    for row in decisions.itertuples():
        while ei < len(events) and events[ei].available_at < row.decision_at:
            e = events[ei]
            p = 1 / (1 + 10 ** (-(ratings[e.home_id] - ratings[e.away_id] + 65 * (1-e.neutral))/400))
            delta = 20 * (e.y-p)
            ratings[e.home_id] += delta
            ratings[e.away_id] -= delta
            histories[e.home_id].append((e.scheduled_at, e.home_score, e.away_score, e.y))
            histories[e.away_id].append((e.scheduled_at, e.away_score, e.home_score, 1-e.y))
            ei += 1
        while si < len(starts) and starts[si].scheduled_at < row.decision_at:
            e = starts[si]
            last_start[e.home_id] = last_start[e.away_id] = e.scheduled_at
            si += 1
        def stats(team):
            h = list(histories[team])
            if not h:
                return np.array([0., 0., 0., .5, 0.])
            a = np.array([[v[1], v[2], v[3]] for v in h], dtype=float)
            return np.array([(a[:,0]-a[:,1]).mean(), a[:,0].mean(), a[:,1].mean(), a[:,2].mean(), len(h)])
        diff = stats(row.home_id)-stats(row.away_id)
        rests = [min(14., (row.scheduled_at-last_start[t]).total_seconds()/86400)
                 if t in last_start else 14. for t in (row.home_id, row.away_id)]
        elo_diff = ratings[row.home_id]-ratings[row.away_id]
        values = [*diff, *rests, float(rests[0] < 1.5), float(rests[1] < 1.5), elo_diff, row.neutral]
        output.append({"game_id": row.game_id, "decision_at": row.decision_at,
                       "available_at": row.available_at, "y": row.y,
                       "p_elo": 1/(1+10**(-(elo_diff+65*(1-row.neutral))/400)),
                       **dict(zip(FEATURES, values))})
    return pd.DataFrame(output)
