"""Download nflverse weekly QB statistics, cached and hashed per season.

Free CC-BY-4.0 nflverse feed. Weekly rows carry no publication timestamp, so a
row becomes usable only once its GAME's result was available — the join and the
cutoff logic live in nfl_qb.py, not here. This script only stores and hashes.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

BASE = ("https://github.com/nflverse/nflverse-data/releases/download/"
        "player_stats/stats_player_week_{season}.csv")
KEEP = ["season", "week", "season_type", "team", "player_id", "player_display_name",
        "position", "passing_epa", "passing_yards", "passing_tds",
        "passing_interceptions", "attempts"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seasons", required=True, help="e.g. 2019,2020,2021")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out)
    (out/"raw").mkdir(parents=True, exist_ok=True)
    frames, sources = [], []
    for season in [s.strip() for s in a.seasons.split(",") if s.strip()]:
        cache = out/"raw"/f"stats_player_week_{season}.csv"
        meta_path = out/"raw"/f"stats_player_week_{season}.source.json"
        if cache.exists() and meta_path.exists():
            print(f"Reusing cached QB stats {season}", flush=True)
            meta = json.loads(meta_path.read_text())
        else:
            url = BASE.format(season=season)
            print(f"Downloading QB stats {season}", flush=True)
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=180) as r:
                body = r.read()
            cache.write_bytes(body)
            meta = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "capture": "backfill", "license": "CC-BY-4.0 (nflverse)"}
            meta_path.write_text(json.dumps(meta, indent=2)+"\n")
        if hashlib.sha256(cache.read_bytes()).hexdigest() != meta["sha256"]:
            raise SystemExit(f"Cached QB stats for {season} do not match their hash")
        frame = pd.read_csv(cache, low_memory=False)
        frame = frame[frame.position.eq("QB") & frame.season_type.eq("REG")]
        frames.append(frame[[c for c in KEEP if c in frame.columns]])
        sources.append(meta)
    stats = pd.concat(frames, ignore_index=True)
    dest = out/"nfl-qb-weekly.csv"
    stats.to_csv(dest, index=False)
    (out/"manifest.json").write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(), "sport": "nfl",
        "rows": len(stats), "quarterbacks": int(stats.player_id.nunique()),
        "seasons": a.seasons.split(","), "sources": sources,
        "warning": "Regular season QB rows only. No publication timestamp exists in the feed; "
                   "usability is decided by the joined game's result availability, never by "
                   "the week label alone."}, indent=2)+"\n")
    print(f"Saved {len(stats)} QB week rows to {dest}")


if __name__ == "__main__":
    main()
