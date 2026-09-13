"""NFL prospective capture, settlement and push-aware betting on synthetic odds.

Every price in this file is SYNTHETIC and clearly labelled. These tests verify
arithmetic, settlement and safeguards only. No synthetic profit here is
evidence of any market advantage.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sports_method import nfl_collect as nc
from sports_method import nfl_monitor as nm
from sports_method import nfl_policy as npol
from sports_method.io import write_json
from test_nfl import nfl_fixture

POLICY = {"probability_haircut": .015, "cost_per_stake": .005, "min_ev": .02,
          "bankroll": 1000., "kelly_fraction": .25, "max_game_fraction": .025,
          "max_open_fraction": .10, "max_daily_fraction": .10, "stake_increment": 1.}


def big_fixture(tmp_path):
    """Large enough to satisfy the production fit/calibration minimums."""
    return nfl_fixture(tmp_path, seasons=(2019, 2020, 2021, 2022, 2023, 2024),
                       pairs=6, weeks=17)


def frozen_pair(tmp_path, data):
    out = tmp_path/"pair"
    nc.freeze_nfl(data, out, fit_through=2023, calibration_season=2024)
    return out


def future_collection(tmp_path, data, cutoff):
    """A one-game collection whose cutoff lies in the caller's chosen future."""
    games = pd.read_csv(Path(data)/"games.csv", dtype={"game_id": str})
    row = games.iloc[0].copy()
    row["game_id"] = "2026_01_AAA_BBB"
    row["season"], row["week"] = 2026, 1
    row["scheduled_at"] = (cutoff+pd.Timedelta(minutes=60)).isoformat()
    row["decision_at"] = cutoff.isoformat()
    row["schedule_observed_at"] = (cutoff-pd.Timedelta(hours=48)).isoformat()
    collection = tmp_path/"collection"
    collection.mkdir()
    pd.DataFrame([row]).to_csv(collection/"schedule.csv", index=False)
    write_json(collection/"collection.json",
               {"sport": "nfl", "season": 2026, "games": 1})
    return collection


def test_freeze_is_single_use_and_reserves_the_holdout(tmp_path):
    data = big_fixture(tmp_path)
    out = frozen_pair(tmp_path, data)
    bundle = json.loads((out/"bundle.json").read_text())
    assert bundle["sport"] == "nfl" and bundle["reserved_holdout_season"] == 2025
    assert 0 < bundle["tie_rate"] < .05
    assert "metrics" not in bundle
    with pytest.raises(FileExistsError):
        nc.freeze_nfl(data, out, fit_through=2023, calibration_season=2024)


def test_poll_window_backdating_and_drift_gates(tmp_path, monkeypatch):
    data = big_fixture(tmp_path)
    pair = frozen_pair(tmp_path, data)
    cutoff = pd.Timestamp("2026-09-13T19:25:00Z")
    collection = future_collection(tmp_path, data, cutoff)
    out = tmp_path/"records"
    with pytest.raises(ValueError, match="backdate"):
        nc.poll_nfl(collection, pair, data, out, at=str(cutoff), record=True)
    # Outside the five-minute pre-cutoff window nothing is written.
    assert nc.poll_nfl(collection, pair, data, out,
                       at=str(cutoff-pd.Timedelta(minutes=30)))["games"] == 0
    assert nc.poll_nfl(collection, pair, data, out,
                       at=str(cutoff+pd.Timedelta(seconds=1)))["games"] == 0
    assert nc.poll_nfl(collection, pair, data, out,
                       at=str(cutoff-pd.Timedelta(minutes=2)))["games"] == 1
    # Repeat in the same window must not duplicate or overwrite.
    assert nc.poll_nfl(collection, pair, data, out,
                       at=str(cutoff-pd.Timedelta(minutes=1)))["games"] == 0
    assert len(list((out/"simulated").glob("*.json"))) == 1
    assert not (out/"recorded").exists()
    bundle = json.loads((pair/"bundle.json").read_text())
    bundle["surface"]["nfl_data"] = "changed"
    write_json(pair/"bundle.json", bundle)
    with pytest.raises(ValueError, match="drifted"):
        nc.poll_nfl(collection, pair, data, out, at=str(cutoff-pd.Timedelta(minutes=2)))


def test_recorded_and_simulated_stay_separate(tmp_path, monkeypatch):
    data = big_fixture(tmp_path)
    pair = frozen_pair(tmp_path, data)
    cutoff = pd.Timestamp("2026-09-13T19:25:00Z")
    collection = future_collection(tmp_path, data, cutoff)
    out = tmp_path/"records"
    nc.poll_nfl(collection, pair, data, out, at=str(cutoff-pd.Timedelta(minutes=2)))
    issue = cutoff-pd.Timedelta(minutes=2)
    monkeypatch.setattr(nc, "now", lambda: issue.isoformat())
    result = nc.poll_nfl(collection, pair, data, out, record=True)
    assert result["mode"] == "prospective" and result["games"] == 1
    # The same game exists once in each directory and the files never mix.
    assert len(list((out/"simulated").glob("*.json"))) == 1
    assert len(list((out/"recorded").glob("*.json"))) == 1
    recorded = json.loads(next((out/"recorded").glob("*.json")).read_text())
    assert recorded["mode"] == "prospective"
    assert recorded["predictions"]["p_tie"] > 0
    three = recorded["predictions"]["challenger_three_way"]
    assert sum(three.values()) == pytest.approx(1.)


def test_late_completion_refuses_to_issue(tmp_path, monkeypatch):
    data = big_fixture(tmp_path)
    pair = frozen_pair(tmp_path, data)
    cutoff = pd.Timestamp("2026-09-13T19:25:00Z")
    collection = future_collection(tmp_path, data, cutoff)
    times = iter([(cutoff-pd.Timedelta(minutes=2)).isoformat(),
                  (cutoff+pd.Timedelta(seconds=1)).isoformat()])
    monkeypatch.setattr(nc, "now", lambda: next(times))
    with pytest.raises(ValueError, match="crossed T-60"):
        nc.poll_nfl(collection, pair, data, tmp_path/"late", record=True)
    assert not (tmp_path/"late").exists()


def settled_records(tmp_path, outcomes):
    """Build recorded NFL snapshots plus a dataset settling them as requested."""
    data = nfl_fixture(tmp_path)
    games = pd.read_csv(Path(data)/"games.csv", dtype={"game_id": str})
    results = pd.read_csv(Path(data)/"results.csv", dtype={"game_id": str})
    template = games.iloc[0].to_dict()
    records = tmp_path/"records"/"recorded"
    records.mkdir(parents=True)
    schedule_rows = []
    import hashlib
    base = pd.Timestamp("2026-09-13T19:25:00Z")
    for i, outcome in enumerate(outcomes):
        game_id = f"2026_0{i+1}_XXX_YYY"
        cutoff = base+pd.Timedelta(days=7*i)
        schedule_rows.append({**template, "game_id": game_id, "season": 2026, "week": i+1,
                              "scheduled_at": (cutoff+pd.Timedelta(minutes=60)).isoformat(),
                              "decision_at": cutoff.isoformat(),
                              "schedule_observed_at": (cutoff-pd.Timedelta(hours=48)).isoformat()})
        if outcome != "cancelled":
            scores = {"home": (24, 17), "away": (17, 24), "tie": (20, 20)}[outcome]
            games.loc[len(games)] = schedule_rows[-1]
            results.loc[len(results)] = {"game_id": game_id, "home_score": scores[0],
                                         "away_score": scores[1], "overtime": 0,
                                         "available_at": (cutoff+pd.Timedelta(hours=25)).isoformat()}
        payload = {"sport": "nfl", "contract": nc.nfl_data.CONTRACT, "mode": "prospective",
                   "issued_at": str(cutoff-pd.Timedelta(minutes=2)),
                   "inputs_observed_at": str(cutoff-pd.Timedelta(minutes=2)),
                   "game_id": game_id, "season": 2026, "week": i+1,
                   "home_id": "XXX", "away_id": "YYY",
                   "scheduled_at": str(cutoff+pd.Timedelta(minutes=60)), "cutoff": str(cutoff),
                   "predictions": {"p_control_home_given_decided": .55,
                                   "p_challenger_home_given_decided": .60, "p_tie": .002,
                                   "control_three_way": {}, "challenger_three_way": {}},
                   "features": {}, "provenance": {}}
        name = hashlib.sha256(game_id.encode()).hexdigest()+".json"
        (records/name).write_text(json.dumps(payload))
    games.to_csv(data/"games.csv", index=False)
    results.to_csv(data/"results.csv", index=False)
    collection = tmp_path/"collection"
    collection.mkdir()
    # A cancelled game VANISHES from the schedule feed, as verified upstream.
    kept = [r for r, o in zip(schedule_rows, outcomes) if o != "cancelled"]
    pd.DataFrame(kept).to_csv(collection/"schedule.csv", index=False)
    return data, collection, tmp_path/"records"


def test_settlement_handles_ties_voids_and_pending(tmp_path):
    data, collection, records = settled_records(
        tmp_path, ["home", "away", "tie", "cancelled"])
    report = nm.settle_nfl(records, collection, data, tmp_path/"eval")
    assert report["sport"] == "nfl" and report["settled"] == 3
    assert report["voided_cancelled"] == ["2026_04_XXX_YYY"]
    assert report["awaiting_result"] == []
    for model in ("control", "challenger"):
        m = report["models"][model]
        assert m["games"] == 3 and m["ties"] == 1 and m["decided_games"] == 2
        assert m["three_way_log_loss"] > 0
    rows = pd.read_csv(tmp_path/"eval"/"settled_pairs.csv")
    assert set(rows.outcome) == {"home", "away", "tie"}
    assert rows[rows.outcome == "tie"].moneyline_settlement.iloc[0] == "push"
    text = (tmp_path/"eval"/"PASTE_BACK.md").read_text()
    assert "push" in text and "never pooled" in text


def test_settlement_never_modifies_a_record_and_detects_tampering(tmp_path):
    data, collection, records = settled_records(tmp_path, ["home", "away"])
    before = {p.name: p.read_bytes() for p in (records/"recorded").glob("*.json")}
    nm.settle_nfl(records, collection, data, tmp_path/"eval")
    after = {p.name: p.read_bytes() for p in (records/"recorded").glob("*.json")}
    assert before == after
    victim = next((records/"recorded").glob("*.json"))
    victim.rename(victim.with_name("0"*64+".json"))
    with pytest.raises(ValueError, match="does not match"):
        nm.settle_nfl(records, collection, data, tmp_path/"eval2")


def test_status_counts_missed_windows(tmp_path):
    data, collection, records = settled_records(tmp_path, ["home", "away", "tie"])
    status = nm.nfl_status(collection, records, at="2027-01-01T00:00:00Z")
    assert status["sport"] == "nfl"
    assert status["past_cutoffs"] == 3 and status["recorded"] == 3
    assert status["missed_games"] == 0
    empty = tmp_path/"nothing"
    assert nm.nfl_status(collection, empty,
                         at="2027-01-01T00:00:00Z")["missed_games"] == 3


# --- synthetic-odds betting checks (SYNTHETIC PRICES, not evidence) ---

def test_synthetic_push_settlement_conserves_stake():
    stake, odds = 100., 2.0
    assert npol.settle("tie", "home", odds, stake) == 0
    assert npol.settle("void", "home", odds, stake) == 0
    # Over a synthetic book of pushes, bankroll is unchanged before costs.
    total = sum(npol.settle("tie", "home", odds, stake) for _ in range(50))
    assert total == 0


def test_synthetic_correlated_week_exposure_is_capped():
    """Same-week NFL bets settle together, so their exposure must be summed."""
    rng = np.random.default_rng(11)
    equity = POLICY["bankroll"]
    open_stake = 0.
    placed = []
    for _ in range(20):                       # one synthetic NFL week
        p_home = float(rng.uniform(.45, .75))
        best = npol.candidate(p_home, .002, 2.05, 1.95, POLICY)
        if not best["qualifies"]:
            continue
        wanted = equity*min(POLICY["kelly_fraction"]*best["kelly"],
                            POLICY["max_game_fraction"])
        # The whole week is one settlement block: cap on total open exposure.
        allowed = min(wanted, equity*POLICY["max_open_fraction"]-open_stake)
        stake = np.floor(max(0., allowed)/POLICY["stake_increment"])*POLICY["stake_increment"]
        if stake <= 0:
            continue
        open_stake += stake
        placed.append(stake)
    assert placed, "synthetic prices should qualify at least one bet"
    assert open_stake <= equity*POLICY["max_open_fraction"]+1e-9
    assert max(placed) <= equity*POLICY["max_game_fraction"]+1e-9


def test_synthetic_worse_prices_stop_qualification():
    generous = npol.candidate(.62, .002, 2.2, 1.8, POLICY)
    assert generous["qualifies"]
    crushed = npol.candidate(.62, .002, 1.2, 1.8, POLICY)
    assert not crushed["qualifies"] or crushed["ev"] < generous["ev"]
    assert not npol.candidate(.62, .002, 1.01, 1.01, POLICY)["qualifies"]


def test_ignoring_the_push_would_overstate_required_price():
    """The push-aware break-even is strictly cheaper than the binary one."""
    policy = {"probability_haircut": 0., "cost_per_stake": 0., "min_ev": 0.}
    p_home, p_tie = .5, .05
    best = npol.candidate(p_home, p_tie, 2.5, 1.1, policy)
    p_win = p_home*(1-p_tie)
    binary_break_even = 1/p_win           # d where p_win*(d-1) = 1-p_win
    assert best["min_odds"] < binary_break_even
