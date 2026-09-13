import math
import numpy as np
import pandas as pd

def candidate(row,p,policy):
    choices=[]
    for side,prob in [("home",p),("away",1-p)]:
        risk=max(0.,prob-policy["probability_haircut"])
        d=float(row[side+"_odds"])
        c=policy["cost_per_stake"]
        ev=risk*d-1-c
        minimum=(1+c+policy["min_ev"])/risk if risk else None
        a,ell=d-1-c,1+c
        kelly=max(0.,ev/(a*ell)) if a>0 else 0.
        choices.append({"side":side,"p":float(prob),"p_risk":risk,"odds":d,"book":row[side+"_book"],
            "ev":ev,"min_odds":minimum,"kelly":kelly})
    selected=max(choices,key=lambda x:x["ev"])
    selected["qualifies"]=selected["ev"]>=policy["min_ev"] and selected["kelly"]>0
    return selected

def replay(predictions,column,policy,odds_multiplier=1.):
    cash=float(policy["bankroll"])
    open_bets=[];bets=[];daily={};peak=cash;drawdown=0.
    def equity():
        return cash+sum(b["stake"] for b in open_bets)
    for _,original in predictions.sort_values(["decision_at","game_id"]).iterrows():
        time=pd.Timestamp(original.decision_at)
        due=[b for b in open_bets if b["settle"]<=time]
        for b in due:
            cash+=b["stake"]*b["odds"]*b["won"]
            open_bets.remove(b)
            peak=max(peak,equity())
            drawdown=max(drawdown,1-equity()/peak)
        row=original.copy()
        for side in ("home","away"):
            row[side+"_odds"]=1+(float(row[side+"_odds"])-1)*odds_multiplier
        choice=candidate(row,float(row[column]),policy)
        if not choice["qualifies"]:
            continue
        eq=equity();day=time.date().isoformat()
        open_stake=sum(b["stake"] for b in open_bets)
        wanted=eq*min(policy["kelly_fraction"]*choice["kelly"],policy["max_game_fraction"])
        allowed=min(wanted,eq*policy["max_open_fraction"]-open_stake,
                    eq*policy["max_daily_fraction"]-daily.get(day,0),cash/(1+policy["cost_per_stake"]))
        inc=policy["stake_increment"]
        stake=math.floor(max(0.,allowed)/inc+1e-9)*inc
        if stake<=0:
            continue
        won=int(row.y if choice["side"]=="home" else 1-row.y)
        b={**choice,"game_id":row.game_id,"decision_at":row.decision_at,
           "settle":pd.Timestamp(row.result_available_at),"stake":stake,"won":won,
           "return_per_stake":choice["odds"]*won-1-policy["cost_per_stake"]}
        if b["settle"]<=time:
            raise ValueError("Result timestamp precedes decision")
        cash-=stake*(1+policy["cost_per_stake"])
        daily[day]=daily.get(day,0)+stake
        open_bets.append(b);bets.append(b)
        peak=max(peak,equity());drawdown=max(drawdown,1-equity()/peak)
    for b in sorted(open_bets.copy(),key=lambda x:x["settle"]):
        cash+=b["stake"]*b["odds"]*b["won"];open_bets.remove(b)
        peak=max(peak,equity());drawdown=max(drawdown,1-equity()/peak)
    frame=pd.DataFrame(bets)
    turnover=sum(b["stake"] for b in bets)
    pnl=cash-policy["bankroll"]
    return frame,{"bets":len(bets),"turnover":turnover,"pnl":pnl,
        "flat_yield":float(np.mean([b["return_per_stake"] for b in bets])) if bets else None,
        "weighted_yield":pnl/turnover if turnover else None,
        "bankroll_return":pnl/policy["bankroll"],"max_drawdown":drawdown}

