"""NFL quarterback player-impact RESEARCH candidate.

Separate research track. Nothing here is in the frozen NFL pair or any issued
prospective record.

## The three participation concepts, kept strictly apart

The goal's hardest requirement here is not statistical, it is definitional:

  declared status       what an injury report SAYS before the game.
                        The nflverse injuries feed carries NO timestamp, so a
                        backfilled row cannot prove what was declared before a
                        past kickoff. Not used as a pregame input here.
  expected participation who we BELIEVE will start, using only pregame-available
                        information. Implemented as the quarterback who started
                        that team's most recent game whose RESULT was already
                        available at the cutoff.
  actual participation  who DID start. `games.csv` home_qb_id/away_qb_id is
                        exactly this, and using it as a pregame input would
                        leak the lineup. It is used ONLY to establish history
                        for games already settled, never for the target game.

The leak is subtle and worth stating plainly: the target game's own qb_id is
known in the historical file but was not knowable at its cutoff. Every feature
below is therefore derived from strictly earlier games.
"""
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

QB_WINDOW = 8
QB_FEATURES = ["qb_epa_diff", "qb_starts_diff", "qb_unknown_diff", "qb_backup_diff"]


def _weekly_lookup(qb_weekly, games):
    """Map (season, week, team) -> that week's primary QB row.

    The stats feed has no game id, so the join is by season/week/team; where a
    team used more than one quarterback in a week, the one with the most
    attempts is treated as the starter.
    """
    frame = qb_weekly.copy()
    frame["attempts"] = pd.to_numeric(frame.get("attempts"), errors="coerce").fillna(0)
    frame = frame.sort_values("attempts", ascending=False)
    frame = frame.drop_duplicates(["season", "week", "team"], keep="first")
    return {(int(r.season), int(r.week), str(r.team)):
            {"player_id": str(r.player_id),
             "passing_epa": float(r.passing_epa) if pd.notna(r.passing_epa) else 0.}
            for r in frame.itertuples()}


def qb_frame(games, qb_weekly):
    """Home-minus-away expected-starter features, built in availability order.

    `games` must carry season, week, home_id, away_id, decision_at, available_at
    and the ACTUAL starter columns home_qb_id/away_qb_id for settled games.
    """
    lookup = _weekly_lookup(qb_weekly, games)
    history = defaultdict(lambda: deque(maxlen=QB_WINDOW))   # qb -> recent epa
    starts = defaultdict(int)                                # qb -> settled starts
    team_last_starter = {}                                   # team -> qb of last settled game
    team_starter_counts = defaultdict(lambda: defaultdict(int))
    decisions = games.sort_values(["decision_at", "game_id"])
    events = list(games.sort_values(["available_at", "game_id"]).itertuples())
    rows, unknown, matched = [], 0, 0
    ei = 0
    for row in decisions.itertuples():
        while ei < len(events) and events[ei].available_at < row.decision_at:
            e = events[ei]
            for side in ("home", "away"):
                team = getattr(e, f"{side}_id")
                actual = getattr(e, f"{side}_qb_id", None)
                key = (int(e.season), int(e.week), str(team))
                weekly = lookup.get(key)
                starter = str(actual) if pd.notna(actual) else (
                    weekly["player_id"] if weekly else None)
                if starter is None:
                    continue
                if weekly is not None and weekly["player_id"] == starter:
                    history[starter].append(weekly["passing_epa"])
                starts[starter] += 1
                team_last_starter[str(team)] = starter
                team_starter_counts[str(team)][starter] += 1
            ei += 1
        values = {}
        for side in ("home", "away"):
            team = str(getattr(row, f"{side}_id"))
            # EXPECTED starter: last settled game's starter. Never this game's.
            expected = team_last_starter.get(team)
            if expected is None or not history[expected]:
                unknown += 1
                values[side] = {"epa": 0., "starts": 0., "unknown": 1., "backup": 0.}
                continue
            matched += 1
            counts = team_starter_counts[team]
            most_used = max(counts, key=counts.get) if counts else expected
            values[side] = {"epa": float(np.mean(history[expected])),
                            "starts": float(starts[expected]), "unknown": 0.,
                            "backup": float(expected != most_used)}
        rows.append({"game_id": row.game_id,
                     "qb_epa_diff": values["home"]["epa"]-values["away"]["epa"],
                     "qb_starts_diff": values["home"]["starts"]-values["away"]["starts"],
                     "qb_unknown_diff": values["home"]["unknown"]-values["away"]["unknown"],
                     "qb_backup_diff": values["home"]["backup"]-values["away"]["backup"]})
    frame = pd.DataFrame(rows)
    frame.attrs["expected_starter_matched"] = matched
    frame.attrs["expected_starter_unknown"] = unknown
    return frame


def compare_qb(data, qb_weekly_csv, out):
    """Base NFL features versus the same plus QB expected-starter features."""
    from .io import code_hash, digest, new_dir, now, write_json
    from .nfl_data import NFL_FEATURES, build_nfl_features, load_nfl_games
    from .nfl_train import (DEVELOPMENT_FOLDS, FINAL_HOLDOUT_SEASON, WARNING,
                            fit_fold, fold_frames, paired_week_interval)
    from .nfl_data import three_way_metrics
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    games = load_nfl_games(data)
    games = games[games.season < FINAL_HOLDOUT_SEASON].copy()
    raw = pd.read_csv(Path(data)/"games.csv", dtype={"game_id": str})
    qb_columns = [c for c in ("game_id", "home_qb_id", "away_qb_id") if c in raw.columns]
    if len(qb_columns) < 3:
        raise ValueError("Dataset lacks home_qb_id/away_qb_id; rebuild with a newer adapter")
    games = games.merge(raw[qb_columns], on="game_id", how="left", validate="one_to_one")
    weekly = pd.read_csv(qb_weekly_csv)
    features = build_nfl_features(games).merge(
        qb_frame(games, weekly), on="game_id", validate="one_to_one")
    extended = list(NFL_FEATURES)+QB_FEATURES
    out = new_dir(out)
    features.to_csv(out/"development_features.csv", index=False)
    protocol = (
        "RESEARCH CANDIDATE. Base NFL features versus the same plus quarterback "
        f"expected-starter features: mean passing EPA over that quarterback's last "
        f"{QB_WINDOW} games whose results were available before the cutoff, settled "
        "start count, an unknown-starter indicator and a backup indicator, all home "
        "minus away. The EXPECTED starter is the quarterback who started the team's "
        "most recent settled game; the target game's own starter is never read. "
        "Declared injury status is NOT used: the nflverse injuries feed carries no "
        "timestamp and cannot establish what was declared before a past kickoff. "
        "Development evidence only; not confirmation.")
    report = {"created_at": now(), "sport": "nfl", "warning": WARNING, "protocol": protocol,
              "qb_features": QB_FEATURES, "window_games": QB_WINDOW,
              "expected_starter_matched": features.attrs.get("expected_starter_matched"),
              "folds": {}, "pooled": {}, "code_sha256": code_hash(),
              "provenance": {"qb_weekly_sha256": digest(qb_weekly_csv),
                             "data_sha256": {f: digest(data/f)
                                             for f in ("games.csv", "results.csv")}},
              }
    pooled = {"base": [], "qb": []}
    for season in DEVELOPMENT_FOLDS:
        fit, cal, val = fold_frames(features, season)
        fold = {"split_counts": {"fit": len(fit), "calibration": len(cal),
                                 "validation": len(val)}, "models": {}}
        predictions = {}
        for name, columns in (("base", list(NFL_FEATURES)), ("qb", extended)):
            _, _, _, p, p_tie = fit_fold(fit, cal, val, columns=columns)
            fold["models"][name] = three_way_metrics(val, p, p_tie)
            predictions[name] = p
            record = val[["game_id", "season", "decision_at", "y", "is_tie"]].copy()
            record["p"] = p
            pooled[name].append(record)
        decided = val[val.is_tie == 0]
        mask = (val.is_tie == 0).to_numpy()
        fold["qb_minus_base"] = paired_week_interval(
            decided, predictions["qb"][mask], predictions["base"][mask])
        report["folds"][str(season)] = fold
        print(f"{season}: base={fold['models']['base']['decided_log_loss']:.6f} "
              f"qb={fold['models']['qb']['decided_log_loss']:.6f}", flush=True)
    reference = pd.concat(pooled["base"], ignore_index=True)
    for name, parts in pooled.items():
        combined = pd.concat(parts, ignore_index=True)
        if not combined[["game_id", "y"]].equals(reference[["game_id", "y"]]):
            raise ValueError("Variants must score identical games")
        report["pooled"][name] = three_way_metrics(combined, combined.p, .002)
    decided_mask = (reference.is_tie == 0).to_numpy()
    scored = {n: pd.concat(p, ignore_index=True).p.to_numpy()[decided_mask]
              for n, p in pooled.items()}
    report["pooled"]["qb_minus_base"] = paired_week_interval(
        reference[reference.is_tie == 0], scored["qb"], scored["base"])
    write_json(out/"report.json", report)
    ci = report["pooled"]["qb_minus_base"]
    text = ("interval withheld" if ci["ci95"] is None else
            f"95% week-block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]"
            + ("  (excludes zero)" if ci["ci95"][1] < 0 or ci["ci95"][0] > 0
               else "  (includes zero)"))
    lines = ["# NFL quarterback impact research comparison", "", WARNING, "", protocol, "", ""]
    for season in DEVELOPMENT_FOLDS:
        f = report["folds"][str(season)]
        lines.append(f"- {season}: base {f['models']['base']['decided_log_loss']:.6f} vs "
                     f"qb {f['models']['qb']['decided_log_loss']:.6f}")
    lines += ["", f"Pooled qb minus base (decided games): {ci['difference']:+.6f}; {text}.", "",
              "Development evidence only; adoption would require a new frozen release and "
              "prospective capture."]
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "pooled_difference": ci["difference"]}
