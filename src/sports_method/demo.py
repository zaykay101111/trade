from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from .io import write_json,new_dir

def make_demo(out,base_config,n=1200):
    out=new_dir(out);rng=np.random.default_rng(55)
    c=dict(base_config);c["mode"]="synthetic"
    start=pd.Timestamp("2020-01-01T20:00:00Z")
    boundaries=[int(n*x) for x in [.40,.55,.70,.85,1.]]
    for k,i in zip(["train_end","tune_end","calibration_end","validation_end","test_end"],boundaries):
        c[k]=(start+pd.Timedelta(days=i)).isoformat()
    c["bootstrap_repeats"]=200
    c["grid"]=[{"max_depth":2,"n_estimators":30,"learning_rate":.05},
               {"max_depth":3,"n_estimators":30,"learning_rate":.05}]
    strength=rng.normal(0,.6,10);games=[];results=[];odds=[]
    for i in range(n):
        home,away=rng.choice(10,2,replace=False)
        time=start+pd.Timedelta(days=i)
        decision=time-pd.Timedelta(hours=1)
        q=float(expit(.2+strength[home]-strength[away]))
        win=rng.random()<q
        hs=int(rng.integers(95,120));margin=int(rng.integers(1,22));aws=hs-margin if win else hs+margin
        game_id=f"demo_{i:05d}"
        games.append({"game_id":game_id,"home_id":str(home),"away_id":str(away),
                      "scheduled_at":time.isoformat(),"decision_at":decision.isoformat(),
                      "schedule_observed_at":(time-pd.Timedelta(days=2)).isoformat(),
                      "season_type":"regular","contract":c["contract"]})
        results.append({"game_id":game_id,"home_score":hs,"away_score":aws,
                        "available_at":(time+pd.Timedelta(hours=3)).isoformat()})
        for book in c["reference_books"]+c["execution_books"]:
            qp=float(np.clip(q+rng.normal(0,.008),.08,.92))
            odds.append({"game_id":game_id,"book":book,
                         "quote_at":(decision-pd.Timedelta(minutes=2)).isoformat(),
                         "available_at":(decision-pd.Timedelta(minutes=1)).isoformat(),
                         "home_odds":1/(qp*1.035),"away_odds":1/((1-qp)*1.035),"contract":c["contract"]})
    for name,rows in [("games",games),("results",results),("odds",odds)]:
        pd.DataFrame(rows).to_csv(out/(name+".csv"),index=False)
    write_json(out/"config.json",c)
    return out

