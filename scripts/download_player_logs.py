"""Download player game logs (minutes and box statistics) via nba_api.

Free public endpoint, cached per season under out/raw; the combined CSV is only
rewritten from caches, so reruns are cheap and reproducible. These logs support
player-impact RESEARCH features: what a listed player's historical minutes and
production were before a game. They say nothing about availability by
themselves and must never replace declared injury status (actual absence would
leak the outcome).
"""
import argparse
import json
import time
from pathlib import Path
import pandas as pd


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seasons", required=True, help="Comma-separated, e.g. 2020-21,2021-22")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out)
    (out/"raw").mkdir(parents=True, exist_ok=True)
    try:
        from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
    except ImportError as exc:
        raise SystemExit("Install with: python -m pip install -e '.[nba]'") from exc
    frames = []
    for season in [s.strip() for s in a.seasons.split(",") if s.strip()]:
        cache = out/"raw"/f"player-logs-{season}.json"
        if cache.exists():
            print(f"Reusing cached player logs {season}", flush=True)
            frame = pd.read_json(cache)
        else:
            print(f"Downloading player logs {season}", flush=True)
            frame = LeagueGameLog(season=season, player_or_team_abbreviation="P",
                                  timeout=120).get_data_frames()[0]
            if frame.empty:
                raise SystemExit(f"Empty player log for {season}")
            frame.to_json(cache, orient="records", date_format="iso")
            time.sleep(1)
        frame["requested_season"] = season
        frames.append(frame)
    logs = pd.concat(frames, ignore_index=True)
    logs["GAME_ID"] = logs.GAME_ID.astype(str).str.zfill(10)
    dest = out/"nba-player-games.csv"
    logs.to_csv(dest, index=False)
    (out/"manifest.json").write_text(json.dumps({
        "source": "nba_api LeagueGameLog player_or_team_abbreviation=P",
        "seasons": a.seasons.split(","), "rows": len(logs),
        "players": int(logs.PLAYER_ID.nunique()),
        "warning": "Box statistics only; availability must come from declared injury reports. "
                   "Minutes for a game become known only after it is played; feature builders "
                   "must exclude the target game and anything after it."}, indent=2)+"\n")
    print(f"Saved {len(logs)} player-game rows to {dest}")


if __name__ == "__main__":
    main()
