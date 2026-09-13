"""Canonical CSV validation and time-aware feature construction."""
from pathlib import Path
import numpy as np
import pandas as pd
from .io import digest, write_json

FEATURES = ["margin_diff", "points_for_diff", "points_against_diff",
            "rest_diff", "home_back_to_back", "away_back_to_back",
            "home_history", "away_history", "home_win_rate", "away_win_rate",
            "reference_dispersion", "reference_age_minutes"]

COLUMNS = {
 "games": ["game_id","home_id","away_id","scheduled_at","schedule_observed_at","decision_at","season_type","contract"],
 "results": ["game_id","home_score","away_score","available_at"],
 "odds": ["game_id","book","quote_at","available_at","home_odds","away_odds","contract"]
}
TIMES = {"games":["scheduled_at","schedule_observed_at","decision_at"],
         "results":["available_at"], "odds":["quote_at","available_at"]}

def utc(series):
    if series.isna().any() or not series.astype(str).str.contains(r"(?:Z|[+-][0-9]{2}:?[0-9]{2})$", regex=True).all():
        raise ValueError("All timestamps require explicit UTC offset; missing/date-only values rejected")
    return pd.to_datetime(series, utc=True, errors="raise")

def load_tables(folder, config):
    if config["mode"] not in ("historical_reconstructed","prospective","synthetic"):
        raise ValueError("Unknown provenance mode")
    policy=config["policy"]
    if not (0 < policy["bankroll"] and 0 < policy["stake_increment"] and
            0 <= policy["probability_haircut"] < .5 and 0 <= policy["cost_per_stake"] < 1 and
            0 <= policy["min_ev"] and 0 < policy["kelly_fraction"] <= 1):
        raise ValueError("Invalid policy arithmetic parameters")
    if not all(0 < policy[k] <= 1 for k in ("max_game_fraction","max_open_fraction","max_daily_fraction")):
        raise ValueError("Invalid exposure fractions")
    folder = Path(folder)
    tables = {}
    for name, columns in COLUMNS.items():
        df = pd.read_csv(folder / (name + ".csv"), dtype={"game_id":str,"home_id":str,"away_id":str})
        missing = set(columns) - set(df)
        if missing:
            raise ValueError(f"{name}: missing columns {sorted(missing)}")
        if df[columns].isna().any().any():
            raise ValueError(f"{name}: null required field")
        for col in TIMES[name]:
            df[col] = utc(df[col])
        tables[name] = df
    g, r, o = (tables[k] for k in ("games","results","odds"))
    if g.empty or g.game_id.duplicated().any() or r.game_id.duplicated().any():
        raise ValueError("Empty games or duplicate game/result IDs")
    if (g.home_id == g.away_id).any():
        raise ValueError("Identical home and away team")
    if not set(r.game_id) <= set(g.game_id) or not set(o.game_id) <= set(g.game_id):
        raise ValueError("Unmapped game IDs")
    if o.duplicated(["game_id","book","quote_at","available_at","contract"]).any():
        raise ValueError("Duplicate odds revision keys")
    if not np.isfinite(o[["home_odds","away_odds"]].to_numpy(float)).all() or (o[["home_odds","away_odds"]] <= 1).any().any():
        raise ValueError("Decimal odds must be finite and greater than one")
    if not np.isfinite(r[["home_score","away_score"]].to_numpy(float)).all() or (r[["home_score","away_score"]] < 0).any().any():
        raise ValueError("Invalid result scores")
    if ((r.home_score % 1 != 0) | (r.away_score % 1 != 0) | (r.home_score == r.away_score)).any():
        raise ValueError("NBA final scores require unequal nonnegative integers")
    if (g.schedule_observed_at > g.decision_at).any():
        raise ValueError("Schedule revision was unavailable at the decision time")
    if not ((g.scheduled_at-g.decision_at).dt.total_seconds() == config["cutoff_minutes"]*60).all():
        raise ValueError("Cutoff differs from the declared policy")
    if (o.quote_at > o.available_at).any():
        raise ValueError("Quote cannot be available before its source timestamp")
    joined = r.merge(g[["game_id","scheduled_at"]], on="game_id")
    if (joined.available_at <= joined.scheduled_at).any():
        raise ValueError("Final result available before scheduled game")
    if set(config["reference_books"]) & set(config["execution_books"]):
        raise ValueError("Reference and execution books must be disjoint")
    if config["min_reference_books"] < 3:
        raise ValueError("This release requires at least three reference books")
    for name in ["reference_books","execution_books"]:
        if len(set(config[name])) != len(config[name]):
            raise ValueError("Duplicate configured books")
    return tables

def latest_quotes(odds, game_id, cutoff, config):
    rows = odds[(odds.game_id == game_id) &
                (odds.quote_at <= cutoff) & (odds.available_at <= cutoff) &
                (odds.contract == config["contract"])].copy()
    rows = rows[(cutoff-rows.quote_at).dt.total_seconds() <= config["max_quote_age_minutes"]*60]
    return rows.sort_values(["available_at","quote_at"]).drop_duplicates("book",keep="last")

def build(folder, config, out):
    tables = load_tables(folder, config)
    g,r,o = (tables[k] for k in ("games","results","odds"))
    history = g.merge(r,on="game_id",how="inner").sort_values("available_at")
    records, excluded = [], []
    for game in g.sort_values(["decision_at","game_id"]).itertuples():
        reason = None
        if game.season_type != "regular" or game.contract != config["contract"]:
            reason = "outside_contract"
        quotes = latest_quotes(o, game.game_id, game.decision_at, config)
        refs = quotes[quotes.book.isin(config["reference_books"])]
        offers = quotes[quotes.book.isin(config["execution_books"])]
        if reason is None and len(refs) < config["min_reference_books"]:
            reason = "missing_fresh_reference_books"
        if reason is None and offers.empty:
            reason = "missing_fresh_execution_book"
        past = history[history.available_at < game.decision_at].sort_values("scheduled_at")
        team_features = []
        for team in (game.home_id,game.away_id):
            games = past[(past.home_id == team)|(past.away_id == team)].tail(config["rolling_games"])
            if len(games) < config["min_history"]:
                reason = reason or "insufficient_prior_games"
            home = games.home_id == team
            pf = np.where(home, games.home_score, games.away_score)
            pa = np.where(home, games.away_score, games.home_score)
            rest = min(14, (game.scheduled_at-games.scheduled_at.max()).total_seconds()/86400) if len(games) else 14
            team_features.append(dict(margin=float(np.mean(pf-pa)) if len(games) else 0,
                pf=float(np.mean(pf)) if len(games) else 0,pa=float(np.mean(pa)) if len(games) else 0,
                rest=rest,count=len(games),win=float(np.mean(pf>pa)) if len(games) else .5))
        if reason:
            excluded.append({"game_id":game.game_id,"reason":reason})
            continue
        u, v = 1/refs.home_odds.to_numpy(), 1/refs.away_odds.to_numpy()
        q = u/(u+v)
        h,a = team_features
        row = dict(game_id=game.game_id,home_id=game.home_id,away_id=game.away_id,
                   decision_at=game.decision_at.isoformat(),scheduled_at=game.scheduled_at.isoformat(),
                   q=float(np.median(q)),reference_dispersion=float(np.std(q)),
                   reference_age_minutes=float((game.decision_at-refs.quote_at).dt.total_seconds().max()/60),
                   margin_diff=h["margin"]-a["margin"],points_for_diff=h["pf"]-a["pf"],
                   points_against_diff=h["pa"]-a["pa"],rest_diff=h["rest"]-a["rest"],
                   home_back_to_back=int(h["rest"]<1.5),away_back_to_back=int(a["rest"]<1.5),
                   home_history=h["count"],away_history=a["count"],home_win_rate=h["win"],away_win_rate=a["win"])
        for side in ("home","away"):
            offer = offers.sort_values([side+"_odds","book"],ascending=[False,True]).iloc[0]
            row[side+"_odds"] = float(offer[side+"_odds"])
            row[side+"_book"] = offer.book
            row[side+"_quote_at"] = offer.quote_at.isoformat()
            later=latest_quotes(o,game.game_id,game.decision_at+pd.Timedelta(minutes=5),config)
            later=later[(later.book==offer.book)&(later.available_at>game.decision_at)]
            row[side+"_delay5_odds"]=float(later.iloc[0][side+"_odds"]) if len(later) else np.nan
        result = r[r.game_id == game.game_id]
        row["y"] = int(result.iloc[0].home_score>result.iloc[0].away_score) if len(result) else np.nan
        row["result_available_at"] = result.iloc[0].available_at.isoformat() if len(result) else ""
        records.append(row)
    out = Path(out)
    if out.exists():
        raise FileExistsError("Use a new dataset output directory")
    out.mkdir(parents=True)
    pd.DataFrame(records).to_csv(out/"features.csv",index=False)
    pd.DataFrame(excluded,columns=["game_id","reason"]).to_csv(out/"excluded.csv",index=False)
    audit = {"schema_version":1,"mode":config["mode"],"games":len(g),"eligible":len(records),
        "excluded":len(excluded),"exclusion_reasons":pd.Series([x["reason"] for x in excluded],dtype=str).value_counts().to_dict(),
        "features":FEATURES,"input_hashes":{k:digest(Path(folder)/(k+".csv")) for k in COLUMNS},
        "features_sha256":digest(out/"features.csv"),"config":config,
        "lineage_limit":"Timestamp assertions validate declared availability; archive provenance must be audited separately."}
    write_json(out/"audit.json",audit)
    return audit
