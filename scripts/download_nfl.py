"""Download the free nflverse schedule/result feed into a canonical dataset.

Resumable and reproducible: the raw CSV is cached verbatim under out/raw with
its SHA-256 and actual retrieval time, and the canonical games.csv/results.csv
are derived from that cache. Re-running without --refresh never re-requests.

Two timestamps are NOT the same thing and are kept apart:
  retrieved_at        - when WE fetched the file (real, recorded by us)
  schedule_observed_at - a RECONSTRUCTED assumption (kickoff minus a lag)
The provider supplies no publication or revision timestamp, so a backfilled
schedule can never establish what was visible before a past game. Capture
marks each dataset as "backfill" or "prospective" accordingly.

Regular season, full-game moneyline only: playoffs, preseason and college are
excluded here rather than downstream, so they cannot leak into a dataset.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

import pandas as pd

SOURCE = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
LICENSE = "CC-BY-4.0 (nflverse); aggregation of NFL/NGS/PFR sources, not an official feed"
# Kickoff local times are US Eastern with no timezone column in the feed.
LOCAL_ZONE = "America/New_York"
CONTRACT = "nfl_regular_fullgame_moneyline_ot_tie_push"
GAMES_COLUMNS = ["game_id", "sport", "season", "week", "home_id", "away_id", "home_name",
                 "away_name", "scheduled_at", "schedule_observed_at", "decision_at",
                 "season_type", "contract", "is_neutral", "div_game", "roof", "source_status",
                 # ACTUAL starting quarterbacks. Present only for played games and
                 # never a pregame input: they establish history for settled games,
                 # and using a target game's own value would leak its lineup.
                 "home_qb_id", "away_qb_id"]


def fetch(url, timeout=120):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as response:
        if response.status != 200:
            raise SystemExit(f"HTTP {response.status} for {url}")
        return response.read()


def build(raw_csv, *, observed_lag_hours, availability_lag_hours, decision_lead_minutes):
    frame = pd.read_csv(raw_csv, dtype={"game_id": str})
    frame = frame[frame.game_type == "REG"].copy()
    if frame.empty:
        raise SystemExit("No regular-season rows in the source file")
    local = pd.to_datetime(frame.gameday.astype(str)+" "+frame.gametime.astype(str),
                           format="%Y-%m-%d %H:%M", errors="coerce")
    missing_time = local.isna()
    # A row with no usable kickoff cannot carry a defensible T-60 cutoff.
    frame, local = frame[~missing_time].copy(), local[~missing_time]
    scheduled = local.dt.tz_localize(LOCAL_ZONE, ambiguous=True,
                                     nonexistent="shift_forward").dt.tz_convert("UTC")
    frame["scheduled_at"] = scheduled
    frame["decision_at"] = scheduled-pd.Timedelta(minutes=decision_lead_minutes)
    frame["schedule_observed_at"] = scheduled-pd.Timedelta(hours=observed_lag_hours)
    games = pd.DataFrame({
        "game_id": frame.game_id, "sport": "nfl", "season": frame.season.astype(int),
        "week": frame.week.astype(int),
        "home_id": frame.home_team.astype(str), "away_id": frame.away_team.astype(str),
        "home_name": frame.home_team.astype(str), "away_name": frame.away_team.astype(str),
        "scheduled_at": frame.scheduled_at.map(lambda t: t.isoformat()),
        "schedule_observed_at": frame.schedule_observed_at.map(lambda t: t.isoformat()),
        "decision_at": frame.decision_at.map(lambda t: t.isoformat()),
        "season_type": "regular", "contract": CONTRACT,
        "is_neutral": frame.location.astype(str).str.lower().eq("neutral"),
        "div_game": frame.div_game.fillna(0).astype(int),
        "roof": frame.roof.fillna("unknown").astype(str),
        "source_status": frame.result.notna().map({True: "Final", False: "Scheduled"}),
        "home_qb_id": frame.get("home_qb_id"), "away_qb_id": frame.get("away_qb_id"),
    })[GAMES_COLUMNS]
    played = frame[frame.result.notna()]
    results = pd.DataFrame({
        "game_id": played.game_id,
        "home_score": played.home_score.astype(int),
        "away_score": played.away_score.astype(int),
        "overtime": played.overtime.fillna(0).astype(int),
        "available_at": (played.scheduled_at+pd.Timedelta(hours=availability_lag_hours)
                         ).map(lambda t: t.isoformat()),
    })
    dropped = int(missing_time.sum())
    return games, results, dropped


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, help="New dataset directory")
    p.add_argument("--cache", help="Reuse a raw CSV already downloaded into another dataset")
    p.add_argument("--refresh", action="store_true", help="Re-request even if a cache exists")
    p.add_argument("--prospective", action="store_true",
                   help="Mark this capture as taken close to the games it covers")
    p.add_argument("--observed-lag-hours", type=float, default=48)
    p.add_argument("--availability-lag-hours", type=float, default=24)
    p.add_argument("--decision-lead-minutes", type=float, default=60)
    a = p.parse_args()
    out = Path(a.out)
    if (out/"games.csv").exists():
        raise SystemExit(f"Output already has games.csv: {out}; choose a new directory")
    (out/"raw").mkdir(parents=True, exist_ok=True)
    raw_csv = out/"raw"/"nflverse-games.csv"
    source_meta = out/"raw"/"nflverse-games.source.json"
    if a.cache and not a.refresh:
        cached = Path(a.cache)
        raw_csv.write_bytes(cached.read_bytes())
        meta = json.loads(Path(str(cached).replace(".csv", ".source.json")).read_text())
        meta["reused_from"] = str(cached)
    elif raw_csv.exists() and not a.refresh:
        meta = json.loads(source_meta.read_text())
    else:
        body = fetch(SOURCE)
        raw_csv.write_bytes(body)
        meta = {"url": SOURCE, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                "capture": "prospective" if a.prospective else "backfill",
                "license": LICENSE}
    source_meta.write_text(json.dumps(meta, indent=2)+"\n")
    if hashlib.sha256(raw_csv.read_bytes()).hexdigest() != meta["sha256"]:
        raise SystemExit("Cached raw CSV does not match its recorded hash")
    games, results, dropped = build(
        raw_csv, observed_lag_hours=a.observed_lag_hours,
        availability_lag_hours=a.availability_lag_hours,
        decision_lead_minutes=a.decision_lead_minutes)
    games.to_csv(out/"games.csv", index=False)
    results.to_csv(out/"results.csv", index=False)
    ties = int((results.home_score == results.away_score).sum())
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(), "sport": "nfl",
        "contract": CONTRACT, "source": meta, "rows": len(games),
        "played": len(results), "unplayed": len(games)-len(results),
        "ties": ties, "neutral_site": int(games.is_neutral.sum()),
        "dropped_missing_kickoff": dropped,
        "seasons": [int(games.season.min()), int(games.season.max())],
        "observed_lag_hours": a.observed_lag_hours,
        "availability_lag_hours": a.availability_lag_hours,
        "decision_lead_minutes": a.decision_lead_minutes,
        "warning": "Regular season only. Kickoff converted from US Eastern by us; the feed "
                   "carries no timezone, publication or revision timestamp. "
                   "schedule_observed_at is a RECONSTRUCTED assumption and is not evidence of "
                   "historical availability. available_at is ASSUMED kickoff plus lag, not a "
                   "verified publication time. Cancelled games are absent from the feed rather "
                   "than present with a null result. Closing moneylines in the source are "
                   "untimestamped and are deliberately not imported.",
    }
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({k: manifest[k] for k in
                      ("rows", "played", "unplayed", "ties", "neutral_site",
                       "dropped_missing_kickoff", "seasons")}, indent=2))
    print(f"Saved {len(games)} regular-season games to {out}")


if __name__ == "__main__":
    main()
