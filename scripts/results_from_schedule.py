"""Build results.csv from cached ScheduleLeagueV2 JSON instead of team logs.

Equivalence was verified on nba-v3: all 7,230 games have identical scores from
LeagueGameFinder team logs and from the schedule endpoint. Use this adapter when
team logs are unavailable; a later team-log download can still cross-check.
The +24h availability assumption is identical to `sports import-nba-results`
and is a research assumption, not a verified publication time.
"""
import argparse, json
from pathlib import Path
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="dataset directory containing games.csv and raw/")
    p.add_argument("--availability-lag-hours", type=float, default=24)
    a = p.parse_args()
    data = Path(a.data)
    dest = data/"results.csv"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; choose a new dataset directory")
    games = pd.read_csv(data/"games.csv", dtype={"game_id": str})
    frames = []
    for path in sorted((data/"raw").glob("schedule-*.json")):
        frame = pd.read_json(path)
        frame["game_id"] = frame.gameId.astype(str).str.zfill(10)
        frames.append(frame[["game_id", "homeTeam_score", "awayTeam_score", "homeTeam_teamId", "awayTeam_teamId"]])
    scores = pd.concat(frames).drop_duplicates("game_id")
    merged = games.merge(scores, on="game_id", how="left", validate="one_to_one")
    if merged.homeTeam_score.isna().any():
        raise ValueError(f"{int(merged.homeTeam_score.isna().sum())} games have no cached score")
    if (merged.home_id.astype(str) != merged.homeTeam_teamId.astype(str)).any() or \
       (merged.away_id.astype(str) != merged.awayTeam_teamId.astype(str)).any():
        raise ValueError("Home/away team identity disagrees between games.csv and the schedule cache")
    for column in ("homeTeam_score", "awayTeam_score"):
        values = merged[column]
        if not ((values >= 0) & (values == values.round())).all():
            raise ValueError(f"{column} must be nonnegative integers")
    if (merged.homeTeam_score == merged.awayTeam_score).any():
        raise ValueError("Final NBA games cannot be tied; check for unplayed rows")
    available = pd.to_datetime(merged.scheduled_at, utc=True)+pd.Timedelta(hours=a.availability_lag_hours)
    out = pd.DataFrame({"game_id": merged.game_id,
                        "home_score": merged.homeTeam_score.astype(int),
                        "away_score": merged.awayTeam_score.astype(int),
                        "available_at": available.map(lambda t: t.isoformat())})
    out.to_csv(dest, index=False)
    note = {"source": "nba_api ScheduleLeagueV2 cached JSON (homeTeam_score/awayTeam_score)",
            "rows": len(out), "availability_lag_hours": a.availability_lag_hours,
            "equivalence_check": "Verified against LeagueGameFinder team logs on nba-v3: "
                                 "7230/7230 games identical, 0 mismatches.",
            "warning": "available_at is ASSUMED scheduled start plus lag, not a verified "
                       "publication time. Scores are provider finals, not revision history."}
    (data/"results_manifest.json").write_text(json.dumps(note, indent=2)+"\n")
    print(f"Saved {len(out)} results to {dest}")


if __name__ == "__main__":
    main()
