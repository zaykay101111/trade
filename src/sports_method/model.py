import os
import platform
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.metrics import log_loss
import sklearn
import xgboost as xgb
from .data import FEATURES
from .io import read_json, write_json, digest, code_hash, now, new_dir

def logits(p):
    return logit(np.clip(np.asarray(p,float),1e-6,1-1e-6))

def fit_logistic(X,y,q, *, l2=.01):
    if not np.isfinite(l2) or l2 < 0:
        raise ValueError("L2 penalty must be finite and nonnegative")
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale<1e-8] = 1
    Z = np.column_stack([np.ones(len(X)),(X-mean)/scale])
    offset = logits(q)
    def objective(w):
        z = offset+Z@w
        loss = np.mean(np.logaddexp(0,z)-y*z)+l2*np.sum(w[1:]**2)
        grad = Z.T@(expit(z)-y)/len(y)
        grad[1:] += 2*l2*w[1:]
        return loss,grad
    fit = minimize(objective,np.zeros(Z.shape[1]),jac=True,method="L-BFGS-B")
    if not fit.success:
        raise RuntimeError("Logistic optimizer did not converge: "+fit.message)
    return {"mean":mean.tolist(),"scale":scale.tolist(),"coef":fit.x.tolist()}

def predict_logistic(model,X,q):
    Z = np.column_stack([np.ones(len(X)),(X-np.array(model["mean"]))/np.array(model["scale"])])
    return expit(logits(q)+Z@np.array(model["coef"]))

def fit_calibration(p,y):
    z = logits(p)
    def loss(v):
        a,b = v[0],np.exp(v[1])
        eta = a+b*z
        return np.mean(np.logaddexp(0,eta)-y*eta)+.001*np.sum(v**2)
    fit = minimize(loss,[0.,0.],bounds=[(-3,3),(-3,3)],method="L-BFGS-B")
    if not fit.success:
        raise RuntimeError("Calibration optimizer failed")
    return {"intercept":float(fit.x[0]),"slope":float(np.exp(fit.x[1]))}

def calibrate(p,c):
    return expit(c["intercept"]+c["slope"]*logits(p))

def split_rows(df,config,name):
    t = pd.to_datetime(df.decision_at,utc=True)
    ends = [pd.Timestamp(config[k]) for k in ["train_end","tune_end","calibration_end","validation_end","test_end"]]
    if sorted(ends)!=ends or len(set(ends))!=5:
        raise ValueError("Split boundaries must be strictly increasing")
    names = ["train","tune","calibration","validation","test"]
    i = names.index(name)
    mask = t<ends[i]
    if i:
        mask &= t>=ends[i-1]
    if name in ("train","tune","calibration"):
        available = pd.to_datetime(df.result_available_at,utc=True,errors="coerce")
        mask &= available<ends[i]
    part=df[mask].copy()
    if part.empty or part.y.isna().any() or len(part.y.unique())!=2:
        raise ValueError(f"{name}: needs settled games containing both classes")
    return part

def fit(dataset,config,out):
    out = new_dir(out)
    df=pd.read_csv(Path(dataset)/"features.csv",dtype={"game_id":str})
    audit=read_json(Path(dataset)/"audit.json")
    if digest(Path(dataset)/"features.csv")!=audit["features_sha256"]:
        raise ValueError("Features modified after audited build")
    if audit["config"] != config:
        raise ValueError("Build and training configurations differ; rebuild dataset")
    parts={k:split_rows(df,config,k) for k in ("train","tune","calibration")}
    if min(map(len,parts.values()))<30:
        raise ValueError("At least 30 games per fitting segment required even for smoke tests")
    train,tune,cal=(parts[k] for k in ("train","tune","calibration"))
    trials=[]
    threads=int(os.environ.get("SLURM_CPUS_PER_TASK",config["threads"]))
    for i,params in enumerate(config["grid"]):
        learner=xgb.XGBClassifier(**params,objective="binary:logistic",eval_metric="logloss",
            tree_method="hist",n_jobs=threads,random_state=config["seed"],
            reg_lambda=10,min_child_weight=20,base_score=.5)
        learner.fit(train[FEATURES],train.y,base_margin=logits(train.q),
            eval_set=[(tune[FEATURES],tune.y)],base_margin_eval_set=[logits(tune.q)],verbose=False)
        p=learner.predict_proba(tune[FEATURES],base_margin=logits(tune.q))[:,1]
        trials.append({"trial":i,"params":params,"tune_log_loss":float(log_loss(tune.y,p)),
                       "tune_curve":learner.evals_result()["validation_0"]["logloss"]})
        write_json(out/"progress.json",{"stage":"tuning","completed":i+1,"total":len(config["grid"]),"latest_loss":trials[-1]["tune_log_loss"]})
    best=min(trials,key=lambda x:x["tune_log_loss"])
    combined=pd.concat([train,tune])
    learner=xgb.XGBClassifier(**best["params"],objective="binary:logistic",eval_metric="logloss",
        tree_method="hist",n_jobs=threads,random_state=config["seed"],
        reg_lambda=10,min_child_weight=20,base_score=.5)
    learner.fit(combined[FEATURES],combined.y,base_margin=logits(combined.q))
    learner.save_model(out/"residual.json")
    logistic=fit_logistic(combined[FEATURES].to_numpy(),combined.y.to_numpy(),combined.q)
    raw_res=learner.predict_proba(cal[FEATURES],base_margin=logits(cal.q))[:,1]
    raw_log=predict_logistic(logistic,cal[FEATURES].to_numpy(),cal.q)
    calibrators={name:fit_calibration(p,cal.y.to_numpy()) for name,p in
        [("market",cal.q),("logistic",raw_log),("residual",raw_res)]}
    write_json(out/"bundle.json",{"version":1,"created_at":now(),"mode":config["mode"],
        "config":config,"features":FEATURES,"logistic":logistic,"calibrators":calibrators,
        "split_counts":{k:len(v) for k,v in parts.items()},"selected_params":best["params"],
        "dataset_sha256":digest(Path(dataset)/"features.csv"),"code_sha256":code_hash(),
        "versions":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,
                    "scipy":scipy.__version__,"sklearn":sklearn.__version__,"xgboost":xgb.__version__}})
    write_json(out/"trials.json",trials)
    write_json(out/"progress.json",{"stage":"complete","model":"residual","trials":len(trials)})
    return out

def predict(run,df):
    run=Path(run);b=read_json(run/"bundle.json")
    if b["features"]!=FEATURES:
        raise ValueError("Feature schema mismatch")
    model=xgb.XGBClassifier()
    model.load_model(run/"residual.json")
    p=model.predict_proba(df[FEATURES],base_margin=logits(df.q))[:,1]
    lp=predict_logistic(b["logistic"],df[FEATURES].to_numpy(),df.q)
    out=df.copy()
    out["p_market"]=out.q
    out["p_market_cal"]=calibrate(out.q,b["calibrators"]["market"])
    out["p_logistic"]=calibrate(lp,b["calibrators"]["logistic"])
    out["p_residual"]=calibrate(p,b["calibrators"]["residual"])
    return out

def freeze(run):
    run=Path(run)
    if (run/"freeze.json").exists():
        raise FileExistsError("Already frozen")
    bundle=read_json(run/"bundle.json")
    if bundle["code_sha256"]!=code_hash():
        raise ValueError("Source changed since training; train a new run")
    write_json(run/"freeze.json",{"frozen_at":now(),"code_sha256":code_hash(),
        "bundle_sha256":digest(run/"bundle.json"),"model_sha256":digest(run/"residual.json"),
        "policy":bundle["config"]["policy"],"note":"Local tamper detection, not an independent preregistration service."})

def verify_freeze(run):
    run=Path(run);f=read_json(run/"freeze.json")
    for key,path in [("bundle_sha256","bundle.json"),("model_sha256","residual.json")]:
        if f[key]!=digest(run/path):
            raise ValueError("Frozen model bundle was modified")
    if f["code_sha256"]!=code_hash():
        raise ValueError("Code differs from frozen implementation")
