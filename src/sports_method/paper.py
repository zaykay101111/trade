"""Prospective paper ledger with transactionally enforced exposure and duplicate checks."""
import json
import math
import sqlite3
from pathlib import Path
import pandas as pd
from .io import read_json,digest,write_json,now
from .model import predict,verify_freeze
from .policy import candidate

def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS decisions (game_id TEXT PRIMARY KEY, issued_at TEXT NOT NULL, payload TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, game_id TEXT NOT NULL, checked_at TEXT NOT NULL, price REAL, available INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS settlements (game_id TEXT PRIMARY KEY, settled_at TEXT NOT NULL, outcome TEXT NOT NULL, pnl REAL NOT NULL)")
    db.commit()
    return db

def issue(run,dataset,ledger):
    verify_freeze(run)
    bundle=read_json(Path(run)/"bundle.json")
    if bundle["mode"]=="synthetic":raise ValueError("Synthetic bundle cannot issue prospective decisions")
    audit=read_json(Path(dataset)/"audit.json")
    if audit["mode"]!="prospective":
        raise ValueError("Paper issuing requires prospective timestamp provenance")
    for key in ["contract","cutoff_minutes","reference_books","execution_books","rolling_games","min_history","max_quote_age_minutes"]:
        if audit["config"][key]!=bundle["config"][key]:
            raise ValueError("Prospective data feature contract differs from bundle")
    if digest(Path(dataset)/"features.csv")!=audit["features_sha256"]:
        raise ValueError("Prospective feature file modified since build")
    df=pd.read_csv(Path(dataset)/"features.csv",dtype={"game_id":str})
    t=pd.Timestamp(now());decision=pd.to_datetime(df.decision_at,utc=True)
    df=df[(decision<=t)&(decision>=t-pd.Timedelta(minutes=10))]
    if df.empty:return {"issued":0,"reason":"No decisions in the current ten-minute window"}
    pred=predict(run,df)
    policy=bundle["config"]["policy"]
    db=connect(ledger)
    with db:
        db.execute("BEGIN IMMEDIATE")
        signature=digest(Path(run)/"bundle.json")
        existing=db.execute("SELECT value FROM meta WHERE key='bundle'").fetchone()
        if existing and existing[0]!=signature:
            raise ValueError("Use a separate ledger for a new model release")
        db.execute("INSERT OR IGNORE INTO meta VALUES ('bundle',?)",(signature,))
        db.execute("INSERT OR IGNORE INTO meta VALUES ('bankroll',?)",(str(policy["bankroll"]),))
        pnl=db.execute("SELECT COALESCE(SUM(pnl),0) FROM settlements").fetchone()[0]
        eq=policy["bankroll"]+pnl
        issued=0
        for _,row in pred.sort_values(["decision_at","game_id"]).iterrows():
            if db.execute("SELECT 1 FROM decisions WHERE game_id=?",(row.game_id,)).fetchone():continue
            open_rows=db.execute("SELECT payload FROM decisions WHERE game_id NOT IN (SELECT game_id FROM settlements)").fetchall()
            open_stake=sum(json.loads(x[0])["stake"] for x in open_rows)
            today=db.execute("SELECT payload FROM decisions WHERE substr(issued_at,1,10)=?",(t.date().isoformat(),)).fetchall()
            day_stake=sum(json.loads(x[0])["stake"] for x in today)
            x=candidate(row,float(row.p_residual),policy)
            stake=0.
            if x["qualifies"] and eq>0:
                allowed=min(eq*min(policy["kelly_fraction"]*x["kelly"],policy["max_game_fraction"]),
                    eq*policy["max_open_fraction"]-open_stake,eq*policy["max_daily_fraction"]-day_stake,
                    eq/(1+policy["cost_per_stake"])-open_stake)
                stake=math.floor(max(0.,allowed)/policy["stake_increment"])*policy["stake_increment"]
            payload={**x,"stake":stake,"decision_at":row.decision_at,"scheduled_at":row.scheduled_at,
                     "quote_at":row[x["side"]+"_quote_at"],"cost_per_stake":policy["cost_per_stake"],
                     "dataset_sha256":digest(Path(dataset)/"features.csv"),"bundle_sha256":signature,
                     "expiry":min(pd.Timestamp(row.decision_at)+pd.Timedelta(minutes=10),
                                  pd.Timestamp(row[x["side"]+"_quote_at"])+pd.Timedelta(minutes=policy.get("live_quote_age_minutes",10))).isoformat(),
                     "status":"conditional_paper" if stake else "no_bet"}
            if pd.Timestamp(payload["expiry"])<t:
                payload["stake"]=0.;payload["status"]="expired_quote"
            db.execute("INSERT INTO decisions VALUES (?,?,?)",(row.game_id,t.isoformat(),json.dumps(payload)))
            issued+=1
    db.close()
    return {"issued":issued,"ledger":str(ledger),"mode":"paper_only"}

def record_check(ledger,game,price,available):
    if price is not None and (not math.isfinite(price) or price<=1):raise ValueError("Invalid checked price")
    db=connect(ledger)
    with db:
        row=db.execute("SELECT payload FROM decisions WHERE game_id=?",(game,)).fetchone()
        if not row:raise ValueError("Unknown decision")
        if available and price is None:raise ValueError("Available check needs --price")
        db.execute("INSERT INTO checks(game_id,checked_at,price,available) VALUES (?,?,?,?)",(game,now(),price,int(available)))
    db.close()

def settle(ledger,game,outcome):
    if outcome not in ["win","loss","void"]:raise ValueError("Invalid settlement")
    db=connect(ledger)
    with db:
        row=db.execute("SELECT payload FROM decisions WHERE game_id=?",(game,)).fetchone()
        if not row:raise ValueError("Unknown decision")
        p=json.loads(row[0])
        if pd.Timestamp(now())<=pd.Timestamp(p["scheduled_at"]):
            raise ValueError("Cannot settle before scheduled start")
        pnl=0. if outcome=="void" else p["stake"]*(p["odds"]*(outcome=="win")-1-p["cost_per_stake"])
        db.execute("INSERT INTO settlements VALUES (?,?,?,?)",(game,now(),outcome,pnl))
    db.close()

def monitor(ledger,out):
    from .evaluate import block_interval
    db=connect(ledger)
    rows=db.execute("SELECT d.game_id,d.issued_at,d.payload,s.outcome,s.pnl FROM decisions d LEFT JOIN settlements s USING(game_id)").fetchall()
    opportunities=[];settled=[];price_results=[]
    for game,issued,payload,outcome,pnl in rows:
        p=json.loads(payload)
        if p["stake"]<=0:continue
        opportunities.append((game,issued,p))
        checks=db.execute("SELECT checked_at,price,available FROM checks WHERE game_id=? ORDER BY checked_at,id",(game,)).fetchall()
        # Count the first check; preserve late checks as failures rather than dropping them.
        if checks:
            at,price,available=checks[0]
            price_results.append(bool(available and price>=p["min_odds"] and pd.Timestamp(at)<=pd.Timestamp(p["expiry"])))
        if outcome is not None:
            settled.append({"issued_at":issued,"pnl":pnl,"stake":p["stake"],"outcome":outcome,
                            "p":p["p"],"return":pnl/p["stake"]})
    db.close()
    turnover=sum(x["stake"] for x in settled);pnl=sum(x["pnl"] for x in settled)
    nonvoid=[x for x in settled if x["outcome"]!="void"]
    span=(pd.Timestamp(now())-min(pd.Timestamp(x[1]) for x in opportunities)).total_seconds()/86400 if opportunities else 0.
    report={"mode":"prospective_paper_only","issued_decisions":len(rows),"paper_candidates":len(opportunities),
        "settled":len(settled),"unsettled":len(opportunities)-len(settled),"observed_days":span,
        "operations_sample_checkpoint":bool(len(settled)>=300 and span>=90),
        "turnover":turnover,"paper_pnl":pnl,
        "yield":pnl/turnover if turnover else None,
        "flat_yield_ci95":block_interval([x["return"] for x in settled],[x["issued_at"] for x in settled]),
        "checked_candidates":len(price_results),"unchecked_candidates":len(opportunities)-len(price_results),
        "check_coverage":len(price_results)/len(opportunities) if opportunities else None,
        "price_available_rate_among_checked":sum(price_results)/len(price_results) if price_results else None,
        "selected_brier":sum((x["p"]-(x["outcome"]=="win"))**2 for x in nonvoid)/len(nonvoid) if nonvoid else None,
        "execution_claim":"No accepted real bets. P&L assumes original displayed price and must be read with quote availability.",
        "instruction":"Review data integrity daily, operations weekly, performance on predeclared monthly dates. Do not retune from this report."}
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    write_json(dest/"monitor.json",report)
    (dest/"PASTE_BACK.md").write_text("# PROSPECTIVE PAPER MONITOR\n\n```json\n"+json.dumps(report,indent=2)+"\n```\n")
    return report
