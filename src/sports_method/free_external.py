"""Replicate the frozen candidate recipe on an external era (e.g. published-paper years).

This is not the reserved-holdout workflow and not a development-tuning command.
It applies the SAME frozen recipe -- eleven features, lambda 0.01, sigmoid
calibration, fixed Elo, constant home rate, secondary boosted trees -- to a
different range of seasons, so results can be compared with published work.
Nothing here alters the recipe, and no boundary of the 2020-2026 dataset is used.
"""
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import log_loss
from .free_data import FEATURES, load_games, build_features
from .free_train import metrics, paired_interval, WARNING
from .free_final import CANDIDATE, GRID, PENALTY, MODELS, fit_candidate, score
from .io import new_dir, write_json, digest, code_hash, now

# Walsh & Joshi (arXiv:2303.06021) train on 2014/15-2017/18 and bet on 2018/19.
PAPER_ERA = {"start": "2014-07-01", "train": "2017-07-01", "tune": "2018-01-01",
             "calibration": "2018-07-01", "evaluation": "2019-07-01"}


def expected_calibration_error(p, y, bins=20):
    """Binned |confidence - accuracy|, plus the classwise variant the paper selects on.

    For binary outcomes with uniform bins the classwise variant equals ECE, since
    binning 1-p groups the same games; both are reported so the number is directly
    comparable with published classwise-ECE figures. ECE is binning-dependent and
    biased at finite sample size, so this project reports it without selecting on it.
    """
    p, y = np.asarray(p, float), np.asarray(y, int)
    edges = np.linspace(0, 1, bins+1)

    def binned(probability, target):
        index = np.clip(np.digitize(probability, edges[1:-1]), 0, bins-1)
        total = 0.
        for b in range(bins):
            mask = index == b
            if mask.any():
                total += mask.mean()*abs(probability[mask].mean()-target[mask].mean())
        return total

    ece = binned(p, y.astype(float))
    classwise = (binned(p, y.astype(float))+binned(1-p, 1.-y))/2
    return {"ece": float(ece), "classwise_ece": float(classwise), "bins": bins}


def era_partition(features, era):
    if list(era) != ["start", "train", "tune", "calibration", "evaluation"]:
        raise ValueError("Era needs start, train, tune, calibration, evaluation")
    stamps = [pd.Timestamp(v, tz="UTC") for v in era.values()]
    if sorted(stamps) != stamps or len(set(stamps)) != 5:
        raise ValueError("Era boundaries must be strictly increasing")
    parts, lower = {}, stamps[0]
    for name, end in list(era.items())[1:]:
        upper = pd.Timestamp(end, tz="UTC")
        part = features[(features.decision_at >= lower) & (features.decision_at < upper)].copy()
        if name != "evaluation":
            part = part[part.available_at < upper]
        if len(part) < 30 or part.y.nunique() != 2:
            raise ValueError(f"{name}: need at least 30 games and both outcomes")
        parts[name] = part
        lower = upper
    return parts


def replicate_external(data, out, era=None, threads=2, label="external era"):
    era = dict(PAPER_ERA if era is None else era)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    data = Path(data)
    raw = load_games(data)
    span = (raw.decision_at.min(), raw.decision_at.max())
    features = build_features(raw)
    parts = era_partition(features, era)
    # Reuse the frozen fitting recipe unchanged; only the calendar differs.
    renamed = {"train": parts["train"], "tune": parts["tune"], "calibration": parts["calibration"]}
    fitted = fit_candidate(renamed, threads)
    evaluation = parts["evaluation"]
    predictions = score(fitted, evaluation)
    y = evaluation.y.to_numpy()
    out = new_dir(out)
    protocol = (f"Frozen candidate recipe applied to {label}. Same eleven features, lambda "
        f"{PENALTY}, sigmoid calibration, fixed Elo, constant home rate and secondary boosted "
        "trees as the 2020-2026 work. Elo starts at 1500 with no prior history, so the first "
        "season of any era is a burn-in period. These seasons were never used to design the "
        "recipe, but this is a retrospective comparison across a different era, not a "
        "prospective test; era differences in pace, scoring and home advantage are real.")
    report = {"created_at": now(), "mode": "odds_free_external", "warning": WARNING,
              "protocol": protocol, "label": label, "candidate": CANDIDATE, "era": era,
              "data_span": [str(span[0]), str(span[1])],
              "split_counts": {k: len(v) for k, v in parts.items()},
              "metrics": {name: metrics(y, p) for name, p in predictions.items()},
              "calibration_error": {name: expected_calibration_error(p, y)
                                    for name, p in predictions.items()},
              "vs_elo": {name: paired_interval(evaluation, predictions[name], predictions["elo"])
                         for name in ("logistic", "boosted")},
              "vs_home_rate": {name: paired_interval(evaluation, predictions[name], predictions["home_rate"])
                               for name in ("elo", "logistic", "boosted")},
              "selected_params": fitted["selected_params"], "refit_games": fitted["refit_games"],
              "code_sha256": code_hash(),
              "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")},
              "versions": {"python": platform.python_version(), "numpy": np.__version__,
                           "pandas": pd.__version__, "sklearn": sklearn.__version__,
                           "xgboost": xgb.__version__}, "calibration_bins": {}, "monthly": {}}
    for name, p in predictions.items():
        bins = []
        for low in np.arange(0, 1, .1):
            mask = (p >= low) & (p < low+.1)
            if mask.any():
                bins.append({"lower": float(low), "n": int(mask.sum()),
                             "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
        report["calibration_bins"][name] = bins
    months = evaluation.decision_at.dt.strftime("%Y-%m")
    for month in sorted(months.unique()):
        mask = (months == month).to_numpy()
        report["monthly"][month] = {"n": int(mask.sum()),
            **{k: metrics(y[mask], p[mask]) for k, p in predictions.items()}}
    frame = evaluation[["game_id", "decision_at", "y", "neutral"]].copy()
    for name, p in predictions.items():
        frame["p_"+name] = p
    frame.to_csv(out/"evaluation_predictions.csv", index=False)
    features.to_csv(out/"features.csv", index=False)
    write_json(out/"bundle.json", {"mode": "odds_free_external", "features": FEATURES,
        "logistic": fitted["logistic"], "home_rate": fitted["home_rate"],
        "calibrators": fitted["calibrators"], "selected_params": fitted["selected_params"],
        "l2": PENALTY, "era": era, "data_sha256": report["data_sha256"],
        "code_sha256": report["code_sha256"], "versions": report["versions"]})
    write_json(out/"trials.json", fitted["trials"])
    write_json(out/"report.json", report)
    lines = [f"# External-era replication: {label}", "", WARNING, "", protocol, "",
             f"Data span: {span[0]} to {span[1]}", f"Era boundaries (exclusive UTC): {era}",
             f"Split counts: {report['split_counts']}", f"Refit games: {fitted['refit_games']}", "",
             "Evaluation-season metrics (lower log loss/Brier better; ECE for comparability only):"]
    for name, m in report["metrics"].items():
        e = report["calibration_error"][name]
        lines.append(f"- {name}: log loss={m['log_loss']:.6f}; Brier={m['brier']:.6f}; "
                     f"accuracy={m['accuracy']:.2%}; ECE={e['ece']:.4f}; classwise-ECE={e['classwise_ece']:.4f}")
    lines.append("")
    lines.append("Paired log-loss differences (negative favors the first model):")
    for name, v in report["vs_elo"].items():
        lines.append(f"- {name} minus elo: {v['difference']:+.6f}; 95% block interval [{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]")
    for name, v in report["vs_home_rate"].items():
        lines.append(f"- {name} minus home_rate: {v['difference']:+.6f}; 95% block interval [{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]")
    lines.extend(["", "Reliability bins: count / mean predicted / observed"])
    for name in ("elo", "logistic", "boosted"):
        lines.append(f"- {name}: " + "; ".join(f"{b['n']} / {b['predicted']:.3f} / {b['observed']:.3f}"
                                               for b in report["calibration_bins"][name]))
    lines.extend(["", "Monthly log loss:"])
    for month, m in report["monthly"].items():
        lines.append(f"- {month}, n={m['n']}: " + "; ".join(f"{k}={m[k]['log_loss']:.4f}" for k in MODELS))
    lines.extend(["", "No odds, stake sizing, ROI or profitability is computed here. Accuracy and ECE",
                  "are reported for comparison with published work only; selection in this project",
                  "uses log loss, a strictly proper scoring rule that already penalizes miscalibration.",
                  "A different era is not an independent replication of the 2020-2026 result: team",
                  "quality, pace and home advantage differ, and Elo needs a burn-in season."])
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "label": label, "split_counts": report["split_counts"],
            "evaluation_log_loss": {k: report["metrics"][k]["log_loss"] for k in MODELS},
            "report_command": f'sports report --path "{out}"'}
