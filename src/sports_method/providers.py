"""Explicit, bounded downloads and adapters. Never fetch on import."""
import json
import os
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
import pandas as pd
from .io import read_json,write_json,now,digest

def plan_odds(games_file,out):
    g=pd.read_csv(games_file)
    times=set()
    for t in pd.to_datetime(g.decision_at,utc=True):
        # Both decision and five-minute execution-delay snapshots.
        times.update([t.isoformat(),(t+pd.Timedelta(minutes=5)).isoformat()])
    plan={"provider":"the-odds-api.com","market":"h2h","regions":"us,uk,eu",
          "timestamps":sorted(times),"requests":len(times),
          "estimated_credits_upper_bound":len(times)*10*3,
          "note":"One market, three regions. Confirm provider charging/coverage before executing. No request made."}
    write_json(out,plan);return plan

def fetch_odds(plan_path,out,max_requests,execute=False):
    plan=read_json(plan_path)
    if not execute:
        return {"dry_run":True,"requests":len(plan["timestamps"]),"estimated_credits_upper_bound":plan["estimated_credits_upper_bound"]}
    key=os.environ.get("ODDS_API_KEY")
    if not key:
        raise ValueError("Set ODDS_API_KEY in the environment; never paste it into reports")
    if max_requests<=0:
        raise ValueError("Set a positive --max-requests")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    done=0
    for stamp in plan["timestamps"]:
        filename=stamp.replace(":","").replace("+","_")+".json"
        dest=out/filename
        if dest.exists():
            continue
        if done>=max_requests:
            break
        params={"apiKey":key,"regions":plan["regions"],"markets":"h2h","oddsFormat":"decimal","date":stamp}
        url="https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds?"+urlencode(params)
        try:
            with urlopen(Request(url,headers={"Accept":"application/json"}),timeout=45) as response:
                body=json.load(response)
                quota={k:response.headers.get(k) for k in ["x-requests-remaining","x-requests-used","x-requests-last"]}
        except (HTTPError,URLError) as exc:
            raise RuntimeError("Odds download failed; HTTP status "+str(getattr(exc,"code","network"))+"; request URL suppressed to protect key") from None
        write_json(dest,{"retrieved_at":now(),"requested_at":stamp,"quota":quota,"body":body})
        done+=1
    return {"downloaded":done,"folder":str(out)}

def normalize_odds(raw,mapping,out,contract):
    m=pd.read_csv(mapping,dtype=str)
    needed={"provider_event_id","game_id","home_name","away_name"}
    if not needed<=set(m) or m.provider_event_id.duplicated().any():
        raise ValueError("event_map needs unique provider_event_id, game_id, home_name, away_name")
    lookup=m.set_index("provider_event_id").to_dict("index")
    rows=[];unmapped=set()
    for path in sorted(Path(raw).glob("*.json")):
        wrapper=read_json(path);body=wrapper["body"]
        stamp=body["timestamp"]
        for event in body["data"]:
            if event["id"] not in lookup:
                unmapped.add(event["id"]);continue
            match=lookup[event["id"]]
            if (event["home_team"],event["away_team"])!=(match["home_name"],match["away_name"]):
                raise ValueError("Mapped event team names changed; audit mapping")
            for book in event["bookmakers"]:
                for market in book["markets"]:
                    if market["key"]!="h2h":
                        continue
                    outcomes={x["name"]:x["price"] for x in market["outcomes"]}
                    if set(outcomes)!={match["home_name"],match["away_name"]}:
                        continue
                    quote=market.get("last_update",book["last_update"])
                    if pd.Timestamp(quote)>pd.Timestamp(stamp):
                        continue
                    rows.append({"game_id":match["game_id"],"book":book["key"],
                        "quote_at":quote,"available_at":stamp,"home_odds":outcomes[match["home_name"]],
                        "away_odds":outcomes[match["away_name"]],"contract":contract,
                        "raw_sha256":digest(path),"retrieved_at":wrapper["retrieved_at"]})
    if not rows:
        raise ValueError("No mapped paired odds found")
    dest=Path(out)
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).drop_duplicates(["game_id","book","quote_at","available_at","contract"]).to_csv(dest,index=False)
    return {"rows":len(rows),"unmapped_event_ids":sorted(unmapped),
            "mode":"historical_reconstructed","warning":"Provider snapshot time is asserted archive availability, not original local ingestion."}

def import_nba_results(raw_csv,games_file,out):
    raw=pd.read_csv(raw_csv,dtype={"GAME_ID":str,"TEAM_ID":str})
    games=pd.read_csv(games_file,dtype={"game_id":str,"home_id":str,"away_id":str})
    # canonical game_id must be NBA GAME_ID for this adapter.
    rows=[]
    for game in games.itertuples():
        h=raw[(raw.GAME_ID==game.game_id)&(raw.TEAM_ID==game.home_id)]
        a=raw[(raw.GAME_ID==game.game_id)&(raw.TEAM_ID==game.away_id)]
        if len(h)!=1 or len(a)!=1:
            raise ValueError(f"Need exactly two mapped team results for {game.game_id}")
        rows.append({"game_id":game.game_id,"home_score":int(h.iloc[0].PTS),
                     "away_score":int(a.iloc[0].PTS),
                     "available_at":(pd.Timestamp(game.scheduled_at)+pd.Timedelta(hours=24)).isoformat()})
    dest=Path(out)
    if dest.exists():raise FileExistsError(dest)
    pd.DataFrame(rows).to_csv(dest,index=False)
    return {"games":len(rows),"availability":"ASSUMED +24h after scheduled start; verify on delayed/suspended games; research only"}

