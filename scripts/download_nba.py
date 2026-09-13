"""Optional NBA.com team-log downloader. Run explicitly; raw data only."""
import argparse
from pathlib import Path
import time
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();dest=Path(a.out)
    if dest.exists():raise FileExistsError(dest)
    from nba_api.stats.endpoints import leaguegamefinder
    frames=[]
    for season in a.seasons.split(","):
        print("Downloading regular-season team logs:",season,flush=True)
        request=leaguegamefinder.LeagueGameFinder(season_nullable=season,
            league_id_nullable="00",season_type_nullable="Regular Season",
            player_or_team_abbreviation="T",timeout=60)
        frame=request.get_data_frames()[0]
        frame["requested_season"]=season
        frames.append(frame)
        time.sleep(1)
    dest.parent.mkdir(parents=True,exist_ok=True)
    pd.concat(frames).to_csv(dest,index=False)
    print("Saved",dest,"— final stats are not historical injury/status revisions.")
if __name__=="__main__":main()

