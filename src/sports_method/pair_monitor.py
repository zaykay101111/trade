"""Monitoring and settlement for paired prospective records.

Deliberately OUTSIDE the frozen forecast surface: this module reads snapshots
and settled outcomes, never issues forecasts, and may evolve during the season
without forcing a challenger refreeze. It never modifies a recorded file.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .free_data import load_games
from .io import now, write_json, new_dir


def pair_status(collection, out, archive=None, at=None):
    """Coverage summary for paired prospective records. Reads only; never writes.

    A past cutoff with no recorded snapshot is a MISSED game: recorded forecasts
    alone cannot establish coverage, so missses are enumerated explicitly.
    """
    at = pd.to_datetime(at, utc=True) if at is not None else pd.Timestamp(now())
    schedule = pd.read_csv(Path(collection)/"schedule.csv", dtype={"game_id": str})
    schedule["decision_at"] = pd.to_datetime(schedule.decision_at, utc=True)
    recorded_dir = Path(out)/"recorded"
    recorded = {p.stem for p in recorded_dir.glob("*.json")} if recorded_dir.exists() else set()
    past = schedule[schedule.decision_at < at]
    key = past.game_id.map(lambda g: hashlib.sha256(g.encode()).hexdigest())
    missed = past[~key.isin(recorded)]
    report = {"as_of": str(at), "past_cutoffs": len(past), "recorded": len(recorded),
              "missed_games": int(len(missed)),
              "missed": missed[["game_id", "decision_at"]].astype(str).to_dict("records"),
              "next_cutoff": str(schedule[schedule.decision_at >= at].decision_at.min())}
    states, usable = {}, 0
    for path in sorted(recorded_dir.glob("*.json")) if recorded_dir.exists() else []:
        payload = json.loads(path.read_text())
        usable += int(payload["features"].get("availability_covered", 0))
        for side in ("home_state", "away_state"):
            for row in payload["selected_reports"]:
                state = row.get(side, "unknown")
                states[state] = states.get(state, 0)+1
    report["both_usable"] = usable
    report["report_states"] = states
    if archive is not None:
        index = Path(archive)/"index.jsonl"
        entries = [json.loads(l) for l in index.read_text().splitlines() if l.strip()] \
            if index.exists() else []
        prospective = [pd.to_datetime(e["retrieved_at"], utc=True) for e in entries
                       if e.get("capture") == "prospective"]
        recent = [t for t in prospective if t >= at-pd.Timedelta(hours=48)]
        report["archive"] = {"prospective_files": len(prospective),
                             "eligible_last_48h": len(recent),
                             "latest_retrieved_at": str(max(prospective)) if prospective else None}
    return report


def _score(y, p):
    p = np.clip(np.asarray(p, float), 1e-9, 1-1e-9)
    y = np.asarray(y, float)
    loss = -(y*np.log(p)+(1-y)*np.log1p(-p))
    bins = np.clip((p*10).astype(int), 0, 9)
    calibration = [{"bin": int(b), "count": int((bins == b).sum()),
                    "mean_forecast": float(p[bins == b].mean()),
                    "observed_rate": float(y[bins == b].mean())}
                   for b in np.unique(bins)]
    ece = float(sum(c["count"]*abs(c["mean_forecast"]-c["observed_rate"])
                    for c in calibration)/len(p))
    return {"games": int(len(p)), "log_loss": float(loss.mean()),
            "brier": float(np.mean((p-y)**2)),
            "accuracy": float(np.mean((p >= .5) == y)),
            "ece_10bin": ece, "calibration": calibration}, loss


def pair_evaluate(records, collection, data, out, include_simulated=False):
    """Settle recorded paired forecasts against completed games. Descriptive only.

    Snapshots are never modified. Every settled recorded pair enters the primary
    injury-minus-control contrast, including missing-report games; covered-only
    is secondary. No promotion decision is computed here.
    """
    from .evaluate import block_interval
    mode = "simulated" if include_simulated else "recorded"
    root = Path(records)/mode
    snapshots = []
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        payload = json.loads(path.read_text())
        if hashlib.sha256(payload["game_id"].encode()).hexdigest() != path.stem:
            raise ValueError(f"Snapshot filename does not match its game: {path.name}")
        snapshots.append(payload)
    report = {"created_at": now(), "mode": mode, "snapshots": len(snapshots),
              "warning": "Descriptive monitoring of frozen models. No promotion, no odds, no ROI. "
                         "Simulated records are rehearsal only and never evidence."}
    status = pair_status(collection, records)
    report["coverage"] = {"past_cutoffs": status["past_cutoffs"],
                          "recorded": status["recorded"],
                          "missed_games": status["missed_games"],
                          "report_states": status["report_states"]}
    if not snapshots:
        report["status"] = "No snapshots to settle"
        write_json(new_dir(out)/"report.json", report)
        return report
    settled = load_games(data).set_index("game_id")
    frame = pd.DataFrame([{**s["predictions"], "game_id": s["game_id"],
                           "cutoff": s["cutoff"],
                           "covered": bool(s["features"].get("availability_covered"))}
                          for s in snapshots])
    if frame.game_id.duplicated().any():
        raise ValueError("Duplicate snapshot game IDs")
    known = frame.game_id.isin(settled.index)
    pending = frame[~known]
    frame = frame[known].copy()
    outcomes = settled.loc[frame.game_id]
    frame["y"] = (outcomes.home_score > outcomes.away_score).astype(int).to_numpy()
    report["settled"] = int(len(frame))
    report["awaiting_result"] = pending.game_id.tolist()
    if frame.empty:
        report["status"] = "No snapshot has a settled result yet"
        write_json(new_dir(out)/"report.json", report)
        return report
    losses = {}
    report["models"] = {}
    for name in ("p_injury", "p_control", "p_deployed"):
        report["models"][name], losses[name] = _score(frame.y, frame[name])
    contrasts = {}
    for label, a, b in (("injury_minus_control", "p_injury", "p_control"),
                        ("injury_minus_deployed", "p_injury", "p_deployed"),
                        ("control_minus_deployed", "p_control", "p_deployed")):
        diff = losses[a]-losses[b]
        contrasts[label] = {"difference": float(diff.mean()),
                            "ci95_weekly_blocks": block_interval(diff, frame.cutoff),
                            "note": "negative favors the first model; interval None below 10 blocks"}
    report["contrasts"] = contrasts
    covered = frame[frame.covered]
    if len(covered):
        diff = (losses["p_injury"]-losses["p_control"])[frame.covered.to_numpy()]
        report["covered_only_secondary"] = {
            "games": int(len(covered)),
            "injury_minus_control": float(diff.mean()),
            "ci95_weekly_blocks": block_interval(diff, covered.cutoff)}
    out = new_dir(out)
    write_json(out/"report.json", report)
    primary = contrasts["injury_minus_control"]
    (out/"PASTE_BACK.md").write_text(
        "# Paired settlement report ("+mode+")\n\n"+report["warning"]+"\n\n"
        f"Snapshots: {len(snapshots)}; settled: {len(frame)}; awaiting result: {len(pending)}; "
        f"missed T-60 windows: {status['missed_games']}.\n\n"
        "| model | games | log loss | Brier | accuracy | ECE(10) |\n|---|---|---|---|---|---|\n"
        + "\n".join(f"| {m} | {v['games']} | {v['log_loss']:.6f} | {v['brier']:.6f} | "
                    f"{v['accuracy']:.4f} | {v['ece_10bin']:.4f} |"
                    for m, v in report["models"].items())
        + f"\n\nPrimary (all settled pairs) injury minus control: {primary['difference']:+.6f}; "
          f"95% weekly-block interval {primary['ci95_weekly_blocks']}.\n")
    return report
