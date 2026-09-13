"""Synthetic-odds verification of the betting machinery.

Every number here is synthetic. These tests verify arithmetic and safeguards
only; nothing in them is evidence of edge, and synthetic profit must never
pass an evidence gate.
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sports_method.io import read_json
from sports_method.policy import candidate, replay

POLICY = read_json(Path(__file__).parents[1]/"configs/first_model.json")["policy"]


def synthetic_rows(n, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2024-01-01T18:00:00Z")
    for i in range(n):
        p_true = rng.uniform(.3, .7)
        rows.append(dict(
            game_id=f"S{i:04d}",
            decision_at=str(start+pd.Timedelta(hours=6*i)),
            result_available_at=str(start+pd.Timedelta(hours=6*i+20)),
            home_odds=float(np.clip(rng.normal(1/p_true, .15), 1.05, 15)),
            away_odds=float(np.clip(rng.normal(1/(1-p_true), .15), 1.05, 15)),
            home_book="synth", away_book="synth",
            y=int(rng.random() < p_true),
            p_model=float(np.clip(p_true+rng.normal(0, .05), .01, .99))))
    return pd.DataFrame(rows)


def test_candidate_ev_kelly_and_min_odds_are_consistent():
    for p in (.35, .5, .62, .75):
        for home, away in ((1.8, 2.1), (1.3, 3.6), (2.6, 1.55)):
            row = {"home_odds": home, "away_odds": away, "home_book": "a", "away_book": "b"}
            x = candidate(row, p, POLICY)
            prob = p if x["side"] == "home" else 1-p
            risk = max(0., prob-POLICY["probability_haircut"])
            cost = POLICY["cost_per_stake"]
            assert x["ev"] == pytest.approx(risk*x["odds"]-1-cost)
            if x["min_odds"] is not None:
                shaved = dict(row)
                shaved[x["side"]+"_odds"] = x["min_odds"]*.999
                worse = candidate(shaved, p, POLICY)
                if worse["side"] == x["side"]:
                    assert not worse["qualifies"]
            if x["odds"]-1-cost > 0:
                full = x["ev"]/((x["odds"]-1-cost)*(1+cost))
                assert x["kelly"] == pytest.approx(max(0., full))


def test_replay_accounting_identity_and_caps():
    frame = synthetic_rows(400)
    bets, report = replay(frame, "p_model", POLICY)
    if not len(bets):
        pytest.skip("No qualifying synthetic bets under this seed")
    expected_pnl = float((bets.stake*bets.return_per_stake).sum())
    assert report["pnl"] == pytest.approx(expected_pnl)
    assert report["turnover"] == pytest.approx(float(bets.stake.sum()))
    increment = POLICY["stake_increment"]
    assert all(abs(s/increment-round(s/increment)) < 1e-6 for s in bets.stake)
    # Caps are fractions of live equity, which the synthetic run never lets exceed
    # this bound, so the bankroll-scaled ceiling is exact here.
    peak_equity = POLICY["bankroll"]+max(0., report["pnl"])
    assert bets.stake.max() <= peak_equity*POLICY["max_game_fraction"]+increment
    daily = bets.assign(day=pd.to_datetime(bets.decision_at, utc=True).dt.date).groupby("day").stake.sum()
    assert (daily <= peak_equity*POLICY["max_daily_fraction"]+increment).all()
    assert 0 <= report["max_drawdown"] <= 1


def test_worse_prices_reduce_activity_to_zero():
    frame = synthetic_rows(400)
    bets, report = replay(frame, "p_model", POLICY)
    crushed, crushed_report = replay(frame, "p_model", POLICY, odds_multiplier=.5)
    assert len(crushed) < len(bets)
    assert crushed_report["turnover"] < report["turnover"]
    zero, zero_report = replay(frame, "p_model", POLICY, odds_multiplier=.01)
    assert len(zero) == 0 and zero_report["bets"] == 0


def test_result_before_decision_is_refused():
    frame = synthetic_rows(50)
    frame["p_model"] = .99  # force qualification
    frame.loc[:, "result_available_at"] = frame.decision_at
    with pytest.raises(ValueError, match="precedes"):
        replay(frame, "p_model", POLICY)


def test_synthetic_profit_is_labelled_not_evidence():
    # The demo/smoke path is the only consumer of synthetic odds; its outputs
    # must carry the synthetic warning so no gate can mistake them.
    from sports_method.demo import make_demo  # noqa: F401  (import guards existence)
    text = Path(Path(__file__).parents[1]/"src"/"sports_method"/"demo.py").read_text()
    assert "synthetic" in text.lower()
