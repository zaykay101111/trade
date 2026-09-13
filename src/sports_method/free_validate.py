"""Fixed expanding-window development checks, never final-holdout evaluation."""
from pathlib import Path
import numpy as np
import pandas as pd
from .free_train import fit_free, metrics, WARNING
from .io import new_dir, read_json, write_json, now, code_hash

YEARS = (2022, 2023, 2024)
DELAYS = (0, 24, 48)
MODELS = ("home_rate", "elo", "logistic", "boosted")


def fold_boundaries(year):
    if year not in YEARS:
        raise ValueError("Only development seasons 2022-23 through 2024-25 are allowed")
    return {"train": f"{year-1}-07-01", "tune": f"{year}-01-01",
            "calibration": f"{year}-07-01", "validation": f"{year+1}-07-01"}


def validate_free(data, out, threads=2):
    if threads < 1:
        raise ValueError("threads must be positive")
    out = new_dir(out)
    report = {"created_at": now(), "code_sha256": code_hash(), "warning": WARNING,
              "final_holdout": "NOT SCORED", "folds": {}, "pooled": {},
              "protocol": "Expanding training; prior-season tune/calibration; next-season validation. "
              "Each delay scenario rebuilds features and refits/tunes/calibrates all models. "
              "Extra 0/24/48h means assumed total 24/48/72h availability for this imported dataset. "
              "Not a fixed-model outage test or a test of schedule revisions. "
              "Seasons have disjoint validation games but overlapping training; not independent trials. "
              "2024-25 was already inspected; these are development robustness checks, not fresh confirmation."}
    pooled = {d: [] for d in DELAYS}
    for year in YEARS:
        name = f"{year}-{str(year+1)[-2:]}"
        report["folds"][name] = {}
        baseline = None
        for delay in DELAYS:
            child = out / f"{name}-delay-{delay}h"
            fit_free(data, child, threads, boundaries=fold_boundaries(year), delay_hours=delay)
            r = read_json(child / "report.json")
            pred = pd.read_csv(child / "validation_predictions.csv", dtype={"game_id": str})
            if baseline is None:
                baseline = pred
            if not pred[["game_id", "y", "decision_at"]].equals(baseline[["game_id", "y", "decision_at"]]):
                raise ValueError("Delay scenarios must evaluate identical games and outcomes")
            summary = {"split_counts": r["split_counts"], "metrics": r["metrics"],
                       "vs_elo": r["vs_elo"], "calibration_bins": r["calibration_bins"],
                       "excluded_labels": r["excluded_from_fitting_at_availability_boundaries"],
                       "change_vs_no_extra_delay": {}}
            for model in MODELS:
                summary["change_vs_no_extra_delay"][model] = {
                    "log_loss_change": r["metrics"][model]["log_loss"] - metrics(baseline.y, baseline['p_'+model])["log_loss"],
                    "mean_absolute_probability_change": float(np.abs(pred['p_'+model]-baseline['p_'+model]).mean())}
            report["folds"][name][str(delay)] = summary
            pooled[delay].append(pred)
            write_json(out / "progress.json", {"last_completed": child.name,
                       "completed": sum(len(v) for v in pooled.values()), "total": 9})
    for delay, frames in pooled.items():
        frame = pd.concat(frames, ignore_index=True)
        if frame.game_id.duplicated().any():
            raise ValueError("Overlapping validation games across folds")
        report["pooled"][str(delay)] = {"games": len(frame),
            "metrics": {m: metrics(frame.y, frame['p_'+m]) for m in MODELS}}
    write_json(out / "report.json", report)
    lines = ["# Rolling-season and delayed-data checks", "", WARNING, "",
             report["protocol"], "", "Final holdout: NOT SCORED.", "",
             "Log loss by season and extra availability delay (lower is better):"]
    for season, scenarios in report['folds'].items():
        for delay, r in scenarios.items():
            line = f"- {season}, +{delay}h, n={r['split_counts']['validation']}: "
            lines.append(line + "; ".join(f"{m}={r['metrics'][m]['log_loss']:.6f}" for m in MODELS))
            for m in ('logistic', 'boosted'):
                ci = r['vs_elo'][m]
                lines.append(f"  {m} minus Elo: {ci['difference']:.6f}, 95% block interval [{ci['ci95'][0]:.6f}, {ci['ci95'][1]:.6f}]")
    lines.extend(["", "Pooled descriptive metrics (no independent-fold significance claim):"])
    for delay, r in report['pooled'].items():
        for m, v in r['metrics'].items():
            lines.append(f"- +{delay}h {m}: n={r['games']}, log loss={v['log_loss']:.6f}, Brier={v['brier']:.6f}, accuracy={v['accuracy']:.2%}")
    lines.extend(["", "Delay sensitivity vs matching no-extra-delay fold:"])
    for season, scenarios in report['folds'].items():
        for delay in ('24', '48'):
            for m in ('logistic', 'boosted'):
                v = scenarios[delay]['change_vs_no_extra_delay'][m]
                lines.append(f"- {season} +{delay}h {m}: log-loss change={v['log_loss_change']:+.6f}; mean |probability change|={v['mean_absolute_probability_change']:.6f}")
    lines.extend(["", "No automatic pass/fail or final model promotion. Intervals exclude training/selection uncertainty.",
                  "Full calibration bins and counts: report.json; each fold contains its models, hashes and predictions."])
    (out / 'PASTE_BACK.md').write_text('\n'.join(lines)+'\n')
    return {"run": str(out), "completed": 9, "final_holdout": "NOT SCORED",
            "report_command": f'sports report --path "{out}"'}
