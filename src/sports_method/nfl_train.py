"""NFL development: home-field and Elo baselines versus a regularized challenger.

Reuses the shared numerics (fit_logistic / fit_calibration / calibrate) rather
than reimplementing them, but owns its splits, outcome handling and metrics
because the NFL contract admits ties and the NBA partitioner hardcodes NBA
dates and forbids anything past the NBA holdout.

Splits are season-aligned and chronological. For a validation season S the
model fits on every game decided before season S-1, calibrates on season S-1,
and is scored on season S. Nothing from S or later informs the fit.

The 2025 season is the RESERVED FINAL HOLDOUT and is never loaded here; 2026 is
the live prospective season. Development therefore stops at 2024.

The L2 penalty is fixed a priori at 0.01 — the value already selected on the
NBA track — rather than tuned on NFL folds. With 272 games per season, spending
development data on a penalty search would cost more than it could plausibly
gain, and re-tuning per fold would invalidate the paired comparison.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from .io import new_dir, write_json, digest, code_hash, now
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate
from .nfl_data import (NFL_FEATURES, build_nfl_features, load_nfl_games, three_way,
                       three_way_metrics, tie_rate)

DEVELOPMENT_FOLDS = (2022, 2023, 2024)
FINAL_HOLDOUT_SEASON = 2025
PROSPECTIVE_SEASON = 2026
L2 = .01
WARNING = ("Research only: no odds, ROI, stakes, or evidence of beating bookmakers. "
           "Kickoff times were converted from US Eastern by us and schedule observation "
           "times are reconstructed, not provider timestamps. Result availability assumes "
           "kickoff plus 24h. Development folds may be inspected repeatedly and can be "
           "overfit; they are not confirmation.")
ADVANCEMENT = ("Prespecified before any holdout use: the challenger advances only if its "
               "pooled DECIDED log loss beats the better of the two baselines across all "
               "three development folds AND the pooled paired difference has a 95% "
               "week-block interval excluding zero. Three-way log loss must not be worse. "
               "Meeting these criteria authorises one single scoring of the reserved 2025 "
               "season; it does not authorise deployment or any wager.")


def week_blocks(frame):
    """Correlated-observation blocks: one NFL week is one block."""
    return (frame.season.astype(int).astype(str)+"-"
            + frame.decision_at.dt.isocalendar().week.astype(int).astype(str))


def paired_week_interval(frame, p, baseline, repetitions=2000, seed=42):
    """Paired bootstrap over whole weeks; negative favours the first model."""
    y = frame.y.to_numpy()

    def losses(v):
        v = np.clip(np.asarray(v, float), 1e-9, 1-1e-9)
        return -y*np.log(v)-(1-y)*np.log1p(-v)

    diffs = losses(p)-losses(baseline)
    keys = week_blocks(frame).to_numpy()
    groups = [diffs[keys == k] for k in pd.unique(keys)]
    sums = np.array([g.sum() for g in groups])
    counts = np.array([len(g) for g in groups])
    if len(groups) < 10:
        return {"difference": float(diffs.mean()), "ci95": None,
                "method": "fewer than 10 week blocks; interval withheld"}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(groups), (repetitions, len(groups)))
    boots = sums[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return {"difference": float(diffs.mean()),
            "ci95": [float(x) for x in np.quantile(boots, [.025, .975])],
            "blocks": len(groups),
            "method": "paired whole-week blocks; negative favours the first model; "
                      "excludes training and selection uncertainty"}


def fold_frames(features, season):
    """Fit before season-1, calibrate on season-1, validate on season."""
    fit = features[features.season < season-1]
    fit = fit[fit.available_at < features[features.season == season-1].decision_at.min()]
    cal = features[features.season == season-1]
    val = features[features.season == season]
    for name, part in (("fit", fit), ("calibration", cal), ("validation", val)):
        if len(part) < 30:
            raise ValueError(f"{name} split for {season} has too few games")
        if part[part.is_tie == 0].y.nunique() != 2:
            raise ValueError(f"{name} split for {season} lacks both decided outcomes")
    return fit, cal, val


def fit_fold(fit, cal, val, columns=NFL_FEATURES, l2=L2):
    """Binary model on DECIDED games; ties are handled by the base-rate factor."""
    decided_fit = fit[fit.is_tie == 0]
    decided_cal = cal[cal.is_tie == 0]
    model = fit_logistic(decided_fit[columns].to_numpy(dtype=float),
                         decided_fit.y.to_numpy(), np.full(len(decided_fit), .5), l2=l2)

    def predict(frame):
        return predict_logistic(model, frame[columns].to_numpy(dtype=float),
                                np.full(len(frame), .5))

    calibrator = fit_calibration(predict(decided_cal), decided_cal.y.to_numpy())
    raw = predict(val)
    # The tie rate is estimated on fitting data only, never on the scored season.
    return model, calibrator, raw, calibrate(raw, calibrator), tie_rate(fit)


def train_nfl(data, out):
    """Baselines and challenger over the rolling development folds."""
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    games = load_nfl_games(data)
    if (games.season >= FINAL_HOLDOUT_SEASON).any():
        games = games[games.season < FINAL_HOLDOUT_SEASON].copy()
    features = build_nfl_features(games)
    out = new_dir(out)
    features.to_csv(out/"development_features.csv", index=False)
    report = {"created_at": now(), "sport": "nfl", "warning": WARNING,
              "advancement_criteria": ADVANCEMENT, "features": list(NFL_FEATURES), "l2": L2,
              "development_folds": list(DEVELOPMENT_FOLDS),
              "final_holdout_season": FINAL_HOLDOUT_SEASON,
              "prospective_season": PROSPECTIVE_SEASON,
              "games_loaded": len(features), "ties_loaded": int(features.is_tie.sum()),
              "folds": {}, "pooled": {}, "code_sha256": code_hash(),
              "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")}}
    pooled = {"home_rate": [], "elo": [], "logistic": []}
    for season in DEVELOPMENT_FOLDS:
        fit, cal, val = fold_frames(features, season)
        model, calibrator, raw, p_logistic, p_tie = fit_fold(fit, cal, val)
        decided_fit = fit[fit.is_tie == 0]
        home_rate = float(decided_fit.y.mean())
        predictions = {"home_rate": np.full(len(val), home_rate),
                       "elo": val.p_elo.to_numpy(), "logistic": p_logistic}
        fold = {"split_counts": {"fit": len(fit), "calibration": len(cal), "validation": len(val)},
                "tie_rate_used": p_tie, "home_rate_used": home_rate,
                "validation_ties": int(val.is_tie.sum()), "models": {}}
        child = new_dir(out/f"{season}")
        write_json(child/"bundle.json", {"features": list(NFL_FEATURES), "logistic": model,
                                         "calibrator": calibrator, "l2": L2,
                                         "tie_rate": p_tie, "home_rate": home_rate,
                                         "validation_season": season})
        frame = val[["game_id", "season", "decision_at", "y", "is_tie"]].copy()
        for name, p in predictions.items():
            fold["models"][name] = three_way_metrics(val, p, p_tie)
            frame["p_"+name] = p
            record = frame[["game_id", "season", "decision_at", "y", "is_tie"]].copy()
            record["p"] = p
            pooled[name].append(record)
        fold["models"]["logistic"]["raw_metrics"] = three_way_metrics(val, raw, p_tie)
        decided = val[val.is_tie == 0]
        mask = (val.is_tie == 0).to_numpy()
        for name in ("home_rate", "elo"):
            fold[f"logistic_minus_{name}"] = paired_week_interval(
                decided, predictions["logistic"][mask], predictions[name][mask])
        frame.to_csv(child/"validation_predictions.csv", index=False)
        report["folds"][str(season)] = fold
        print(f"{season}: home_rate={fold['models']['home_rate']['decided_log_loss']:.6f} "
              f"elo={fold['models']['elo']['decided_log_loss']:.6f} "
              f"logistic={fold['models']['logistic']['decided_log_loss']:.6f}", flush=True)
    reference = pd.concat(pooled["home_rate"], ignore_index=True)
    for name, parts in pooled.items():
        combined = pd.concat(parts, ignore_index=True)
        if not combined[["game_id", "y"]].equals(reference[["game_id", "y"]]):
            raise ValueError("Every model must score identical games")
        report["pooled"][name] = three_way_metrics(combined, combined.p,
                                                   float(np.mean([report["folds"][str(s)]["tie_rate_used"]
                                                                  for s in DEVELOPMENT_FOLDS])))
    decided_all = reference.is_tie == 0
    scored = {name: pd.concat(parts, ignore_index=True).p.to_numpy()[decided_all.to_numpy()]
              for name, parts in pooled.items()}
    pooled_decided = reference[decided_all]
    for name in ("home_rate", "elo"):
        report["pooled"][f"logistic_minus_{name}"] = paired_week_interval(
            pooled_decided, scored["logistic"], scored[name])
    best = min(("home_rate", "elo"),
               key=lambda n: report["pooled"][n]["decided_log_loss"])
    interval = report["pooled"][f"logistic_minus_{best}"]
    all_folds_better = all(
        report["folds"][str(s)]["models"]["logistic"]["decided_log_loss"]
        < report["folds"][str(s)]["models"][best]["decided_log_loss"] for s in DEVELOPMENT_FOLDS)
    excludes_zero = bool(interval["ci95"] and (interval["ci95"][1] < 0 or interval["ci95"][0] > 0))
    three_way_ok = (report["pooled"]["logistic"]["three_way_log_loss"]
                    <= report["pooled"][best]["three_way_log_loss"])
    report["advancement"] = {"stronger_baseline": best, "all_folds_better": all_folds_better,
                             "pooled_interval_excludes_zero": excludes_zero,
                             "three_way_not_worse": three_way_ok,
                             "criteria_met": bool(all_folds_better and excludes_zero and three_way_ok),
                             "holdout_consumed": False}
    write_json(out/"report.json", report)
    lines = ["# NFL development: baselines versus regularized challenger", "", WARNING, "",
             ADVANCEMENT, "",
             f"Games {report['games_loaded']} (ties {report['ties_loaded']}); "
             f"folds {list(DEVELOPMENT_FOLDS)}; 2025 reserved; 2026 prospective.", "",
             "| fold | model | decided log loss | decided Brier | acc | 3-way log loss |",
             "|---|---|---|---|---|---|"]
    for season in DEVELOPMENT_FOLDS:
        for name in ("home_rate", "elo", "logistic"):
            m = report["folds"][str(season)]["models"][name]
            lines.append(f"| {season} | {name} | {m['decided_log_loss']:.6f} | "
                         f"{m['decided_brier']:.6f} | {m['decided_accuracy']:.4f} | "
                         f"{m['three_way_log_loss']:.6f} |")
    for name in ("home_rate", "elo", "logistic"):
        m = report["pooled"][name]
        lines.append(f"| pooled | {name} | {m['decided_log_loss']:.6f} | {m['decided_brier']:.6f} | "
                     f"{m['decided_accuracy']:.4f} | {m['three_way_log_loss']:.6f} |")
    lines.append("")
    for name in ("home_rate", "elo"):
        ci = report["pooled"][f"logistic_minus_{name}"]
        text = "interval withheld" if ci["ci95"] is None else \
            (f"95% week-block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]"
             + ("  (excludes zero)" if ci["ci95"][1] < 0 or ci["ci95"][0] > 0 else "  (includes zero)"))
        lines.append(f"- logistic minus {name}: {ci['difference']:+.6f}; {text}")
    lines += ["", f"Advancement criteria met: **{report['advancement']['criteria_met']}** "
                  f"(stronger baseline: {best}).",
              "No holdout was read. No odds, stake or wager is involved."]
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "criteria_met": report["advancement"]["criteria_met"],
            "stronger_baseline": best, "holdout_consumed": False}
