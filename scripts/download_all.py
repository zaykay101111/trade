"""Orchestrate schedule, results and odds planning. Odds downloads remain capped/dry-run by default."""
import argparse,json,subprocess,sys
from pathlib import Path
def run(cmd):
    print("+"," ".join(map(str,cmd)),flush=True);subprocess.run(cmd,check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("--seasons",required=True);p.add_argument("--out",required=True);p.add_argument("--odds-max-requests",type=int,default=0);p.add_argument("--execute-odds",action="store_true");a=p.parse_args();root=Path(a.out)
    if root.exists():raise FileExistsError(root)
    root.mkdir(parents=True);py=sys.executable
    run([py,"scripts/download_schedule.py","--seasons",a.seasons,"--out",str(root/"schedule")])
    run([py,"scripts/download_nba.py","--seasons",a.seasons,"--out",str(root/"nba-team-games.csv")])
    run(["sports","import-nba-results","--raw",str(root/"nba-team-games.csv"),"--games",str(root/"schedule/games.csv"),"--out",str(root/"results.csv")])
    run(["sports","plan-odds","--games",str(root/"schedule/games.csv"),"--out",str(root/"odds-plan.json")])
    if a.execute_odds:
        if a.odds_max_requests<=0:raise ValueError("--execute-odds requires --odds-max-requests > 0")
        run(["sports","fetch-odds","--plan",str(root/"odds-plan.json"),"--out",str(root/"odds-raw"),"--execute","--max-requests",str(a.odds_max_requests)])
    print(json.dumps({"schedule":str(root/"schedule"),"results":str(root/"results.csv"),"odds_plan":str(root/"odds-plan.json"),"next":"map event IDs then normalize odds"},indent=2))
if __name__=="__main__":main()

