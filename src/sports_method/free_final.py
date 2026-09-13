"""One-use odds-free final-holdout freeze and evaluation.

Separate from the market-based freeze/evaluate commands, which require odds and
a different bundle schema. Nothing here relaxes the development guards: the
train-free/validate-free/ablate-free/regularize-free commands still refuse any
boundary at or past 2025-07-01.
"""
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import scipy
import sklearn
import xgboost as xgb
from sklearn.metrics import log_loss
from .free_data import FEATURES, load_games, build_features
from .free_train import metrics, paired_interval, WARNING
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate
from .io import new_dir, read_json, write_json, digest, code_hash, now

START = "2020-07-01"
# Exclusive UTC upper bounds. Same shape as free_validate.fold_boundaries(2025).
BOUNDARIES = {"train": "2024-07-01", "tune": "2025-01-01",
              "calibration": "2025-07-01", "holdout": "2026-07-01"}
PENALTY = .01
GRID = [{"max_depth": d, "n_estimators": n} for d in (2, 3) for n in (100, 250)]
DELAYS = (24, 48)
MODELS = ("home_rate", "elo", "logistic", "boosted")
HASHED = ("games.csv", "results.csv", "manifest.json")

CANDIDATE = {
    "primary": "logistic regression, all eleven features, lambda=0.01, sigmoid calibration",
    "features": list(FEATURES),
    "l2": PENALTY,
    "offset_q": 0.5,
    "intercept_penalized": False,
    "standardization": "mean/scale fitted on refit rows only",
    "calibration": "single sigmoid (intercept + exp slope, L2 0.001) fitted on calibration period only",
    "elo": {"initial": 1500, "k": 20, "scale": 400, "home_advantage": 65, "season_reset": False},
    "rolling_window_settled_games": 20,
    "rest_cap_days": 14, "back_to_back_threshold_days": 1.5,
    "cold_start": {"scoring_averages": 0, "win_rate": 0.5},
    "comparators": {"home_rate": "constant home-win rate of the refit rows",
                    "elo": "fixed Elo probability, uncalibrated",
                    "boosted": "secondary; four predeclared candidates selected on the tune period"},
    "boosted_grid": GRID,
}
METRIC_PLAN = {
    "primary": "calibrated logistic minus Elo paired log-loss difference, 95% seven-day block bootstrap (1000 resamples, seed 42)",
    "secondary": ["logistic minus home_rate paired difference", "Brier and accuracy for all families",
                  "holdout calibration diagnostic (reported, never applied)", "ten-bin reliability tables",
                  "raw versus calibrated challenger metrics", "boosted minus Elo paired difference"],
    "exploratory": ["monthly log loss", "neutral-site subset", "extra result-availability delays of 24h and 48h"],
    "rules": ["Only the primary comparison is confirmatory.",
              "Intervals exclude training and model-selection uncertainty and are not multiplicity-corrected.",
              "No result here is evidence of a betting edge, ROI or executable price.",
              "A disappointing result is not grounds to re-tune and re-score; the holdout is spent either way."],
}


def _ts(value):
    return pd.Timestamp(value, tz="UTC")


def data_hashes(data):
    data = Path(data)
    return {name: digest(data/name) for name in HASHED if (data/name).exists()}


def final_partition(features):
    """Chronological final split; only the holdout keeps unavailable labels."""
    ends = [_ts(v) for v in BOUNDARIES.values()]
    if sorted(ends) != ends or len(set(ends)) != 4:
        raise ValueError("Final boundaries must be strictly increasing")
    parts, lower = {}, _ts(START)
    for name, end in BOUNDARIES.items():
        upper = _ts(end)
        part = features[(features.decision_at >= lower) & (features.decision_at < upper)].copy()
        if name != "holdout":
            # Labels used for fitting or calibration must have arrived by the boundary.
            part = part[part.available_at < upper]
        if len(part) < 30 or part.y.nunique() != 2:
            raise ValueError(f"{name}: need at least 30 games and both outcomes")
        parts[name] = part
        lower = upper
    if parts["calibration"].available_at.max() >= _ts(BOUNDARIES["calibration"]):
        raise ValueError("Calibration labels must arrive before the holdout begins")
    if parts["holdout"].decision_at.min() < _ts(BOUNDARIES["calibration"]):
        raise ValueError("Holdout must begin at the reserved boundary")
    return parts


def fit_candidate(parts, threads):
    """Fit the frozen candidate and its comparators; holdout rows are never used."""
    train, tune, cal = parts["train"], parts["tune"], parts["calibration"]
    trials = []
    for grid in GRID:
        params = {**grid, "learning_rate": .03, "reg_lambda": 10, "min_child_weight": 20,
                  "tree_method": "hist", "objective": "binary:logistic", "eval_metric": "logloss",
                  "n_jobs": threads, "random_state": 42, "base_score": .5}
        model = xgb.XGBClassifier(**params).fit(train[FEATURES], train.y)
        trials.append({"params": params,
                       "tune_log_loss": float(log_loss(tune.y, model.predict_proba(tune[FEATURES])[:, 1], labels=[0, 1]))})
    best = min(trials, key=lambda t: t["tune_log_loss"])
    combined = pd.concat([train, tune])
    booster = xgb.XGBClassifier(**best["params"]).fit(combined[FEATURES], combined.y)
    logistic = fit_logistic(combined[FEATURES].to_numpy(), combined.y.to_numpy(),
                            np.full(len(combined), .5), l2=PENALTY)
    home_rate = float(combined.y.mean())

    def raw_predict(frame):
        return {"home_rate": np.full(len(frame), home_rate), "elo": frame.p_elo.to_numpy(),
                "logistic": predict_logistic(logistic, frame[FEATURES].to_numpy(), np.full(len(frame), .5)),
                "boosted": booster.predict_proba(frame[FEATURES])[:, 1]}

    on_cal = raw_predict(cal)
    calibrators = {name: fit_calibration(on_cal[name], cal.y.to_numpy()) for name in ("logistic", "boosted")}
    return {"logistic": logistic, "home_rate": home_rate, "calibrators": calibrators,
            "trials": trials, "selected_params": best["params"], "booster": booster,
            "refit_games": len(combined), "raw_predict": raw_predict}


def score(fitted, frame):
    p = fitted["raw_predict"](frame)
    for name in ("logistic", "boosted"):
        p[name + "_raw"] = p[name].copy()
        p[name] = calibrate(p[name], fitted["calibrators"][name])
    return p


def freeze_final(data, out):
    """Write the pre-registration record. Reads no holdout label or prediction."""
    data = Path(data).resolve()
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    raw = load_games(data)
    holdout = raw[raw.decision_at >= _ts(BOUNDARIES["calibration"])]
    if not len(holdout):
        raise ValueError("Dataset contains no reserved holdout games")
    out = new_dir(out)
    record = {"created_at": now(), "mode": "odds_free_final", "warning": WARNING,
              "data": str(data), "data_sha256": data_hashes(data),
              "code_sha256": code_hash(), "candidate": CANDIDATE,
              "boundaries_exclusive_utc": {"start": START, **BOUNDARIES},
              "metric_plan": METRIC_PLAN, "delays_hours": list(DELAYS),
              "counts": {"total_games": len(raw), "development_games": len(raw)-len(holdout),
                         "reserved_holdout_games": len(holdout)},
              "note": "Local tamper evidence and a one-use record, not an independent "
                      "preregistration service. Scoring the holdout is irreversible: "
                      "afterwards 2025-26 is development data and cannot back a fresh-holdout claim."}
    write_json(out/"freeze.json", record)
    return {"run": str(out), "code_sha256": record["code_sha256"],
            "reserved_holdout_games": record["counts"]["reserved_holdout_games"],
            "holdout": "NOT SCORED",
            "next": f'sports evaluate-final --run "{out}" --dry-run'}


def _verify(run):
    run = Path(run)
    if not (run/"freeze.json").exists():
        raise FileNotFoundError(f"No freeze.json in {run}; run freeze-final first")
    record = read_json(run/"freeze.json")
    if record.get("mode") != "odds_free_final":
        raise ValueError("Not an odds-free final freeze record")
    if record["code_sha256"] != code_hash():
        raise ValueError("Source changed since freezing; freeze a new run rather than editing the candidate")
    current = data_hashes(record["data"])
    if current != record["data_sha256"]:
        raise ValueError("Dataset differs from the frozen record")
    return run, record


def evaluate_final(run, threads=2, *, dry_run=False, confirmed=False):
    if threads < 1:
        raise ValueError("threads must be positive")
    if not dry_run and not confirmed:
        raise ValueError("Scoring the reserved holdout is irreversible; pass --yes-consume-final-holdout")
    run, record = _verify(run)
    out = new_dir(run/("dryrun" if dry_run else "holdout"))
    if not dry_run:
        # Claim the single use before any holdout label is read; a crash still consumes it.
        import json
        with (run/"HOLDOUT_CONSUMED.json").open("x") as handle:
            json.dump({"started_at": now(), "code_sha256": record["code_sha256"],
                       "data_sha256": record["data_sha256"]}, handle, indent=2)
    raw = load_games(record["data"])
    features = build_features(raw)          # one pass; prior results only, in availability order
    parts = final_partition(features)
    fitted = fit_candidate(parts, threads)
    holdout = parts["holdout"]
    predictions = score(fitted, holdout)
    bundle = {"mode": "odds_free_final", "features": FEATURES, "logistic": fitted["logistic"],
              "home_rate": fitted["home_rate"], "calibrators": fitted["calibrators"],
              "selected_params": fitted["selected_params"], "l2": PENALTY,
              "boundaries": BOUNDARIES, "refit_games": fitted["refit_games"],
              "data_sha256": record["data_sha256"], "code_sha256": record["code_sha256"],
              "versions": {"python": platform.python_version(), "numpy": np.__version__,
                           "pandas": pd.__version__, "scipy": scipy.__version__,
                           "sklearn": sklearn.__version__, "xgboost": xgb.__version__}}
    write_json(out/"bundle.json", bundle)
    fitted["booster"].save_model(out/"boosted.json")
    write_json(out/"trials.json", fitted["trials"])
    # A dry run must not write holdout outcomes to disk either.
    (features[features.decision_at < _ts(BOUNDARIES["calibration"])] if dry_run
     else features).to_csv(out/"features.csv", index=False)
    if dry_run:
        frame = holdout[["game_id", "decision_at"]].copy()
        for name, p in predictions.items():
            frame["p_"+name] = p
        frame.to_csv(out/"holdout_predictions_unscored.csv", index=False)
        write_json(out/"dryrun.json", {"created_at": now(), "holdout_games": len(holdout),
            "split_counts": {k: len(v) for k, v in parts.items()},
            "note": "Dry run: predictions only. No holdout outcome was read and no metric computed."})
        return {"run": str(out), "holdout": "NOT SCORED", "holdout_games": len(holdout),
                "split_counts": {k: len(v) for k, v in parts.items()},
                "next": f'sports evaluate-final --run "{run}" --yes-consume-final-holdout'}

    y = holdout.y.to_numpy()
    report = {"created_at": now(), "mode": "odds_free_final", "warning": WARNING,
              "candidate": CANDIDATE, "metric_plan": METRIC_PLAN,
              "boundaries_exclusive_utc": {"start": START, **BOUNDARIES},
              "split_counts": {k: len(v) for k, v in parts.items()},
              "excluded_from_fitting_at_availability_boundaries":
                  int(len(features[features.decision_at < _ts(BOUNDARIES["calibration"])])
                      - sum(len(parts[k]) for k in ("train", "tune", "calibration"))),
              "code_sha256": record["code_sha256"], "data_sha256": record["data_sha256"],
              "primary": {}, "secondary": {}, "exploratory": {}}
    report["primary"] = {"logistic_log_loss": metrics(y, predictions["logistic"])["log_loss"],
                         "logistic_minus_elo": paired_interval(holdout, predictions["logistic"], predictions["elo"])}
    report["secondary"] = {
        "metrics": {name: metrics(y, p) for name, p in predictions.items()},
        "logistic_minus_home_rate": paired_interval(holdout, predictions["logistic"], predictions["home_rate"]),
        "boosted_minus_elo": paired_interval(holdout, predictions["boosted"], predictions["elo"]),
        "calibration_diagnostic": {name: fit_calibration(p, y) for name, p in predictions.items()
                                   if name in ("elo", "logistic", "boosted")},
        "calibration_bins": {}}
    for name, p in predictions.items():
        bins = []
        for low in np.arange(0, 1, .1):
            mask = (p >= low) & (p < low+.1)
            if mask.any():
                bins.append({"lower": float(low), "n": int(mask.sum()),
                             "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
        report["secondary"]["calibration_bins"][name] = bins
    months = holdout.decision_at.dt.strftime("%Y-%m")
    report["exploratory"]["monthly"] = {m: {"n": int((months == m).sum()),
        **{k: metrics(y[(months == m).to_numpy()], p[(months == m).to_numpy()]) for k, p in predictions.items()}}
        for m in sorted(months.unique())}
    neutral = holdout.neutral.to_numpy().astype(bool)
    report["exploratory"]["neutral_subset"] = {"n": int(neutral.sum()),
        "note": "Too few games for inference; reported for completeness.",
        "metrics": ({k: metrics(y[neutral], p[neutral]) for k, p in predictions.items()}
                    if neutral.sum() and len(set(y[neutral])) == 2 else None)}
    frame = holdout[["game_id", "decision_at", "y", "neutral"]].copy()
    for name, p in predictions.items():
        frame["p_"+name] = p
    frame.to_csv(out/"holdout_predictions.csv", index=False)

    report["exploratory"]["delays"] = {}
    for delay in DELAYS:
        shifted = raw.copy()
        shifted["available_at"] += pd.Timedelta(hours=delay)
        delayed_parts = final_partition(build_features(shifted))
        delayed_holdout = delayed_parts["holdout"]
        if not delayed_holdout.game_id.reset_index(drop=True).equals(holdout.game_id.reset_index(drop=True)) \
                or not delayed_holdout.y.reset_index(drop=True).equals(holdout.y.reset_index(drop=True)):
            raise ValueError("Delay scenarios must score identical games and outcomes")
        delayed = score(fit_candidate(delayed_parts, threads), delayed_holdout)
        report["exploratory"]["delays"][str(delay)] = {
            "metrics": {k: metrics(y, p) for k, p in delayed.items()},
            "change_vs_baseline": {k: {"log_loss_change": metrics(y, delayed[k])["log_loss"]-metrics(y, predictions[k])["log_loss"],
                                       "mean_absolute_probability_change": float(np.abs(delayed[k]-predictions[k]).mean())}
                                   for k in MODELS}}
        pd.DataFrame({"game_id": holdout.game_id.to_numpy(), **{"p_"+k: v for k, v in delayed.items()}}).to_csv(
            out/f"holdout_predictions_delay_{delay}h.csv", index=False)

    # Saved-model replay: the written bundle must reproduce the written predictions.
    replay = predict_logistic(read_json(out/"bundle.json")["logistic"],
                              holdout[FEATURES].to_numpy(), np.full(len(holdout), .5))
    replayed = calibrate(replay, bundle["calibrators"]["logistic"])
    report["replay_max_absolute_difference"] = float(np.max(np.abs(replayed-predictions["logistic"])))
    if report["replay_max_absolute_difference"] > 1e-12:
        raise RuntimeError("Saved bundle does not reproduce the recorded predictions")
    write_json(out/"report.json", report)

    m, primary = report["secondary"]["metrics"], report["primary"]["logistic_minus_elo"]
    lines = ["# Final holdout evaluation (one use, odds-free)", "", WARNING, "",
             "This record is the single agreed test of the frozen candidate on 2025-26.",
             "2025-26 is now development data and cannot back any later fresh-holdout claim.", "",
             f"Frozen candidate: {CANDIDATE['primary']}",
             f"Boundaries (exclusive UTC): start {START}; " + "; ".join(f"{k} {v}" for k, v in BOUNDARIES.items()),
             f"Split counts: {report['split_counts']}",
             f"Labels excluded at fitting cutoffs: {report['excluded_from_fitting_at_availability_boundaries']}",
             f"Code sha256: {report['code_sha256']}", f"Data sha256: {report['data_sha256']}", "",
             "## Primary (confirmatory)",
             f"- Calibrated logistic log loss: {report['primary']['logistic_log_loss']:.6f}",
             f"- Logistic minus Elo: {primary['difference']:+.6f}; 95% block interval [{primary['ci95'][0]:+.6f}, {primary['ci95'][1]:+.6f}]",
             f"- Interval {'excludes' if primary['ci95'][1] < 0 or primary['ci95'][0] > 0 else 'includes'} zero.",
             "", "## Secondary (pre-specified, descriptive)"]
    for name, values in m.items():
        lines.append(f"- {name}: log loss={values['log_loss']:.6f}; Brier={values['brier']:.6f}; accuracy={values['accuracy']:.2%}")
    for key in ("logistic_minus_home_rate", "boosted_minus_elo"):
        v = report["secondary"][key]
        lines.append(f"- {key}: {v['difference']:+.6f}; 95% block interval [{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]")
    lines.append("- Holdout calibration diagnostic (intercept/slope, reported not applied): " +
                 "; ".join(f"{k}={v['intercept']:+.3f}/{v['slope']:.3f}" for k, v in report["secondary"]["calibration_diagnostic"].items()))
    lines.extend(["", "Reliability bins: count / mean predicted / observed"])
    for name in ("elo", "logistic", "boosted"):
        lines.append(f"- {name}: " + "; ".join(f"{b['n']} / {b['predicted']:.3f} / {b['observed']:.3f}"
                                               for b in report["secondary"]["calibration_bins"][name]))
    lines.extend(["", "## Exploratory (not confirmatory, not multiplicity-corrected)", "", "Monthly log loss:"])
    for month, values in report["exploratory"]["monthly"].items():
        lines.append(f"- {month}, n={values['n']}: " + "; ".join(f"{k}={values[k]['log_loss']:.4f}" for k in MODELS))
    lines.append(f"Neutral-site subset: n={report['exploratory']['neutral_subset']['n']} (too few for inference).")
    lines.append("Extra result-availability delay scenarios (refit and recalibrated under delay):")
    for delay, values in report["exploratory"]["delays"].items():
        lines.append(f"- +{delay}h: " + "; ".join(f"{k}={values['metrics'][k]['log_loss']:.6f}" for k in MODELS))
        lines.append("  change vs baseline: " + "; ".join(
            f"{k}={values['change_vs_baseline'][k]['log_loss_change']:+.6f}" for k in MODELS))
    lines.extend(["", "Intervals exclude training and model-selection uncertainty and are not corrected",
                  "for the development experiments already performed. No ROI, stake sizing, executable",
                  "price or market edge is demonstrated or implied by anything above.",
                  f"Saved-model replay maximum absolute difference: {report['replay_max_absolute_difference']:.2e}.",
                  "Full metrics: report.json. Model and provenance: bundle.json, freeze.json, HOLDOUT_CONSUMED.json."])
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "holdout": "SCORED (one use consumed)",
            "holdout_games": len(holdout),
            "primary_logistic_log_loss": report["primary"]["logistic_log_loss"],
            "primary_logistic_minus_elo": primary["difference"],
            "primary_ci95": primary["ci95"],
            "report_command": f'sports report --path "{out}"'}
