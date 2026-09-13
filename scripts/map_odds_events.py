"""Map Odds API event IDs to canonical NBA game IDs using names and UTC times."""
import argparse,json,re
from pathlib import Path
import pandas as pd

def norm(s):
    return re.sub(r"[^a-z0-9]","",str(s).lower().replace("la ","losangeles"))

def main():
    p=argparse.ArgumentParser();p.add_argument("--raw",required=True);p.add_argument("--games",required=True);p.add_argument("--out",required=True);p.add_argument("--tolerance-minutes",type=float,default=15);a=p.parse_args()
    dest=Path(a.out)
    if dest.exists():raise FileExistsError(dest)
    games=pd.read_csv(a.games,dtype=str); needed={"game_id","home_name","away_name","scheduled_at"}
    if not needed<=set(games):raise ValueError("games.csv needs names/scheduled_at; rerun download_schedule.py")
    games["scheduled_at"]=pd.to_datetime(games.scheduled_at,utc=True); rows=[];unmatched=[];seen=set()
    for path in sorted(Path(a.raw).glob("*.json")):
        body=json.loads(path.read_text())["body"]
        for e in body.get("data",[]):
            h,a2=norm(e.get("home_team")),norm(e.get("away_team")); t=pd.Timestamp(e["commence_time"],tz="UTC")
            c=games[(games.home_name.map(norm)==h)&(games.away_name.map(norm)==a2)]
            if len(c):
                dist=(c.scheduled_at-t).abs().dt.total_seconds()/60; i=dist.idxmin()
                if dist.loc[i]<=a.tolerance_minutes and e["id"] not in seen:
                    rows.append({"provider_event_id":e["id"],"game_id":str(c.loc[i,"game_id"]),
                        "home_name":c.loc[i,"home_name"],"away_name":c.loc[i,"away_name"],
                        "provider_home_name":e["home_team"],"provider_away_name":e["away_team"],
                        "commence_time":e["commence_time"],"match_distance_minutes":float(dist.loc[i])});seen.add(e["id"]);continue
            unmatched.append({"provider_event_id":e.get("id"),"home":e.get("home_team"),"away":e.get("away_team"),"commence_time":e.get("commence_time"),"raw_file":str(path)})
    if not rows:raise RuntimeError("No mappings; inspect unmatched.csv and source coverage")
    dest.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(dest,index=False);pd.DataFrame(unmatched).to_csv(dest.with_name("unmatched.csv"),index=False)
    print(f"Mapped {len(rows)} events; unmatched {len(unmatched)}. Review unmatched.csv.")
if __name__=="__main__":main()

