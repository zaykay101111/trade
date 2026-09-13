"""Possession-adjusted box-score features, and a development comparison against the base set.

Motivated by the external comparison in PAPER_ERA_COMPARISON.md: Walsh & Joshi
report ~69% accuracy on 2017/18 from shooting, rebounding and previous-season
record, against ~66% for our margin/rest/Elo inputs. These features test whether
that gap is really information rather than selection.

The base feature builder in free_data.py is deliberately NOT modified: it is part
of the frozen forecast surface, and editing it would invalidate a deployed
release. Box features are computed in a second pass over the same availability
ordering and merged on game_id.

Adopting these features requires a NEW frozen release before they can count for
any season, exactly like any other change to the candidate.
"""
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
import pandas as pd
from .free_data import FEATURES, build_features, load_games
from .free_train import metrics, paired_interval, partition, WARNING
from .free_validate import YEARS, fold_boundaries
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate
from .io import new_dir, write_json, digest, code_hash, now

BOX_FEATURES = ["off_rating_diff", "def_rating_diff", "net_rating_diff", "pace_diff",
                "efg_diff", "tov_rate_diff", "oreb_rate_diff", "ft_rate_diff",
                "prev_season_win_rate_diff"]
EXTENDED = list(FEATURES)+BOX_FEATURES
WINDOW = 20


def load_box(raw_csv):
    """Per-team box lines keyed by game and team, with possession estimates."""
    raw = pd.read_csv(raw_csv, dtype={"GAME_ID": str, "TEAM_ID": str})
    required = ["FGA", "FGM", "FG3M", "FTA", "OREB", "TOV", "PTS"]
    missing = [c for c in required if c not in raw]
    if missing:
        raise ValueError(f"Team log is missing {missing}")
    raw = raw.dropna(subset=required)
    # Standard possession estimate; a convention, not a measurement.
    raw["POSS"] = raw.FGA-raw.OREB+raw.TOV+.44*raw.FTA
    lines = {}
    for row in raw.itertuples():
        lines[(str(row.GAME_ID).zfill(10), str(row.TEAM_ID))] = {
            "pts": float(row.PTS), "poss": float(row.POSS), "fga": float(row.FGA),
            "fgm": float(row.FGM), "fg3m": float(row.FG3M), "fta": float(row.FTA),
            "oreb": float(row.OREB), "tov": float(row.TOV)}
    return lines


def _aggregate(history):
    """Rolling rates over settled games. Empty history is neutral (all zeros)."""
    if not history:
        return np.zeros(8)
    total = {k: sum(h[k] for h in history) for k in
             ("pts", "poss", "fga", "fgm", "fg3m", "fta", "oreb", "tov", "opp_pts", "opp_poss")}
    poss = max(total["poss"], 1.)
    opp_poss = max(total["opp_poss"], 1.)
    fga = max(total["fga"], 1.)
    misses = max(total["fga"]-total["fgm"], 1.)
    off = 100*total["pts"]/poss
    dfn = 100*total["opp_pts"]/opp_poss
    return np.array([off, dfn, off-dfn, poss/len(history),
                     (total["fgm"]+.5*total["fg3m"])/fga, total["tov"]/poss,
                     total["oreb"]/misses, total["fta"]/fga])


def box_features(df, box):
    """Second pass over the same availability ordering as free_data.build_features.

    A result is revealed only once available_at is strictly before the decision
    cutoff, identically to the base builder, so the two passes stay aligned.
    """
    decisions = df.sort_values(["decision_at", "game_id"])
    events = list(df.sort_values(["available_at", "game_id"]).itertuples())
    histories = defaultdict(lambda: deque(maxlen=WINDOW))
    season_record = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    output, ei = [], 0
    for row in decisions.itertuples():
        while ei < len(events) and events[ei].available_at < row.decision_at:
            e = events[ei]
            ei += 1
            home, away = box.get((e.game_id, e.home_id)), box.get((e.game_id, e.away_id))
            season = str(e.game_id)[3:5]
            season_record[e.home_id][season][e.y == 1] += 1
            season_record[e.away_id][season][e.y == 0] += 1
            if home is None or away is None:
                continue
            histories[e.home_id].append({**home, "opp_pts": away["pts"], "opp_poss": away["poss"]})
            histories[e.away_id].append({**away, "opp_pts": home["pts"], "opp_poss": home["poss"]})
        season = str(row.game_id)[3:5]
        previous = f"{int(season)-1:02d}"

        def prior_rate(team):
            losses, wins = season_record[team][previous]
            played = wins+losses
            return wins/played if played else .5

        diff = _aggregate(list(histories[row.home_id]))-_aggregate(list(histories[row.away_id]))
        output.append({"game_id": row.game_id,
                       **dict(zip(BOX_FEATURES[:-1], diff)),
                       "prev_season_win_rate_diff": prior_rate(row.home_id)-prior_rate(row.away_id)})
    return pd.DataFrame(output)


def build_extended(df, box):
    base = build_features(df)
    extra = box_features(df, box)
    merged = base.merge(extra, on="game_id", validate="one_to_one")
    if len(merged) != len(base):
        raise ValueError("Box features did not align with base features")
    return merged


def _fit(train_frame, cal, val, columns, l2=.01):
    model = fit_logistic(train_frame[columns].to_numpy(), train_frame.y.to_numpy(),
                         np.full(len(train_frame), .5), l2=l2)

    def predict(frame):
        return predict_logistic(model, frame[columns].to_numpy(), np.full(len(frame), .5))

    calibrator = fit_calibration(predict(cal), cal.y.to_numpy())
    raw = predict(val)
    return model, calibrator, raw, calibrate(raw, calibrator)


def compare_extension(data, raw_csv, out, threads=2):
    """Base versus extended features on the existing development folds. Development only."""
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    frame = load_games(data)
    dev = frame[frame.decision_at < pd.Timestamp("2025-07-01", tz="UTC")].copy()
    features = build_extended(dev, load_box(raw_csv))
    out = new_dir(out)
    features.to_csv(out/"development_features.csv", index=False)
    protocol = ("Base eleven features versus the same set plus nine possession-adjusted "
        "box-score differentials, on the three existing chronological development folds. "
        "Same lambda 0.01, same sigmoid calibration, same fold shape. Rolling window of 20 "
        "settled games with the identical availability rule; previous-season win rate uses "
        "only completed prior-season games. Possession count is the standard estimate "
        "FGA-OREB+TOV+0.44*FTA, a convention rather than a measurement. These folds have "
        "been inspected many times: this is development evidence, not confirmation, and "
        "adopting these features requires a new frozen release before any season counts.")
    report = {"created_at": now(), "warning": WARNING, "protocol": protocol,
              "base_features": list(FEATURES), "box_features": BOX_FEATURES,
              "folds": {}, "pooled": {}, "code_sha256": code_hash(),
              "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")},
              "box_sha256": digest(raw_csv)}
    pooled = {"base": [], "extended": []}
    for year in YEARS:
        season = f"{year}-{str(year+1)[-2:]}"
        parts = partition(features, fold_boundaries(year))
        combined = pd.concat([parts["train"], parts["tune"]])
        cal, val = parts["calibration"], parts["validation"]
        fold = {"split_counts": {k: len(v) for k, v in parts.items()}, "models": {}}
        predictions = {}
        for name, columns in (("base", list(FEATURES)), ("extended", EXTENDED)):
            model, calibrator, raw, p = _fit(combined, cal, val, columns)
            child = new_dir(out/f"{season}-{name}")
            write_json(child/"bundle.json", {"features": columns, "logistic": model,
                                             "calibrator": calibrator, "l2": .01,
                                             "boundaries": fold_boundaries(year)})
            prediction = val[["game_id", "decision_at", "y"]].copy()
            prediction["p_raw"], prediction["p"] = raw, p
            prediction.to_csv(child/"validation_predictions.csv", index=False)
            pooled[name].append(prediction)
            predictions[name] = p
            fold["models"][name] = {"metrics": metrics(val.y, p), "raw_metrics": metrics(val.y, raw),
                                    "standardized_slope_norm": float(np.linalg.norm(model["coef"][1:]))}
        fold["extended_minus_base"] = paired_interval(val, predictions["extended"], predictions["base"])
        report["folds"][season] = fold
        print(f"{season}: base={fold['models']['base']['metrics']['log_loss']:.6f} "
              f"extended={fold['models']['extended']['metrics']['log_loss']:.6f}", flush=True)
    base = pd.concat(pooled["base"], ignore_index=True)
    for name, frames in pooled.items():
        pooled_frame = pd.concat(frames, ignore_index=True)
        if not pooled_frame[["game_id", "y"]].equals(base[["game_id", "y"]]):
            raise ValueError("Variants must score identical games")
        report["pooled"][name] = {"games": len(pooled_frame), "metrics": metrics(pooled_frame.y, pooled_frame.p),
                                  "raw_metrics": metrics(pooled_frame.y, pooled_frame.p_raw)}
    report["pooled"]["extended_minus_base_log_loss"] = (report["pooled"]["extended"]["metrics"]["log_loss"]
                                                        - report["pooled"]["base"]["metrics"]["log_loss"])
    write_json(out/"report.json", report)
    lines = ["# Box-score feature extension: development comparison", "", WARNING, "", protocol, "",
             f"Base features ({len(FEATURES)}): {', '.join(FEATURES)}",
             f"Added ({len(BOX_FEATURES)}): {', '.join(BOX_FEATURES)}", "",
             "Per-fold calibrated log loss (lower is better):"]
    for season, fold in report["folds"].items():
        line = f"- {season}, n={fold['split_counts']['validation']}: " + "; ".join(
            f"{k}={v['metrics']['log_loss']:.6f}" for k, v in fold["models"].items())
        ci = fold["extended_minus_base"]
        lines.append(line)
        lines.append(f"  extended minus base: {ci['difference']:+.6f}; "
                     f"95% block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]"
                     + ("  (excludes zero)" if ci['ci95'][1] < 0 or ci['ci95'][0] > 0 else "  (includes zero)"))
    lines.extend(["", "Pooled descriptive metrics:"])
    for name in ("base", "extended"):
        m = report["pooled"][name]
        lines.append(f"- {name}: n={m['games']}; log loss={m['metrics']['log_loss']:.6f}; "
                     f"Brier={m['metrics']['brier']:.6f}; accuracy={m['metrics']['accuracy']:.2%}; "
                     f"raw log loss={m['raw_metrics']['log_loss']:.6f}")
    lines.append(f"- pooled extended minus base: {report['pooled']['extended_minus_base_log_loss']:+.6f}")
    lines.extend(["", "Negative favors the extended set. Pooled folds share training history and are",
                  "descriptive. Intervals exclude training and model-selection uncertainty and are not",
                  "multiplicity-corrected. No feature set is promoted by this command, and nothing here",
                  "is confirmation: these folds have been inspected repeatedly."])
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "pooled_extended_minus_base": report["pooled"]["extended_minus_base_log_loss"],
            "report_command": f'sports report --path "{out}"'}
