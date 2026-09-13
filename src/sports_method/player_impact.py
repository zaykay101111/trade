"""Player-impact RESEARCH features: weight declared statuses by prior minutes.

Separate research candidate only — nothing here touches the frozen forecast
surface, the deployed baseline, or the injury challenger pair.

Availability still comes exclusively from declared injury statuses; player game
logs contribute only each listed player's historical minutes and scoring. A
listed player's history window is bounded by the same result-availability rule
as team features: a log row becomes usable only once its game's result was
available (scheduled + 24h assumption), so the previous night's minutes are
often NOT usable at a T-60 cutoff. Actual absence is never substituted for a
declared status.
"""
import re
import unicodedata
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .injury import (availability_frame, availability_counts, team_lookup,
                     AVAILABILITY_FEATURES, STATUSES, PARSER_VERSION)

WINDOW = 10
WEIGHTED = ("Out", "Doubtful", "Questionable", "Probable")
IMPACT_FEATURES = [f"{s.lower()}_minutes_diff" for s in WEIGHTED] + \
                  ["out_points_diff", "unmatched_listed_diff"]


def normalize_name(name):
    """'Porter Jr., Michael' -> 'michael porter jr'; strips accents/punctuation."""
    name = str(name)
    if "," in name:
        last, first = name.split(",", 1)
        name = first.strip()+" "+last.strip()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[.'’-]", " ", name)).strip().lower()


def player_history(player_logs, games):
    """Per (team, player) sorted arrays of (available_at, minutes, points).

    Joining on GAME_ID inherits the dataset's exact result availability time;
    log rows for games outside the dataset are dropped rather than guessed at.
    """
    logs = player_logs.copy()
    logs["GAME_ID"] = logs.GAME_ID.astype(str).str.zfill(10)
    stamps = games[["game_id", "available_at"]].rename(columns={"game_id": "GAME_ID"})
    logs = logs.merge(stamps, on="GAME_ID", how="inner")
    logs["key"] = logs.PLAYER_NAME.map(normalize_name)
    logs["team_id"] = logs.TEAM_ID.astype(str)
    logs = logs.sort_values("available_at")
    history = {}
    for key, part in logs.groupby(["team_id", "key"], sort=False):
        history[key] = (part.available_at.astype("int64").to_numpy(),
                        part.MIN.to_numpy(dtype=float),
                        part.PTS.to_numpy(dtype=float))
    return history, len(logs)


def prior_stats(history, team_id, player, cutoff):
    entry = history.get((str(team_id), normalize_name(player)))
    if entry is None:
        return None
    stamps, minutes, points = entry
    end = int(np.searchsorted(stamps, pd.Timestamp(cutoff).value, "left"))
    if end == 0:
        return None
    start = max(0, end-WINDOW)
    return float(minutes[start:end].mean()), float(points[start:end].mean())


def impact_frame(games, reports, lookup, player_logs, history_games=None):
    """Home-minus-away sums of listed players' prior mean minutes, by status."""
    counts = availability_counts(games, reports, lookup)
    history, joined_rows = player_history(player_logs,
                                          games if history_games is None else history_games)
    reports = reports.copy()
    reports["team_id"] = reports.team.map(lookup)
    listed = reports[reports.status.isin(STATUSES) & reports.player.notna()]
    by_snapshot = {k: v for k, v in listed.groupby(["source", "team_id"], sort=False)}
    rows, unmatched_total, matched_total = [], 0, 0
    for game in counts.itertuples():
        row = {"game_id": game.game_id}
        side_values = {}
        for side in ("home", "away"):
            values = {s: 0.0 for s in WEIGHTED}
            values["out_points"] = 0.0
            values["unmatched"] = 0
            if getattr(game, f"{side}_state") == "usable":
                team = getattr(game, f"{side}_id")
                snapshot = by_snapshot.get((getattr(game, f"{side}_source"), str(team)))
                date = getattr(game, f"{side}_game_date")
                matchup = getattr(game, f"{side}_matchup")
                if snapshot is not None:
                    chosen_at = pd.to_datetime(getattr(game, f"{side}_report_at"), utc=True)
                    snapshot = snapshot[(snapshot.game_date.astype(str) == str(date))
                                        & (snapshot.matchup.astype(str) == str(matchup))
                                        & (pd.to_datetime(snapshot.report_at, utc=True) == chosen_at)]
                for listed_row in ([] if snapshot is None else snapshot.itertuples()):
                    if listed_row.status not in WEIGHTED:
                        continue
                    stats = prior_stats(history, team, listed_row.player, game.decision_at)
                    if stats is None:
                        values["unmatched"] += 1
                        unmatched_total += 1
                        continue
                    matched_total += 1
                    values[listed_row.status] += stats[0]
                    if listed_row.status == "Out":
                        values["out_points"] += stats[1]
            side_values[side] = values
        for status in WEIGHTED:
            row[f"{status.lower()}_minutes_diff"] = side_values["home"][status]-side_values["away"][status]
        row["out_points_diff"] = side_values["home"]["out_points"]-side_values["away"]["out_points"]
        row["unmatched_listed_diff"] = side_values["home"]["unmatched"]-side_values["away"]["unmatched"]
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.attrs["matched_listed_players"] = matched_total
    frame.attrs["unmatched_listed_players"] = unmatched_total
    frame.attrs["player_log_rows_joined"] = joined_rows
    return frame


def compare_impact(data, parsed_csv, team_log, player_logs, out, threads=2):
    """Availability-extended features versus the same plus player-impact weights."""
    from .free_box import _fit
    from .free_data import FEATURES, build_features, load_games
    from .free_train import metrics, paired_interval, partition, WARNING
    from .free_validate import YEARS, fold_boundaries
    from .io import new_dir, write_json, digest, code_hash, now
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    frame = load_games(data)
    dev = frame[frame.decision_at < pd.Timestamp("2025-07-01", tz="UTC")].copy()
    reports = pd.read_csv(parsed_csv)
    manifest_path = Path(parsed_csv).with_suffix(Path(parsed_csv).suffix+".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    from .injury import __file__ as injury_file
    if manifest["csv_sha256"] != digest(parsed_csv) or manifest["parser_sha256"] != digest(Path(injury_file)):
        raise ValueError("Parsed CSV or parser drifted; reparse into a new file")
    reports["report_at"] = pd.to_datetime(reports.report_at, utc=True, format="mixed")
    lookup = team_lookup(team_log)
    logs = pd.read_csv(player_logs)
    availability = availability_frame(dev, reports, lookup)
    impact = impact_frame(dev, reports, lookup, logs)
    features = (build_features(dev)
                .merge(availability, on="game_id", validate="one_to_one")
                .merge(impact, on="game_id", validate="one_to_one"))
    extended = list(FEATURES)+AVAILABILITY_FEATURES
    with_impact = extended+IMPACT_FEATURES
    out = new_dir(out)
    features.to_csv(out/"development_features.csv", index=False)
    protocol = ("RESEARCH CANDIDATE. Availability-extended model versus the same plus "
        f"impact weights: for each listed player on a usable snapshot, mean minutes over "
        f"the last {WINDOW} of their own games whose results were available before the "
        "cutoff, summed per declared status per side, home minus away, plus Out scoring "
        "and an unmatched-player indicator. Player logs joined to result availability by "
        "game id, so last night's minutes are excluded when not yet available. Statuses "
        "remain declared only; actual absence is never substituted. Reports were "
        "backfilled; development evidence only, repeated inspection risks overfitting. "
        "Primary contrast is impact minus availability-extended.")
    report = {"created_at": now(), "warning": WARNING, "protocol": protocol,
              "impact_features": IMPACT_FEATURES, "window_games": WINDOW,
              "matched_listed_players": impact.attrs["matched_listed_players"],
              "unmatched_listed_players": impact.attrs["unmatched_listed_players"],
              "match_rate": impact.attrs["matched_listed_players"]/max(1,
                  impact.attrs["matched_listed_players"]+impact.attrs["unmatched_listed_players"]),
              "player_log_rows_joined": impact.attrs["player_log_rows_joined"],
              "provenance": {"parsed_csv_sha256": digest(parsed_csv),
                             "team_log_sha256": digest(team_log),
                             "player_logs_sha256": digest(player_logs),
                             "parser_version": PARSER_VERSION},
              "folds": {}, "pooled": {}, "code_sha256": code_hash(),
              "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")}}
    pooled = {"extended": [], "impact": []}
    for year in YEARS:
        season = f"{year}-{str(year+1)[-2:]}"
        parts = partition(features, fold_boundaries(year))
        combined = pd.concat([parts["train"], parts["tune"]])
        cal, val = parts["calibration"], parts["validation"]
        fold = {"split_counts": {k: len(v) for k, v in parts.items()},
                "validation_coverage": float(val.availability_covered.mean()), "models": {}}
        predictions = {}
        for name, columns in (("extended", extended), ("impact", with_impact)):
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
            fold["models"][name] = {"metrics": metrics(val.y, p), "raw_metrics": metrics(val.y, raw)}
        fold["impact_minus_extended"] = paired_interval(val, predictions["impact"], predictions["extended"])
        report["folds"][season] = fold
        print(f"{season}: extended={fold['models']['extended']['metrics']['log_loss']:.6f} "
              f"impact={fold['models']['impact']['metrics']['log_loss']:.6f}", flush=True)
    base = pd.concat(pooled["extended"], ignore_index=True)
    for name, frames_ in pooled.items():
        combined = pd.concat(frames_, ignore_index=True)
        if not combined[["game_id", "y"]].equals(base[["game_id", "y"]]):
            raise ValueError("Variants must score identical games")
        report["pooled"][name] = {"games": len(combined),
                                  "metrics": metrics(combined.y, combined.p),
                                  "raw_metrics": metrics(combined.y, combined.p_raw)}
    report["pooled"]["impact_minus_extended_log_loss"] = (
        report["pooled"]["impact"]["metrics"]["log_loss"]
        - report["pooled"]["extended"]["metrics"]["log_loss"])
    write_json(out/"report.json", report)
    pooled_diff = report["pooled"]["impact_minus_extended_log_loss"]
    lines = ["# Player-impact research comparison", "", report["warning"], "", protocol, "",
             f"Listed-player match rate: {report['match_rate']:.1%} "
             f"({report['matched_listed_players']} matched, {report['unmatched_listed_players']} unmatched).", ""]
    for season, fold in report["folds"].items():
        ci = fold["impact_minus_extended"]
        lines.append(f"- {season}: impact minus extended {ci['difference']:+.6f}; "
                     f"95% block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]"
                     + ("  (excludes zero)" if ci['ci95'][1] < 0 or ci['ci95'][0] > 0 else "  (includes zero)"))
    lines += ["", f"Pooled impact minus extended log loss: {pooled_diff:+.6f}", "",
              "Development evidence only; adoption would require a new frozen release "
              "and prospective capture."]
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "pooled_difference": pooled_diff,
            "match_rate": report["match_rate"]}
