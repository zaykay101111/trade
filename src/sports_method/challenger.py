"""Frozen matched injury challenger; offline, append-only prospective snapshots.

Never modifies the deployed baseline or scores the consumed holdout.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from . import injury
from .collect import pending_features, forecast
from .free_data import FEATURES, build_features, load_games
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate
from .io import digest, forecast_surface_hash, now, read_json, write_json, new_dir


def surface():
    return {"baseline": forecast_surface_hash(), "injury": digest(injury.__file__),
            "challenger": digest(__file__)}


def predict(spec, frame):
    raw = predict_logistic(spec["logistic"], frame[spec["features"]].to_numpy(dtype=float),
                           np.full(len(frame), .5))
    return calibrate(raw, spec["calibrator"])


def freeze(data, reports, team_log, baseline, out):
    """Fixed development-supported window: fit <Jan 2025, calibrate <Jul 2025."""
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}")
    manifest = read_json(str(reports)+".manifest.json")
    if manifest["csv_sha256"] != digest(reports) or manifest["parser_sha256"] != digest(injury.__file__):
        raise ValueError("Parsed CSV or parser drifted; use a freshly parsed file")
    baseline = Path(baseline)/"bundle.json"
    deployed = read_json(baseline)
    if deployed.get("forecast_surface_sha256") != forecast_surface_hash():
        raise ValueError("Baseline forecast surface drifted")
    games = load_games(data)
    games = games[games.decision_at < pd.Timestamp("2025-07-01", tz="UTC")].copy()
    lookup = injury.team_lookup(team_log)
    extra = injury.availability_frame(games, pd.read_csv(reports), lookup)
    selected = extra.attrs["selected_reports"]
    extra.attrs = {}
    frame = build_features(games).merge(extra, on="game_id", validate="one_to_one")
    fit_end, cal_end = pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2025-07-01", tz="UTC")
    train = frame[(frame.decision_at < fit_end) & (frame.available_at < fit_end)]
    cal = frame[(frame.decision_at >= fit_end) & (frame.available_at < cal_end)]
    for name, part in (("fit", train), ("calibration", cal)):
        if len(part) < 30 or part.y.nunique() != 2:
            raise ValueError(f"Insufficient {name} data")
        if part.availability_covered.mean() < .8:
            raise ValueError(f"Insufficient {name} injury coverage (requires 80%)")
    models = {}
    for name, columns in (("control", FEATURES), ("injury", FEATURES+injury.AVAILABILITY_FEATURES)):
        model = fit_logistic(train[columns].to_numpy(dtype=float), train.y.to_numpy(),
                             np.full(len(train), .5), l2=.01)
        raw = predict_logistic(model, cal[columns].to_numpy(dtype=float), np.full(len(cal), .5))
        models[name] = {"features": columns, "logistic": model,
                        "calibrator": fit_calibration(raw, cal.y.to_numpy())}
    bundle = {"version": "injury-pair-v1", "created_at": now(), "surface": surface(),
              "baseline_sha256": digest(baseline), "models": models, "team_lookup": lookup,
              "fit_end": str(fit_end), "calibration_end": str(cal_end), "l2": .01,
              "split_counts": {"fit": len(train), "calibration": len(cal)},
              "coverage": {"fit": float(train.availability_covered.mean()),
                           "calibration": float(cal.availability_covered.mean())},
              "sources": {"games": digest(Path(data)/"games.csv"),
                          "results": digest(Path(data)/"results.csv"), "reports": digest(reports),
                          "parse_manifest": digest(str(reports)+".manifest.json"), "team_log": digest(team_log)},
              "protocol": "Primary contrast injury minus matched control on ALL recorded games, including missing reports. "
                          "Deployed newer baseline is a secondary operational benchmark. No retrospective scoring or promotion. "
                          "Record once per game, in five minutes BEFORE T-60; never backdate. "
                          "Development injury data are backfilled; prospective timestamps are local capture evidence, not independent attestation."}
    out = new_dir(out)
    write_json(out/"bundle.json", bundle)
    write_json(out/"parse_manifest.json", manifest)
    selected.to_csv(out/"training_selected_reports.csv", index=False)
    (out/"PASTE_BACK.md").write_text("# Frozen injury challenger pair\n\n"
        "No season scored. Existing deployed baseline unchanged.\n\n"
        f"Fit games: {len(train)}; calibration games: {len(cal)}.\n"
        f"Both-usable injury coverage: fit {bundle['coverage']['fit']:.1%}, calibration {bundle['coverage']['calibration']:.1%}.\n"
        "Matched control: 11 inputs. Injury challenger: 25 inputs.\n"
        "Fit cutoff: 2025-01-01 UTC; calibration cutoff: 2025-07-01 UTC.\n\n"+bundle["protocol"]+"\n")
    return {"run": str(out), "models": list(models), "scored": False,
            "bundle_sha256": digest(out/"bundle.json")}


def captured_reports(archive, at):
    """Parse only locally captured, hash-verified, recent prospective sources."""
    if archive is None:
        return pd.DataFrame(), []
    archive = Path(archive)
    index = archive/"index.jsonl"
    if not index.exists():
        raise FileNotFoundError(f"Archive index missing: {index}")
    frames, provenance, seen = [], [], set()
    for line in index.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        name = entry["filename"]
        if Path(name).name != name or name in seen:
            raise ValueError("Unsafe or duplicate archive filename")
        seen.add(name)
        retrieved = pd.to_datetime(entry.get("retrieved_at"), utc=True, errors="coerce")
        if entry.get("capture") != "prospective" or pd.isna(retrieved):
            continue
        if not at-pd.Timedelta(hours=48) <= retrieved < at:
            continue
        path = archive/"pdf"/name
        if digest(path) != entry["sha256"]:
            raise ValueError(f"Injury PDF hash mismatch: {name}")
        frame = injury.parse_report(path)
        if frame.empty:
            raise ValueError(f"No rows parsed from prospective PDF: {name}")
        nominal = pd.to_datetime(frame.report_at, utc=True)
        if (nominal > retrieved).any():
            raise ValueError(f"PDF report time after retrieval: {name}")
        frame = frame.assign(capture="prospective", retrieved_at=str(retrieved),
                             pdf_sha256=entry["sha256"], parser_version=injury.PARSER_VERSION,
                             source_url=entry.get("url"))
        frames.append(frame)
        provenance.append(entry)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), provenance


def availability(games, reports, lookup):
    # Existing parser rejects an empty input; represent missingness directly.
    if not reports.empty:
        return injury.availability_frame(games, reports, lookup)
    extra = pd.DataFrame({"game_id": games.game_id})
    for column in injury.AVAILABILITY_FEATURES:
        extra[column] = int(column in ("home_missing", "away_missing"))
    selection = games[["game_id", "decision_at", "scheduled_at", "home_id", "away_id"]].copy()
    selection["home_state"] = selection["away_state"] = "missing"
    selection["availability_covered"] = False
    extra.attrs["selected_reports"] = selection
    return extra


def poll(collection, pair, baseline, data, out, archive=None, at=None, record=False):
    """No network access. Simulation by default; --record uses actual UTC only."""
    if record and at is not None:
        raise ValueError("Cannot backdate a recorded forecast with --at")
    actual = pd.Timestamp(now())
    issue = pd.to_datetime(at, utc=True) if at is not None else actual
    pair_file = Path(pair)/"bundle.json"
    bundle = read_json(pair_file)
    if bundle.get("surface") != surface():
        raise ValueError("Challenger source drifted; freeze a new version")
    if digest(Path(baseline)/"bundle.json") != bundle["baseline_sha256"]:
        raise ValueError("Baseline bundle changed")
    if record and pd.Timestamp(bundle["created_at"]) >= issue:
        raise ValueError("Release must precede issuance")
    schedule_path = Path(collection)/"schedule.csv"
    schedule = pd.read_csv(schedule_path, dtype={"game_id": str, "home_id": str, "away_id": str})
    for col in ("scheduled_at", "decision_at", "schedule_observed_at"):
        schedule[col] = pd.to_datetime(schedule[col], utc=True)
    if schedule.game_id.duplicated().any():
        raise ValueError("Duplicate schedule IDs")
    targets = schedule[(schedule.decision_at >= issue) &
                       (schedule.decision_at <= issue+pd.Timedelta(minutes=5))].copy()
    if targets.empty:
        return {"games": 0, "status": "No games in the five-minute pre-cutoff window"}
    if (targets.home_id == targets.away_id).any() or targets[["home_id", "away_id"]].isin(["0"]).any().any():
        raise ValueError("Unassigned or identical teams")
    if ((targets.scheduled_at-targets.decision_at) != pd.Timedelta(hours=1)).any():
        raise ValueError("Requires T-60 cutoffs")
    if (targets.schedule_observed_at > issue).any():
        raise ValueError("Schedule observation is later than issuance")
    root = Path(out)/("recorded" if record else "simulated")
    targets = targets[~targets.game_id.map(lambda g: (root/(hashlib.sha256(g.encode()).hexdigest()+".json")).exists())]
    if targets.empty:
        return {"games": 0, "status": "Games already recorded"}
    neutral = targets.is_neutral.astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0})
    if neutral.isna().any():
        raise ValueError("Invalid neutral flag")
    targets["neutral"] = neutral.astype(int)
    settled = load_games(data)
    # The feature cutoff is actual feature observation, not the upcoming nominal T-60.
    observed_targets = targets.copy()
    observed_targets["decision_at"] = issue
    features = pending_features(settled, observed_targets)
    reports, sources = captured_reports(archive, issue)
    extra = availability(observed_targets, reports, bundle["team_lookup"])
    selected = extra.attrs["selected_reports"]
    extra.attrs = {}
    frame = features.merge(extra, on="game_id", validate="one_to_one")
    frame["p_deployed"] = forecast(baseline, frame).p_model.to_numpy()
    for name, spec in bundle["models"].items():
        frame["p_"+name] = predict(spec, frame)
    provenance = {"pair_sha256": digest(pair_file), "baseline_sha256": bundle["baseline_sha256"],
                  "schedule_sha256": digest(schedule_path),
                  "data_sha256": {f: digest(Path(data)/f) for f in ("games.csv", "results.csv")},
                  "surface": surface(), "injury_sources": sources}
    completed = pd.Timestamp(now()) if record else issue
    if (targets.decision_at < completed).any():
        raise ValueError("Calculation crossed T-60; no prospective forecasts recorded")
    root.mkdir(parents=True, exist_ok=True)
    for row in frame.to_dict("records"):
        game = targets[targets.game_id == row["game_id"]].iloc[0]
        chosen = selected[selected.game_id == row["game_id"]].to_json(orient="records", date_format="iso")
        payload = {"mode": "prospective" if record else "simulation", "issued_at": str(completed),
                   "inputs_observed_at": str(issue), "game_id": row["game_id"],
                   "scheduled_at": str(game.scheduled_at), "cutoff": str(game.decision_at),
                   "predictions": {k: row[k] for k in ("p_deployed", "p_control", "p_injury")},
                   "features": {k: row[k] for k in FEATURES+injury.AVAILABILITY_FEATURES},
                   "selected_reports": json.loads(chosen), "provenance": provenance}
        path = root/(hashlib.sha256(row["game_id"].encode()).hexdigest()+".json")
        with path.open("x") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
    summary = {"games": len(frame), "mode": "prospective" if record else "simulation",
               "both_usable": int(frame.availability_covered.sum()), "out": str(root),
               "network_requests": 0, "scored": False}
    return summary
