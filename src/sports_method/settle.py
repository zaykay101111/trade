"""Fold newly settled games into a rolling dataset for prospective forecasting.

Without this the collector's history freezes at the end of the base dataset:
Elo stops updating and rolling windows keep describing last season. Scores come
from the cached ScheduleLeagueV2 payload, the adapter verified against
LeagueGameFinder team logs on nba-v3 at 7,230/7,230 games with zero mismatches.

Every run writes a NEW dataset directory. Nothing is ever edited in place.
"""
import json
from pathlib import Path
import pandas as pd
from .free_data import load_games
from .io import new_dir, write_json, digest, now, code_hash

PLACEHOLDER_TEAM = "0"
RESULTS_COLUMNS = ["game_id", "home_score", "away_score", "available_at"]
GAMES_COLUMNS = ["game_id", "home_id", "away_id", "home_name", "away_name", "scheduled_at",
                 "schedule_observed_at", "decision_at", "season_type", "contract",
                 "is_neutral", "source_status"]
CONTRACT = "nba_regular_fullgame_moneyline_ot"


def settled_rows(raw_dir, observed_lag_hours=48, availability_lag_hours=24):
    """Completed, fully assigned regular-season games from cached schedule JSON."""
    games, results, skipped = [], [], {"not_regular_season": 0, "unassigned_teams": 0,
                                       "not_final": 0, "missing_score": 0, "tied": 0}
    for path in sorted(Path(raw_dir).glob("schedule-*.json")):
        frame = pd.read_json(path)
        for row in frame.itertuples():
            gid = str(getattr(row, "gameId", "")).zfill(10)
            if not gid.startswith("002"):
                skipped["not_regular_season"] += 1
                continue
            home_id, away_id = str(int(row.homeTeam_teamId)), str(int(row.awayTeam_teamId))
            if PLACEHOLDER_TEAM in (home_id, away_id) or home_id == away_id:
                skipped["unassigned_teams"] += 1
                continue
            status = str(getattr(row, "gameStatusText", "")).strip()
            if not status.startswith("Final"):
                skipped["not_final"] += 1
                continue
            home_score, away_score = getattr(row, "homeTeam_score", None), getattr(row, "awayTeam_score", None)
            if home_score is None or away_score is None or pd.isna(home_score) or pd.isna(away_score):
                skipped["missing_score"] += 1
                continue
            if int(home_score) == int(away_score):
                # A completed NBA game cannot be tied; treat as unreliable rather than guessing.
                skipped["tied"] += 1
                continue
            scheduled = pd.Timestamp(row.gameDateTimeUTC, tz="UTC") if pd.Timestamp(row.gameDateTimeUTC).tzinfo is None \
                else pd.Timestamp(row.gameDateTimeUTC)
            games.append({"game_id": gid, "home_id": home_id, "away_id": away_id,
                          "home_name": str(row.homeTeam_teamName), "away_name": str(row.awayTeam_teamName),
                          "scheduled_at": scheduled.isoformat(),
                          "schedule_observed_at": (scheduled-pd.Timedelta(hours=observed_lag_hours)).isoformat(),
                          "decision_at": (scheduled-pd.Timedelta(minutes=60)).isoformat(),
                          "season_type": "regular", "contract": CONTRACT,
                          "is_neutral": bool(getattr(row, "isNeutral", False)),
                          "source_status": status})
            results.append({"game_id": gid, "home_score": int(home_score), "away_score": int(away_score),
                            "available_at": (scheduled+pd.Timedelta(hours=availability_lag_hours)).isoformat()})
    # Both frames need explicit columns: before a season's first game settles,
    # these lists are empty and a bare DataFrame would have no columns at all,
    # so every later .game_id access would raise.
    return (pd.DataFrame(games, columns=GAMES_COLUMNS),
            pd.DataFrame(results, columns=RESULTS_COLUMNS), skipped)


def merge_settled(base, season_raw, out, *, observed_lag_hours=48, availability_lag_hours=24):
    """Append newly settled games to a base dataset, writing a new dataset directory."""
    base, out = Path(base), Path(out)
    if out.exists():
        raise FileExistsError(f"Output exists: {out}; choose a new dataset directory")
    base_games = pd.read_csv(base/"games.csv", dtype={"game_id": str, "home_id": str, "away_id": str})
    base_results = pd.read_csv(base/"results.csv", dtype={"game_id": str})
    if set(base_games.game_id) != set(base_results.game_id):
        raise ValueError("Base dataset schedule and results disagree")
    new_games, new_results, skipped = settled_rows(season_raw, observed_lag_hours, availability_lag_hours)
    known = set(base_games.game_id)
    fresh = ~new_games.game_id.isin(known)
    added_games = new_games[fresh]
    added_results = new_results[new_results.game_id.isin(set(added_games.game_id))]
    if added_games.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs in newly settled games")
    games = pd.concat([base_games, added_games], ignore_index=True)
    results = pd.concat([base_results, added_results], ignore_index=True)
    # Write one canonical timestamp spelling. The base file and the new rows can
    # disagree (ISO "T" versus a space), and the loader on the frozen forecast
    # surface parses strictly; normalising here keeps that surface untouched.
    for frame, columns in ((games, ("scheduled_at", "schedule_observed_at", "decision_at")),
                           (results, ("available_at",))):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], utc=True, format="mixed").map(
                lambda t: t.isoformat())
    new_dir(out)
    games.to_csv(out/"games.csv", index=False)
    results.to_csv(out/"results.csv", index=False)
    manifest = {"created_at": now(), "mode": "rolling_settled", "base": str(base),
                "season_raw": str(season_raw), "base_games": len(base_games),
                "added_games": len(added_games), "total_games": len(games),
                "already_known": int((~fresh).sum()), "skipped": skipped,
                "observed_lag_hours": observed_lag_hours,
                "availability_lag_hours": availability_lag_hours,
                "base_sha256": {f: digest(base/f) for f in ("games.csv", "results.csv")},
                "output_sha256": {f: digest(out/f) for f in ("games.csv", "results.csv")},
                "code_sha256": code_hash(),
                "warning": "Scores are provider finals from the schedule payload, not revision "
                           "history. available_at is ASSUMED scheduled start plus lag, not a "
                           "verified publication time. Neutral-site flags are provider values and "
                           "have needed manual correction before; review new neutral games."}
    write_json(out/"manifest.json", manifest)
    # The merged dataset must satisfy every validation the training path applies.
    checked = load_games(out)
    manifest["validated_games"] = len(checked)
    write_json(out/"manifest.json", manifest)
    return {"data": str(out), "base_games": len(base_games), "added_games": len(added_games),
            "total_games": len(games), "skipped": skipped,
            "note": "Point the collector's --data at this directory."}
