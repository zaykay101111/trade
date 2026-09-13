"""Frozen NFL release and immutable prospective paired forecasting.

Mirrors the NBA challenger discipline without touching it: exclusive-create
snapshots, a five-minute pre-cutoff window, no backdating on recorded runs, a
source-drift gate, and simulations kept in a separate directory from real
records.

Fitted parameters (logistic coefficients, calibrator, tie rate) come from
seasons before the calibration season, so the reserved 2025 holdout is never
used to FIT or to SCORE. Elo and rolling features are still computed from every
settled result available before each cutoff, including 2025 — that is feature
construction from pregame-available information, not holdout evaluation, and
withholding it would make the forecasts worse for no integrity gain.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import nfl_data
from .io import digest, new_dir, now, read_json, write_json
from .model import calibrate, predict_logistic
from .nfl_data import (NFL_FEATURES, build_nfl_features, load_nfl_games, three_way, tie_rate)
from .nfl_train import FINAL_HOLDOUT_SEASON, L2, fit_fold

FIT_THROUGH_SEASON = 2023
CALIBRATION_SEASON = 2024
PROTOCOL = (
    "Paired NFL prospective records. Control is Elo; challenger is the regularized "
    "logistic. Both score identical games. Development did NOT meet the prespecified "
    "advancement criteria (the challenger lost the 2024 fold to Elo and the pooled "
    "interval against Elo included zero), so this pair is a RESEARCH comparison "
    "collected prospectively, not a deployment. No stake, odds request or promotion. "
    "Ties settle as a push on the two-way moneyline. Record once per game inside the "
    "five minutes before T-60; never backdate or overwrite."
)


def surface():
    """Narrow NFL forecast surface. Independent of the NBA surface by design."""
    return {"nfl_data": digest(nfl_data.__file__),
            "nfl_collect": digest(__file__)}


def freeze_nfl(data, out, *, fit_through=FIT_THROUGH_SEASON, calibration_season=CALIBRATION_SEASON):
    """Freeze the NFL control/challenger pair. Scores nothing."""
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}")
    data = Path(data)
    games = load_nfl_games(data)
    if (games.season >= FINAL_HOLDOUT_SEASON).any():
        games = games[games.season < FINAL_HOLDOUT_SEASON].copy()
    features = build_nfl_features(games)
    fit = features[features.season <= fit_through]
    cal = features[features.season == calibration_season]
    if len(fit) < 200 or len(cal) < 100:
        raise ValueError("Insufficient fitting or calibration data")
    model, calibrator, _, _, rate = fit_fold(fit, cal, cal)
    bundle = {"version": Path(out).name, "sport": "nfl", "created_at": now(),
              "contract": nfl_data.CONTRACT, "surface": surface(),
              "features": list(NFL_FEATURES), "l2": L2,
              "logistic": model, "calibrator": calibrator, "tie_rate": rate,
              "fit_through_season": fit_through, "calibration_season": calibration_season,
              "reserved_holdout_season": FINAL_HOLDOUT_SEASON,
              "split_counts": {"fit": len(fit), "calibration": len(cal)},
              "elo": {"k": nfl_data.ELO_K, "scale": nfl_data.ELO_SCALE,
                      "home": nfl_data.ELO_HOME, "window": nfl_data.HISTORY_WINDOW},
              "sources": {f: digest(data/f) for f in ("games.csv", "results.csv")},
              "protocol": PROTOCOL}
    out = new_dir(out)
    write_json(out/"bundle.json", bundle)
    (out/"PASTE_BACK.md").write_text(
        "# Frozen NFL pair\n\n"+PROTOCOL+"\n\n"
        f"Fit games: {len(fit)} (through {fit_through}); calibration games: {len(cal)} "
        f"({calibration_season}).\nFrozen tie rate: {rate:.5f}. Features: {len(NFL_FEATURES)}.\n"
        f"Season {FINAL_HOLDOUT_SEASON} reserved and unread.\nNo season scored.\n")
    return {"run": str(out), "scored": False, "tie_rate": rate,
            "bundle_sha256": digest(out/"bundle.json")}


def init_nfl_collection(data, out, season):
    """Create a collection plan for one NFL season from the dataset schedule."""
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}")
    games = pd.read_csv(Path(data)/"games.csv", dtype={"game_id": str})
    season_games = games[games.season.astype(int) == int(season)].copy()
    if season_games.empty:
        raise ValueError(f"No games for season {season}")
    for column in ("scheduled_at", "decision_at", "schedule_observed_at"):
        season_games[column] = pd.to_datetime(season_games[column], utc=True)
    season_games = season_games.sort_values(["decision_at", "game_id"])
    out = new_dir(out)
    season_games.to_csv(out/"schedule.csv", index=False)
    meta = {"created_at": now(), "sport": "nfl", "season": int(season),
            "contract": nfl_data.CONTRACT, "games": len(season_games),
            "first_cutoff": str(season_games.decision_at.min()),
            "last_cutoff": str(season_games.decision_at.max()),
            "source_games_sha256": digest(Path(data)/"games.csv"),
            "warning": "Kickoff converted from US Eastern by us; the feed carries no "
                       "timezone or revision timestamp. Refresh the schedule as the "
                       "season progresses; flexed kickoffs move cutoffs."}
    write_json(out/"collection.json", meta)
    return {"collection": str(out), "games": len(season_games),
            "first_cutoff": meta["first_cutoff"]}


def refresh_nfl_collection(collection, data):
    """Fold an updated schedule in. Recorded snapshots are never touched.

    NFL kickoffs get flexed, so cutoffs move during a season. A game id that
    DISAPPEARS from the feed is a cancellation, not a data error, and is
    recorded as such rather than silently dropped.
    """
    collection = Path(collection)
    meta = read_json(collection/"collection.json")
    current = pd.read_csv(collection/"schedule.csv", dtype={"game_id": str})
    incoming = pd.read_csv(Path(data)/"games.csv", dtype={"game_id": str})
    incoming = incoming[incoming.season.astype(int) == int(meta["season"])].copy()
    for frame in (current, incoming):
        for column in ("scheduled_at", "decision_at", "schedule_observed_at"):
            frame[column] = pd.to_datetime(frame[column], utc=True)
    known = set(current.game_id)
    arriving = set(incoming.game_id)
    added = incoming[~incoming.game_id.isin(known)]
    vanished = current[~current.game_id.isin(arriving)]
    before = current.set_index("game_id").decision_at
    after = incoming.set_index("game_id").decision_at
    shared = sorted(known & arriving)
    moved = [{"game_id": g, "before": str(before[g]), "after": str(after[g])}
             for g in shared if before[g] != after[g]]
    incoming.sort_values(["decision_at", "game_id"]).to_csv(collection/"schedule.csv", index=False)
    record = {"at": now(), "added": added.game_id.tolist(),
              "cancelled_or_withdrawn": vanished.game_id.tolist(),
              "cutoff_revisions": moved,
              "source_games_sha256": digest(Path(data)/"games.csv")}
    with (collection/"revisions.jsonl").open("a") as stream:
        stream.write(json.dumps(record)+"\n")
    return {"collection": str(collection), "games": len(incoming),
            "added": len(record["added"]),
            "cancelled_or_withdrawn": len(record["cancelled_or_withdrawn"]),
            "cutoff_revisions": len(moved)}


def _pending_features(settled, targets):
    """Features for unplayed games, built from settled history only.

    The pending rows carry no scores, so they cannot enter anyone's history:
    build_nfl_features consumes results in availability order and a pending game
    has no result row at all.
    """
    overlap = set(targets.game_id) & set(settled.game_id)
    if overlap:
        raise ValueError(f"Target games already have settled results: {sorted(overlap)[:3]}")
    placeholder = targets.copy()
    placeholder["home_score"] = 0
    placeholder["away_score"] = 0
    placeholder["is_tie"] = 0
    placeholder["y"] = 0
    placeholder["elo_score"] = .5
    # A far-future availability keeps pending rows out of every history window.
    placeholder["available_at"] = pd.Timestamp("2200-01-01", tz="UTC")
    combined = pd.concat([settled, placeholder], ignore_index=True)
    built = build_nfl_features(combined)
    return built[built.game_id.isin(set(targets.game_id))].reset_index(drop=True)


def poll_nfl(collection, pair, data, out, at=None, record=False, window_minutes=5):
    """One paired NFL cycle. No network access. Simulation unless --record."""
    if record and at is not None:
        raise ValueError("Cannot backdate a recorded forecast with --at")
    actual = pd.Timestamp(now())
    issue = pd.to_datetime(at, utc=True) if at is not None else actual
    pair_file = Path(pair)/"bundle.json"
    bundle = read_json(pair_file)
    if bundle.get("surface") != surface():
        raise ValueError("NFL source drifted; freeze a new version")
    if bundle.get("contract") != nfl_data.CONTRACT:
        raise ValueError("Frozen bundle declares a different contract")
    if record and pd.Timestamp(bundle["created_at"]) >= issue:
        raise ValueError("Release must precede issuance")
    schedule_path = Path(collection)/"schedule.csv"
    schedule = pd.read_csv(schedule_path, dtype={"game_id": str, "home_id": str, "away_id": str})
    for column in ("scheduled_at", "decision_at", "schedule_observed_at"):
        schedule[column] = pd.to_datetime(schedule[column], utc=True)
    if schedule.game_id.duplicated().any():
        raise ValueError("Duplicate schedule IDs")
    targets = schedule[(schedule.decision_at >= issue)
                       & (schedule.decision_at <= issue+pd.Timedelta(minutes=window_minutes))].copy()
    if targets.empty:
        return {"games": 0, "sport": "nfl",
                "status": "No games in the pre-cutoff window"}
    if (targets.home_id == targets.away_id).any():
        raise ValueError("Identical teams")
    if (targets.schedule_observed_at > issue).any():
        raise ValueError("Schedule observation is later than issuance")
    root = Path(out)/("recorded" if record else "simulated")
    targets = targets[~targets.game_id.map(
        lambda g: (root/(hashlib.sha256(g.encode()).hexdigest()+".json")).exists())]
    if targets.empty:
        return {"games": 0, "sport": "nfl", "status": "Games already recorded"}
    settled = load_nfl_games(data)
    observed = targets.copy()
    # Features are cut at the ACTUAL observation time, not the still-future T-60.
    observed["decision_at"] = issue
    observed["neutral"] = observed.is_neutral.astype(str).str.lower().map(
        {"true": 1, "false": 0, "1": 1, "0": 0}).astype(int)
    observed["div_game"] = observed.div_game.fillna(0).astype(int)
    frame = _pending_features(settled, observed)
    columns = bundle["features"]
    raw = predict_logistic(bundle["logistic"],
                           frame[columns].to_numpy(dtype=float), np.full(len(frame), .5))
    p_challenger = calibrate(raw, bundle["calibrator"])
    p_control = frame.p_elo.to_numpy()
    p_tie = float(bundle["tie_rate"])
    provenance = {"pair_sha256": digest(pair_file), "schedule_sha256": digest(schedule_path),
                  "data_sha256": {f: digest(Path(data)/f) for f in ("games.csv", "results.csv")},
                  "surface": surface(), "settled_games_used": int(len(settled))}
    completed = pd.Timestamp(now()) if record else issue
    if (targets.decision_at < completed).any():
        raise ValueError("Calculation crossed T-60; no prospective forecasts recorded")
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    for position, row in enumerate(frame.to_dict("records")):
        game = targets[targets.game_id == row["game_id"]].iloc[0]
        control = three_way(np.array([p_control[position]]), p_tie)[0]
        challenger = three_way(np.array([p_challenger[position]]), p_tie)[0]
        payload = {
            "sport": "nfl", "contract": nfl_data.CONTRACT,
            "mode": "prospective" if record else "simulation",
            "issued_at": str(completed), "inputs_observed_at": str(issue),
            "game_id": row["game_id"], "season": int(game.season), "week": int(game.week),
            "home_id": game.home_id, "away_id": game.away_id,
            "scheduled_at": str(game.scheduled_at), "cutoff": str(game.decision_at),
            "predictions": {"p_control_home_given_decided": float(p_control[position]),
                            "p_challenger_home_given_decided": float(p_challenger[position]),
                            "p_tie": p_tie,
                            "control_three_way": {"away": float(control[0]), "tie": float(control[1]),
                                                  "home": float(control[2])},
                            "challenger_three_way": {"away": float(challenger[0]),
                                                     "tie": float(challenger[1]),
                                                     "home": float(challenger[2])}},
            "features": {k: float(row[k]) for k in columns},
            "provenance": provenance}
        path = root/(hashlib.sha256(row["game_id"].encode()).hexdigest()+".json")
        with path.open("x") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
        written += 1
    return {"games": written, "sport": "nfl",
            "mode": "prospective" if record else "simulation",
            "out": str(root), "network_requests": 0, "scored": False}
