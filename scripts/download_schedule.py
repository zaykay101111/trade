"""Download NBA schedule records and create canonical games.csv.

Uses nba_api ScheduleLeagueV2. schedule_observed_at is a declared 48-hour
reconstruction assumption; the endpoint does not provide full historical
revision history.
"""
import argparse, json, time
from pathlib import Path
import pandas as pd

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seasons",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--observed-lag-hours",type=float,default=48)
    parser.add_argument("--include-postponed",action="store_true")
    a=parser.parse_args(); out=Path(a.out)
    if out.exists() and (out/"games.csv").exists():
        raise FileExistsError(f"Output already has games.csv: {out}; choose a new directory")
    out.mkdir(parents=True, exist_ok=True); (out/"raw").mkdir(exist_ok=True)
    try:
        from nba_api.stats.endpoints.scheduleleaguev2 import ScheduleLeagueV2
    except ImportError as exc:
        raise SystemExit("Install with: python -m pip install -e '.[nba]'") from exc
    rows=[]
    for season in [x.strip() for x in a.seasons.split(",") if x.strip()]:
        raw_path=out/"raw"/f"schedule-{season}.json"
        if raw_path.exists():
            print(f"Reusing saved NBA schedule {season}",flush=True)
            frame=pd.read_json(raw_path)
        else:
            print(f"Downloading NBA schedule {season}",flush=True)
            ep=ScheduleLeagueV2(season=season,timeout=60)
            frame=ep.season_games.get_data_frame()
            frame.to_json(raw_path,orient="records",date_format="iso")
        for _,r in frame.iterrows():
            gid=str(r.get("gameId","")).zfill(10)
            postponed=str(r.get("postponedStatus","") or "")
            # NBA IDs beginning 002 are regular season; 001 is preseason.
            if not gid or gid=="0000000000" or not gid.startswith("002") or (postponed not in ("","N","None") and not a.include_postponed): continue
            status=str(r.get("gameStatusText","")).lower()
            if any(x in status for x in ("preseason","all-star")): continue
            scheduled=pd.Timestamp(r["gameDateTimeUTC"],tz="UTC")
            rows.append({"game_id":gid,"home_id":str(int(r["homeTeam_teamId"])),
                "away_id":str(int(r["awayTeam_teamId"])),
                "home_name":str(r["homeTeam_teamName"]),"away_name":str(r["awayTeam_teamName"]),
                "scheduled_at":scheduled.isoformat(),
                "schedule_observed_at":(scheduled-pd.Timedelta(hours=a.observed_lag_hours)).isoformat(),
                "decision_at":(scheduled-pd.Timedelta(minutes=60)).isoformat(),
                "season_type":"regular","contract":"nba_regular_fullgame_moneyline_ot",
                "is_neutral":bool(r.get("isNeutral",False)),"source_status":str(r.get("gameStatusText",""))})
        time.sleep(1)
    games=pd.DataFrame(rows).drop_duplicates("game_id")
    if games.empty: raise RuntimeError("Schedule endpoint returned no games")
    games.to_csv(out/"games.csv",index=False)
    (out/"manifest.json").write_text(json.dumps({"source":"nba_api ScheduleLeagueV2",
        "seasons":a.seasons.split(","),"rows":len(games),
        "observed_lag_hours":a.observed_lag_hours,
        "warning":"schedule_observed_at is reconstructed, not a provider revision timestamp"},indent=2)+"\n")
    print(f"Saved {len(games)} games to {out/'games.csv'}")
if __name__=="__main__": main()
