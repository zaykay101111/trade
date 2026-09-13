import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sports_method.data import build,load_tables,latest_quotes,FEATURES,utc
from sports_method.demo import make_demo
from sports_method.io import read_json
from sports_method.model import fit_calibration,calibrate,fit_logistic,predict_logistic
from sports_method.policy import candidate,replay
from sports_method.evaluate import block_interval
from sports_method.providers import fetch_odds,normalize_odds
from sports_method.paper import connect,settle,record_check,monitor

@pytest.fixture
def sample(tmp_path):
    config=read_json(Path(__file__).parents[1]/"configs/first_model.json")
    raw=make_demo(tmp_path/"raw",config,160)
    return raw,read_json(raw/"config.json")

def test_timezone_required():
    with pytest.raises(ValueError):utc(pd.Series(["2024-01-01"]))
    assert utc(pd.Series(["2024-01-01T10:00:00+00:00"])).iloc[0].hour==10

def test_future_results_do_not_change_earlier_features(sample,tmp_path):
    raw,c=sample
    build(raw,c,tmp_path/"a")
    r=pd.read_csv(raw/"results.csv")
    r.loc[len(r)-1,"home_score"]+=200
    r.to_csv(raw/"results.csv",index=False)
    build(raw,c,tmp_path/"b")
    a=pd.read_csv(tmp_path/"a/features.csv");b=pd.read_csv(tmp_path/"b/features.csv")
    pd.testing.assert_frame_equal(a[FEATURES+["q"]],b[FEATURES+["q"]])

def test_future_quote_not_used(sample):
    raw,c=sample;t=load_tables(raw,c)
    game=t["games"].iloc[50];o=t["odds"]
    before=latest_quotes(o,game.game_id,game.decision_at,c)
    later=before.copy();later["available_at"]=game.decision_at+pd.Timedelta(seconds=1)
    later["home_odds"]=100.
    after=latest_quotes(pd.concat([o,later]),game.game_id,game.decision_at,c)
    assert after.home_odds.max()<100

def test_result_before_game_rejected(sample):
    raw,c=sample;r=pd.read_csv(raw/"results.csv")
    r.loc[0,"available_at"]="1900-01-01T00:00:00Z";r.to_csv(raw/"results.csv",index=False)
    with pytest.raises(ValueError,match="before scheduled"):load_tables(raw,c)

def test_duplicate_games_rejected(sample):
    raw,c=sample;g=pd.read_csv(raw/"games.csv")
    pd.concat([g,g.iloc[:1]]).to_csv(raw/"games.csv",index=False)
    with pytest.raises(ValueError,match="duplicate"):load_tables(raw,c)

def test_schedule_leak_rejected(sample):
    raw,c=sample;g=pd.read_csv(raw/"games.csv")
    g.loc[0,"schedule_observed_at"]=g.loc[0,"scheduled_at"]
    g.to_csv(raw/"games.csv",index=False)
    with pytest.raises(ValueError,match="Schedule revision"):load_tables(raw,c)

def test_unknown_event_rejected(sample):
    raw,c=sample;o=pd.read_csv(raw/"odds.csv")
    o.loc[0,"game_id"]="UNKNOWN";o.to_csv(raw/"odds.csv",index=False)
    with pytest.raises(ValueError,match="Unmapped"):load_tables(raw,c)

def test_stale_quotes_excluded(sample,tmp_path):
    raw,c=sample;c["max_quote_age_minutes"]=0
    result=build(raw,c,tmp_path/"built")
    assert result["eligible"]==0
    assert result["exclusion_reasons"]["missing_fresh_reference_books"]==160

def test_no_duplicate_reference_vote(sample):
    raw,c=sample;c["reference_books"].append(c["reference_books"][0])
    with pytest.raises(ValueError,match="Duplicate configured"):load_tables(raw,c)

def test_policy_math_and_away_haircut():
    c={"probability_haircut":.015,"cost_per_stake":.005,"min_ev":.02}
    row={"home_odds":1.95,"away_odds":1.1,"home_book":"a","away_book":"a"}
    x=candidate(row,.55,c)
    assert x["ev"]==pytest.approx(.03825)
    assert x["min_odds"]==pytest.approx(1.9158878505)
    assert x["kelly"]==pytest.approx(.03825/(.945*1.005))
    row.update(home_odds=1.1,away_odds=3.)
    x=candidate(row,.55,c)
    assert x["side"]=="away"
    assert x["p_risk"]==pytest.approx(.435)

def test_open_exposure_cap_and_no_unsettled_reinvestment():
    c=read_json(Path(__file__).parents[1]/"configs/first_model.json")["policy"]
    rows=[dict(game_id=str(i),decision_at="2024-01-01T10:00:00Z",result_available_at="2024-01-01T20:00:00Z",
               home_odds=2.,away_odds=1.5,home_book="x",away_book="x",y=1,p_residual=.7) for i in range(20)]
    bets,report=replay(pd.DataFrame(rows),"p_residual",c)
    assert bets.stake.sum()<=100
    assert bets.stake.max()<=25
    assert report["pnl"]==pytest.approx(sum(bets.stake*(2-1-.005)))

def test_calibration_monotonic():
    p=np.linspace(.1,.9,100);y=np.tile([0,1],50)
    fit=fit_calibration(p,y)
    assert fit["slope"]>0
    assert np.all(np.diff(calibrate(p,fit))>=0)

def test_logistic_offset_at_zero_features():
    q=np.full(200,.6);y=np.tile([1,1,1,0,0],40)
    X=np.zeros((200,2));model=fit_logistic(X,y,q)
    assert np.allclose(predict_logistic(model,X,q),.6,atol=1e-5)

def test_block_interval_no_false_precision():
    assert block_interval([1,0],["2024-01-01","2024-01-02"]) is None
    values=np.ones(100)
    ci=block_interval(values,pd.date_range("2024-01-01",periods=100),repeats=50)
    assert ci==[1.,1.]

def test_downloader_dry_run_needs_no_key(tmp_path,monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY",raising=False)
    plan=tmp_path/"plan.json"
    plan.write_text(json.dumps({"timestamps":["2024-01-01T00:00:00Z"],"estimated_credits_upper_bound":30}))
    assert fetch_odds(plan,tmp_path/"raw",0)["dry_run"]
    assert not (tmp_path/"raw").exists()

def test_paper_settlement_and_duplicate_protection(tmp_path):
    ledger=tmp_path/"paper.db";db=connect(ledger)
    payload={"stake":25,"odds":1.95,"cost_per_stake":.005,"p":.55,"min_odds":1.91,
             "expiry":"2020-01-01T12:10:00Z","scheduled_at":"2020-01-01T13:00:00Z"}
    with db:db.execute("INSERT INTO decisions VALUES (?,?,?)",("one","2020-01-01T12:00:00Z",json.dumps(payload)))
    db.close()
    settle(ledger,"one","win")
    with pytest.raises(Exception):settle(ledger,"one","win")
    record_check(ledger,"one",1.95,True)
    report=monitor(ledger,tmp_path/"monitor")
    assert report["paper_pnl"]==pytest.approx(25*.945)
    assert report["price_available_rate_among_checked"]==0 # late checks cannot count as timely

def test_later_same_book_snapshot_used_only_for_delay(sample,tmp_path):
    raw,c=sample
    o=pd.read_csv(raw/"odds.csv");g=pd.read_csv(raw/"games.csv")
    target=g.iloc[80]
    later=o[(o.game_id==target.game_id)&(o.book.isin(c["execution_books"]))].copy()
    later["available_at"]=(pd.Timestamp(target.decision_at)+pd.Timedelta(minutes=4)).isoformat()
    later["quote_at"]=(pd.Timestamp(target.decision_at)+pd.Timedelta(minutes=3)).isoformat()
    later["home_odds"]=1.1;later["away_odds"]=1.1
    pd.concat([o,later]).to_csv(raw/"odds.csv",index=False)
    build(raw,c,tmp_path/"with_delay")
    features=pd.read_csv(tmp_path/"with_delay/features.csv")
    row=features[features.game_id==target.game_id].iloc[0]
    assert row.home_delay5_odds==1.1
    assert row.home_odds!=1.1
    assert row.away_delay5_odds==1.1

def test_freeze_detects_model_mutation(tmp_path):
    from sports_method.model import freeze,verify_freeze
    from sports_method.io import write_json,code_hash
    write_json(tmp_path/"bundle.json",{"code_sha256":code_hash(),"config":{"policy":{}}})
    (tmp_path/"residual.json").write_text("{}")
    freeze(tmp_path);verify_freeze(tmp_path)
    (tmp_path/"residual.json").write_text('{"changed":true}')
    with pytest.raises(ValueError,match="modified"):verify_freeze(tmp_path)

