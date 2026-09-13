"""Settlement and monitoring for NFL paired prospective records.

Outside every forecast surface: reads snapshots and settled results, never
issues a forecast, never modifies a recorded file. Reported separately from
NBA — the two sports have different outcome spaces, so pooling their metrics
would be meaningless and would hide poor performance in either.

NFL-specific settlement handled here and nowhere else:
  tie      -> a real outcome for scoring, and a PUSH for the moneyline
  void     -> a game id that vanished from the schedule feed (cancellation)
  pending  -> kicked off but no result yet, or not yet played
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .io import new_dir, now, write_json
from .nfl_data import load_nfl_games

OUTCOMES = ("away", "tie", "home")


def _load_snapshots(records, mode):
    root = Path(records)/mode
    snapshots = []
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        payload = json.loads(path.read_text())
        if hashlib.sha256(payload["game_id"].encode()).hexdigest() != path.stem:
            raise ValueError(f"Snapshot filename does not match its game: {path.name}")
        if payload.get("sport") != "nfl":
            raise ValueError(f"Non-NFL snapshot in an NFL record directory: {path.name}")
        snapshots.append(payload)
    return snapshots


def nfl_status(collection, records, at=None):
    """Coverage for NFL paired records. Reads only.

    A past cutoff with no snapshot is a MISSED game; recorded forecasts alone
    never establish coverage.
    """
    at = pd.to_datetime(at, utc=True) if at is not None else pd.Timestamp(now())
    schedule = pd.read_csv(Path(collection)/"schedule.csv", dtype={"game_id": str})
    schedule["decision_at"] = pd.to_datetime(schedule.decision_at, utc=True)
    root = Path(records)/"recorded"
    recorded = {p.stem for p in root.glob("*.json")} if root.exists() else set()
    past = schedule[schedule.decision_at < at]
    key = past.game_id.map(lambda g: hashlib.sha256(g.encode()).hexdigest())
    missed = past[~key.isin(recorded)]
    upcoming = schedule[schedule.decision_at >= at].decision_at
    return {"sport": "nfl", "as_of": str(at), "season": int(schedule.season.iloc[0]),
            "scheduled_games": len(schedule), "past_cutoffs": len(past),
            "recorded": len(recorded), "missed_games": int(len(missed)),
            "missed": missed[["game_id", "decision_at"]].astype(str).to_dict("records"),
            "next_cutoff": str(upcoming.min()) if len(upcoming) else None}


def _score(frame, column, p_tie):
    """Three-way and decided-only metrics for one model over settled games."""
    p_home_decided = np.clip(frame[column].to_numpy(float), 1e-9, 1-1e-9)
    p_tie = np.clip(frame[p_tie].to_numpy(float), 0., .5)
    decided = 1-p_tie
    probabilities = np.column_stack([decided*(1-p_home_decided), p_tie, decided*p_home_decided])
    index = frame.outcome_index.to_numpy()
    chosen = probabilities[np.arange(len(index)), index]
    onehot = np.zeros_like(probabilities)
    onehot[np.arange(len(index)), index] = 1.
    is_decided = index != 1
    binary = p_home_decided[is_decided]
    y = (index[is_decided] == 2).astype(float)
    bins = np.clip((binary*10).astype(int), 0, 9)
    calibration = [{"bin": int(b), "count": int((bins == b).sum()),
                    "mean_forecast": float(binary[bins == b].mean()),
                    "observed_rate": float(y[bins == b].mean())} for b in np.unique(bins)]
    ece = float(sum(c["count"]*abs(c["mean_forecast"]-c["observed_rate"])
                    for c in calibration)/max(1, len(binary)))
    return {"games": int(len(frame)), "ties": int((index == 1).sum()),
            "three_way_log_loss": float(-np.log(np.clip(chosen, 1e-9, None)).mean()),
            "three_way_brier": float(((probabilities-onehot)**2).sum(axis=1).mean()),
            "decided_games": int(is_decided.sum()),
            "decided_log_loss": float(-(y*np.log(binary)+(1-y)*np.log1p(-binary)).mean())
            if is_decided.any() else None,
            "decided_brier": float(np.mean((binary-y)**2)) if is_decided.any() else None,
            "decided_accuracy": float(np.mean((binary >= .5) == y)) if is_decided.any() else None,
            "ece_10bin": ece, "calibration": calibration}


def settle_nfl(records, collection, data, out, include_simulated=False):
    """Score settled NFL paired records. Descriptive only; no promotion."""
    from .nfl_train import paired_week_interval
    mode = "simulated" if include_simulated else "recorded"
    snapshots = _load_snapshots(records, mode)
    report = {"created_at": now(), "sport": "nfl", "mode": mode,
              "snapshots": len(snapshots),
              "warning": "Descriptive monitoring of frozen NFL models. No promotion, no odds, "
                         "no ROI. Development did not meet the advancement criteria, so this is "
                         "a research comparison. Simulated records are rehearsal and never "
                         "evidence. NBA and NFL metrics are never pooled."}
    report["coverage"] = nfl_status(collection, records)
    if not snapshots:
        report["status"] = "No snapshots to settle"
        write_json(new_dir(out)/"report.json", report)
        return report
    schedule_ids = set(pd.read_csv(Path(collection)/"schedule.csv",
                                   dtype={"game_id": str}).game_id)
    settled = load_nfl_games(data).set_index("game_id")
    rows = []
    voided, pending = [], []
    for snapshot in snapshots:
        game = snapshot["game_id"]
        if game not in schedule_ids:
            # Cancellations vanish from the feed rather than appearing unplayed.
            voided.append(game)
            continue
        if game not in settled.index:
            pending.append(game)
            continue
        result = settled.loc[game]
        if result.home_score == result.away_score:
            index = 1
        else:
            index = 2 if result.home_score > result.away_score else 0
        rows.append({"game_id": game, "season": snapshot["season"], "week": snapshot["week"],
                     "cutoff": snapshot["cutoff"], "outcome_index": index,
                     "outcome": OUTCOMES[index],
                     "moneyline_settlement": "push" if index == 1 else "win_or_lose",
                     "p_control": snapshot["predictions"]["p_control_home_given_decided"],
                     "p_challenger": snapshot["predictions"]["p_challenger_home_given_decided"],
                     "p_tie": snapshot["predictions"]["p_tie"]})
    report["voided_cancelled"] = voided
    report["awaiting_result"] = pending
    report["settled"] = len(rows)
    if not rows:
        report["status"] = "No snapshot has a settled result yet"
        write_json(new_dir(out)/"report.json", report)
        return report
    frame = pd.DataFrame(rows)
    frame["decision_at"] = pd.to_datetime(frame.cutoff, utc=True)
    frame["y"] = (frame.outcome_index == 2).astype(int)
    frame["is_tie"] = (frame.outcome_index == 1).astype(int)
    report["models"] = {name: _score(frame, "p_"+name, "p_tie")
                        for name in ("control", "challenger")}
    decided = frame[frame.outcome_index != 1]
    report["contrast"] = {
        "challenger_minus_control": paired_week_interval(
            decided, decided.p_challenger.to_numpy(), decided.p_control.to_numpy())
        if len(decided) else None,
        "note": "Decided games only; a push carries no binary outcome to score against. "
                "All settled pairs enter; games are never selected by their result."}
    out = new_dir(out)
    write_json(out/"report.json", report)
    frame.to_csv(out/"settled_pairs.csv", index=False)
    contrast = report["contrast"]["challenger_minus_control"]
    coverage = report["coverage"]
    lines = ["# NFL paired settlement ("+mode+")", "", report["warning"], "",
             f"Snapshots {len(snapshots)}; settled {len(frame)}; ties {int(frame.is_tie.sum())} "
             f"(moneyline push); voided/cancelled {len(voided)}; awaiting result {len(pending)}; "
             f"missed T-60 windows {coverage['missed_games']}.", "",
             "| model | games | 3-way log loss | decided log loss | Brier | acc | ECE(10) |",
             "|---|---|---|---|---|---|---|"]
    def cell(value, places=6):
        return "n/a" if value is None else f"{value:.{places}f}"

    for name, m in report["models"].items():
        lines.append(f"| {name} | {m['games']} | {m['three_way_log_loss']:.6f} | "
                     f"{cell(m['decided_log_loss'])} | {cell(m['decided_brier'])} | "
                     f"{cell(m['decided_accuracy'], 4)} | {m['ece_10bin']:.4f} |")
    if contrast:
        interval = contrast.get("ci95")
        text = "interval withheld (fewer than 10 week blocks)" if interval is None else \
            f"95% week-block interval [{interval[0]:+.6f}, {interval[1]:+.6f}]"
        lines += ["", f"Challenger minus control (decided games): "
                      f"{contrast['difference']:+.6f}; {text}."]
    lines += ["", "Reported separately from NBA; the outcome spaces differ and are never pooled."]
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return report
