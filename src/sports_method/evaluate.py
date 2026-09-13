from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss,brier_score_loss
from .io import read_json,write_json,digest,now
from .model import predict,split_rows,verify_freeze,fit_calibration
from .policy import replay

def block_interval(values,times,days=7,repeats=2000,seed=42):
    values=np.asarray(values,float)
    if not len(values):
        return None
    t=pd.DatetimeIndex(pd.to_datetime(times,utc=True))
    labels=(t.asi8//(86400*10**9*days))
    groups=[values[labels==k] for k in np.unique(labels)]
    if len(groups)<10:
        return None
    rng=np.random.default_rng(seed)
    draws=[float(np.concatenate([groups[i] for i in rng.integers(len(groups),size=len(groups))]).mean()) for _ in range(repeats)]
    return [float(x) for x in np.quantile(draws,[.025,.975])]

def individual_loss(y,p):
    p=np.clip(np.asarray(p,float),1e-9,1-1e-9)
    return -(y*np.log(p)+(1-y)*np.log1p(-p))

def evaluate(run,dataset,split):
    run=Path(run);bundle=read_json(run/"bundle.json");c=bundle["config"]
    if digest(Path(dataset)/"features.csv")!=bundle["dataset_sha256"]:
        raise ValueError("Dataset differs from training manifest")
    out=run/split
    if out.exists():
        raise FileExistsError("Evaluation exists; read its PASTE_BACK.md instead of rerunning")
    if split=="test":
        verify_freeze(run)
        # Claim consumption before accessing test predictions; failures retain the claim.
        with (run/"TEST_CONSUMED.json").open("x") as f:
            import json
            json.dump({"started_at":now(),"dataset":bundle["dataset_sha256"]},f)
    out.mkdir()
    df=pd.read_csv(Path(dataset)/"features.csv",dtype={"game_id":str})
    part=split_rows(df,c,split)
    pred=predict(run,part)
    pred.to_csv(out/"predictions.csv",index=False)
    metrics={}
    baseline=individual_loss(pred.y.to_numpy(),pred.p_market_cal)
    for name in ["market","market_cal","logistic","residual"]:
        p=pred["p_"+name]
        metrics[name]={"log_loss":float(log_loss(pred.y,p)),
            "brier":float(brier_score_loss(pred.y,p)),
            "calibration_diagnostic":fit_calibration(p,pred.y.to_numpy())}
    delta=baseline-individual_loss(pred.y.to_numpy(),pred.p_residual)
    ci=block_interval(delta,pred.decision_at,c["block_days"],c["bootstrap_repeats"],c["seed"])
    ci28=block_interval(delta,pred.decision_at,28,c["bootstrap_repeats"],c["seed"])
    rel=float(delta.mean()/baseline.mean())
    bets,financial=replay(pred,"p_residual",c["policy"])
    bets.to_csv(out/"paper_bets.csv",index=False)
    delayed=[]
    for _,bet in bets.iterrows():
        original=pred[pred.game_id==bet.game_id].iloc[0]
        price=original.get(bet.side+"_delay5_odds",np.nan)
        if pd.notna(price):
            delayed.append({"clears_floor":bool(price>=bet.min_odds),
                            "return":float(price*bet.won-1-c["policy"]["cost_per_stake"])})
    usable=[x["return"] for x in delayed if x["clears_floor"]]
    delay_report={"original_bets":len(bets),"same_book_later_snapshot_observed":len(delayed),
                  "still_clears_price_floor":len(usable),
                  "flat_yield_if_taken_at_delayed_price":float(np.mean(usable)) if usable else None,
                  "qualification":"Missing later snapshots are unknown availability. Same contract/book; original forecasts fixed."}
    _,market_financial=replay(pred,"p_market_cal",c["policy"])
    _,worse=replay(pred,"p_residual",c["policy"],.99)
    yield_ci=block_interval(bets.return_per_stake,bets.decision_at,c["block_days"],c["bootstrap_repeats"],c["seed"]) if len(bets) else None
    selected_metrics={"n":len(bets),
        "brier":float(np.mean((bets.p-bets.won)**2)) if len(bets) else None,
        "log_loss":float(np.mean(individual_loss(bets.won.to_numpy(),bets.p))) if len(bets) else None}
    outlier=None
    if len(bets)>5:
        pnl=bets.stake*bets.return_per_stake
        keep=pnl.sort_values(ascending=False).index[5:]
        outlier={"remove_top_5_profit_bets_pnl":float(pnl.loc[keep].sum()),"remaining_bets":len(keep)}
    bins=[]
    for low in np.arange(0,1,.1):
        group=pred[(pred.p_residual>=low)&(pred.p_residual<low+.1)]
        if len(group):
            bins.append({"lower":round(float(low),1),"n":len(group),
                         "mean_p":float(group.p_residual.mean()),"observed":float(group.y.mean())})
    report={"schema_version":1,"created_at":now(),"split":split,"mode":bundle["mode"],
        "run":run.name,"dataset_sha256":bundle["dataset_sha256"],"code_sha256":bundle["code_sha256"],
        "n_games":len(pred),"start":pred.decision_at.min(),"end":pred.decision_at.max(),
        "metrics":metrics,"relative_log_loss_improvement":rel,
        "paired_log_loss_improvement_ci95":ci,"paired_ci95_28day_sensitivity":ci28,
        "reliability_bins":bins,"paper_policy":financial,"market_only_policy":market_financial,
        "flat_yield_ci95":yield_ci,"selected_probability_metrics":selected_metrics,
        "profit_odds_1pct_worse":worse,"outlier_sensitivity":outlier,
        "gate_forecast":bool(bundle["mode"]!="synthetic" and rel>=.0025 and ci is not None and ci[0]>0),
        "gate_economic_evidence":bool(bundle["mode"]!="synthetic" and yield_ci is not None and yield_ci[0]>0),
        "execution_evidence":"NOT MEASURED: displayed historical quotes; paper stakes only",
        "delayed_price_test":delay_report,
        "data_audit":read_json(Path(dataset)/"audit.json"),
        "limitations":["Synthetic mode never provides market evidence","Haircut is a fixed policy stress, not a confidence bound",
                      "Calibration diagnostic is fitted on this evaluation slice for diagnosis only, never used to change forecasts",
                      "Reported bootstrap intervals do not correct an undisclosed strategy search"],
        "versions":bundle["versions"]}
    write_json(out/"report.json",report)
    text="# PASTE BACK — "+split.upper()+"\n\n"
    text+="Copy this entire file into the chat.\n\n"
    text+="Status: "+bundle["mode"]+"; paper evaluation; no execution claim.\n\n"
    import json
    text+="```json\n"+json.dumps(report,indent=2)+"\n```\n"
    (out/"PASTE_BACK.md").write_text(text)
    return out
