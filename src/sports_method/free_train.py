"""Offline odds-free training. Validation is reusable; final season stays sealed."""
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss
from .free_data import FEATURES, load_games, build_features
from .io import new_dir, digest, code_hash, write_json, now
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate

BOUNDARIES = {"train": "2023-07-01", "tune": "2024-01-01",
              "calibration": "2024-07-01", "validation": "2025-07-01"}
WARNING = ("Research only: no odds, ROI, stakes, or evidence of beating bookmakers. "
           "Schedule observation times are reconstructed; result availability assumes "
           "+24h after scheduled start. Historical revisions are not verified. "
           "Validation is development data; repeated optimization can overfit it.")


def partition(df, boundaries=None):
    boundaries = BOUNDARIES if boundaries is None else boundaries
    if list(boundaries) != list(BOUNDARIES):
        raise ValueError("Expected train, tune, calibration, validation boundaries")
    ends = [pd.Timestamp(v, tz="UTC") for v in boundaries.values()]
    if sorted(ends) != ends or len(set(ends)) != 4 or ends[0] <= pd.Timestamp("2020-07-01", tz="UTC"):
        raise ValueError("Split boundaries must be strictly increasing after training start")
    if ends[-1] > pd.Timestamp("2025-07-01", tz="UTC"):
        raise ValueError("Final holdout must remain unscored")
    parts = {}
    lower = pd.Timestamp("2020-07-01", tz="UTC")
    for name, end in boundaries.items():
        upper = pd.Timestamp(end, tz="UTC")
        part = df[(df.decision_at >= lower) & (df.decision_at < upper)].copy()
        # Labels used for fitting must already have arrived at the next stage.
        if name != "validation":
            part = part[part.available_at < upper]
        if len(part) < 30 or part.y.nunique() != 2:
            raise ValueError(f"{name}: need at least 30 games and both outcomes")
        parts[name] = part
        lower = upper
    return parts


def metrics(y, p):
    return {"log_loss": float(log_loss(y, p, labels=[0,1])),
            "brier": float(brier_score_loss(y, p)),
            "accuracy": float(np.mean((p >= .5) == np.asarray(y)))}


def paired_interval(frame, p, baseline, repetitions=1000):
    """Paired seven-day-block bootstrap: conditional, not training uncertainty."""
    y = frame.y.to_numpy()
    def losses(v):
        v = np.clip(np.asarray(v), 1e-6, 1-1e-6)
        return -y*np.log(v)-(1-y)*np.log1p(-v)
    days = (frame.decision_at-frame.decision_at.min()).dt.days//7
    diffs = losses(p)-losses(baseline)
    groups = [diffs[days.to_numpy() == d] for d in sorted(days.unique())]
    sums = np.array([g.sum() for g in groups]); counts = np.array([len(g) for g in groups])
    rng = np.random.default_rng(42)
    samples = rng.integers(0, len(groups), (repetitions, len(groups)))
    boots = sums[samples].sum(axis=1)/counts[samples].sum(axis=1)
    return {"difference": float(diffs.mean()), "ci95": np.quantile(boots, [.025,.975]).tolist(),
            "method": "paired 7-day blocks; negative favors model; excludes training/selection uncertainty"}


def fit_free(data, out, threads=2, *, boundaries=None, delay_hours=0):
    boundaries = BOUNDARIES.copy() if boundaries is None else dict(boundaries)
    if not np.isfinite(delay_hours) or delay_hours < 0:
        raise ValueError("Delay must be finite and nonnegative")
    if threads < 1:
        raise ValueError("threads must be positive")
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    data = Path(data)
    raw = load_games(data)
    cutoff = pd.Timestamp(boundaries["validation"], tz="UTC")
    if cutoff > pd.Timestamp("2025-07-01", tz="UTC"):
        raise ValueError("Final holdout must remain unscored")
    # Do not generate predictions, metrics or feature rows for the final holdout.
    dev = raw[raw.decision_at < cutoff].copy()
    dev["available_at"] += pd.Timedelta(hours=delay_hours)
    features = build_features(dev)
    parts = partition(features, boundaries)
    out = new_dir(out)
    features.to_csv(out / "features.csv", index=False)
    train, tune, cal, val = (parts[k] for k in boundaries)
    trials = []
    print(f"Tuning four boosted-tree candidates; validation ends {boundaries['validation']}; extra delay {delay_hours}h", flush=True)
    for depth in (2, 3):
        for trees in (100, 250):
            params = {"max_depth": depth, "n_estimators": trees, "learning_rate": .03,
                      "reg_lambda": 10, "min_child_weight": 20, "tree_method": "hist",
                      "objective": "binary:logistic", "eval_metric": "logloss",
                      "n_jobs": threads, "random_state": 42, "base_score": .5}
            model = xgb.XGBClassifier(**params).fit(train[FEATURES], train.y)
            p = model.predict_proba(tune[FEATURES])[:,1]
            trials.append({"params": params, "tune_log_loss": float(log_loss(tune.y, p))})
    best = min(trials, key=lambda t: t["tune_log_loss"])
    combined = pd.concat([train, tune])
    model = xgb.XGBClassifier(**best["params"]).fit(combined[FEATURES], combined.y)
    model.save_model(out / "boosted.json")
    logistic = fit_logistic(combined[FEATURES].to_numpy(), combined.y.to_numpy(), np.full(len(combined), .5))
    home_rate = float(combined.y.mean())
    def predict(frame):
        return {"home_rate": np.full(len(frame), home_rate), "elo": frame.p_elo.to_numpy(),
                "logistic": predict_logistic(logistic, frame[FEATURES].to_numpy(), np.full(len(frame), .5)),
                "boosted": model.predict_proba(frame[FEATURES])[:,1]}
    cal_predictions = predict(cal)
    calibrators = {name: fit_calibration(cal_predictions[name], cal.y.to_numpy())
                   for name in ("logistic", "boosted")}
    predictions = predict(val)
    for name in calibrators:
        predictions[name + "_raw"] = predictions[name].copy()
        predictions[name] = calibrate(predictions[name], calibrators[name])
    report = {"mode": "odds_free", "warning": WARNING, "created_at": now(),
              "extra_result_delay_hours": delay_hours,
              "coverage": {"total_games": len(raw), "development_games": len(dev),
                           "unscored_games_at_or_after_2025_07_01": int((raw.decision_at >= pd.Timestamp('2025-07-01', tz='UTC')).sum())},
              "split_counts": {k: len(v) for k,v in parts.items()},
              "excluded_from_fitting_at_availability_boundaries": len(dev)-sum(len(v) for v in parts.values()),
              "boundaries_exclusive_utc": boundaries,
              "metrics": {k: metrics(val.y, p) for k,p in predictions.items()},
              "vs_elo": {k: paired_interval(val, predictions[k], predictions["elo"])
                         for k in ("logistic", "boosted")}, "monthly": {}, "calibration_bins": {}}
    for name, p in predictions.items():
        bins = []
        for low in np.arange(0, 1, .1):
            mask = (p >= low) & (p < low+.1)
            if mask.any():
                bins.append({"lower": float(low), "n": int(mask.sum()),
                             "predicted": float(p[mask].mean()), "observed": float(val.y.to_numpy()[mask].mean())})
        report["calibration_bins"][name] = bins
    months = val.decision_at.dt.strftime("%Y-%m")
    for month in sorted(months.unique()):
        mask = (months == month).to_numpy()
        report["monthly"][month] = {"n": int(mask.sum()), **{k: metrics(val.y.to_numpy()[mask], p[mask]) for k,p in predictions.items()}}
    pred = val[["game_id", "decision_at", "y"]].copy()
    for name, p in predictions.items():
        pred["p_"+name] = p
    pred.to_csv(out / "validation_predictions.csv", index=False)
    write_json(out / "bundle.json", {"mode": "odds_free", "features": FEATURES, "logistic": logistic,
        "home_rate": home_rate, "calibrators": calibrators, "selected_params": best["params"],
        "boundaries": boundaries, "extra_result_delay_hours": delay_hours,
        "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")},
        "code_sha256": code_hash(), "versions": {"python": platform.python_version(),
        "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__, "xgboost": xgb.__version__}})
    write_json(out / "trials.json", trials)
    write_json(out / "report.json", report)
    lines = ["# Odds-free validation report", "", WARNING, "", "Final holdout: NOT SCORED.",
             f"Coverage: {report['coverage']}", f"Splits: {report['split_counts']}",
             f"Exclusive UTC boundaries: {boundaries}",
             f"Extra result-availability delay: {delay_hours} hours (added to imported availability).",
             f"Labels excluded at fitting cutoffs: {report['excluded_from_fitting_at_availability_boundaries']}",
             "", "Validation metrics (lower log loss/Brier is better):"]
    for name, m in report['metrics'].items():
        lines.append(f"- {name}: log loss={m['log_loss']:.6f}; Brier={m['brier']:.6f}; accuracy={m['accuracy']:.2%}")
    lines.extend(["", "Paired log-loss difference vs Elo (negative favors challenger):"])
    for name, m in report['vs_elo'].items():
        lines.append(f"- {name}: {m['difference']:.6f}; 95% block interval [{m['ci95'][0]:.6f}, {m['ci95'][1]:.6f}]")
    lines.extend(["Intervals exclude training/selection uncertainty.", "", "Monthly validation log loss:"])
    for month, m in report['monthly'].items():
        lines.append(f"- {month}, n={m['n']}: " + "; ".join(f"{k}={m[k]['log_loss']:.4f}" for k in ('home_rate','elo','logistic','boosted')))
    lines.extend(["", "Calibration bins: count / mean predicted / observed home-win rate"])
    for name in ('elo', 'logistic', 'boosted'):
        lines.append(f"- {name}: " + "; ".join(f"{b['n']} / {b['predicted']:.3f} / {b['observed']:.3f}" for b in report['calibration_bins'][name]))
    lines.extend(["", "Full metrics: report.json. Model and data provenance: bundle.json."])
    (out / "PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "split_counts": report["split_counts"],
            "final_holdout": "NOT SCORED", "report_command": f'sports report --path "{out}"'}
