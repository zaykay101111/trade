import numpy as np
import pandas as pd
import pytest

from sports_method import nfl_data as nd
from sports_method import nfl_policy as npol
from sports_method import sports

CONTRACT = nd.CONTRACT


def nfl_fixture(tmp_path, *, with_tie=True, seasons=(2024, 2025), pairs=1, weeks=12):
    """Synthetic NFL seasons, including a tie. Enlarge via seasons/pairs/weeks."""
    rows, results = [], []
    kickoff = pd.Timestamp("2024-09-08T17:00:00Z")
    teams = ["T%02d" % i for i in range(2*pairs+2)]
    matchups = [(teams[2*i], teams[2*i+1]) for i in range(pairs)] or [(teams[0], teams[1])]
    n = 0
    for season in seasons:
        for week in range(1, weeks+1):
            for home, away in matchups:
                start = kickoff+pd.Timedelta(days=7*n//max(1, len(matchups)))
                tie = with_tie and n == 5
                home_score, away_score = (17, 17) if tie else (24, 17) if n % 3 else (13, 20)
                rows.append(dict(
                    game_id=f"{season}_{week:02d}_{away}_{home}", sport="nfl", season=season,
                    week=week, home_id=home, away_id=away, home_name=home, away_name=away,
                    scheduled_at=start.isoformat(),
                    schedule_observed_at=(start-pd.Timedelta(hours=48)).isoformat(),
                    decision_at=(start-pd.Timedelta(minutes=60)).isoformat(),
                    season_type="regular", contract=CONTRACT, is_neutral=False,
                    div_game=n % 2, roof="outdoors", source_status="Final"))
                results.append(dict(game_id=rows[-1]["game_id"], home_score=home_score,
                                    away_score=away_score, overtime=int(tie),
                                    available_at=(start+pd.Timedelta(hours=24)).isoformat()))
                n += 1
    data = tmp_path/"nfl"
    data.mkdir()
    pd.DataFrame(rows).to_csv(data/"games.csv", index=False)
    pd.DataFrame(results).to_csv(data/"results.csv", index=False)
    return data


def test_ties_are_loaded_not_rejected(tmp_path):
    data = nfl_fixture(tmp_path)
    games = nd.load_nfl_games(data)
    assert games.is_tie.sum() == 1
    tied = games[games.is_tie == 1].iloc[0]
    assert tied.home_score == tied.away_score
    # y is only meaningful for decided games; the tie must not read as a home win.
    assert tied.y == 0 and tied.elo_score == .5


def test_nba_loader_still_rejects_a_tie_but_nfl_accepts_one(tmp_path):
    from sports_method.free_data import load_games
    data = nfl_fixture(tmp_path)
    with pytest.raises(ValueError, match="cannot be tied"):
        load_games(data)
    assert len(nd.load_nfl_games(data)) > 0


def test_contract_is_enforced(tmp_path):
    data = nfl_fixture(tmp_path)
    games = pd.read_csv(data/"games.csv")
    games["contract"] = "nba_regular_fullgame_moneyline_ot"
    games.to_csv(data/"games.csv", index=False)
    with pytest.raises(ValueError, match="contract"):
        nd.load_nfl_games(data)


def test_features_use_only_information_available_before_the_cutoff(tmp_path):
    data = nfl_fixture(tmp_path)
    games = nd.load_nfl_games(data)
    base = nd.build_nfl_features(games)
    tampered = games.copy()
    # Rewrite the LAST game's score. Nothing decided earlier may move.
    last = tampered.index[-1]
    tampered.loc[last, ["home_score", "away_score"]] = [99, 0]
    tampered["is_tie"] = (tampered.home_score == tampered.away_score).astype(int)
    tampered["y"] = (tampered.home_score > tampered.away_score).astype(int)
    tampered["elo_score"] = np.where(tampered.is_tie.eq(1), .5, tampered.y.astype(float))
    after = nd.build_nfl_features(tampered)
    columns = list(nd.NFL_FEATURES)
    pd.testing.assert_frame_equal(base.iloc[:-1][columns], after.iloc[:-1][columns])


def test_three_way_distribution_is_proper_and_metrics_split_out_ties(tmp_path):
    data = nfl_fixture(tmp_path)
    features = nd.build_nfl_features(nd.load_nfl_games(data))
    rate = nd.tie_rate(features)
    assert 0 < rate < .05
    probabilities = nd.three_way(features.p_elo, rate)
    assert np.allclose(probabilities.sum(axis=1), 1)
    assert (probabilities > 0).all()
    m = nd.three_way_metrics(features, features.p_elo, rate)
    assert m["games"] == len(features)
    assert m["decided_games"] == len(features)-m["ties"]
    assert m["three_way_log_loss"] > 0 and m["decided_log_loss"] > 0


def test_tie_rate_is_shrunk_and_never_zero():
    # A tie-free training window must not imply a tie is impossible.
    frame = pd.DataFrame({"is_tie": np.zeros(500, dtype=int)})
    rate = nd.tie_rate(frame)
    assert 0 < rate < .002
    many = pd.DataFrame({"is_tie": np.ones(500, dtype=int)})
    assert nd.tie_rate(many) > rate


def test_push_settlement_returns_the_stake():
    assert npol.settle("tie", "home", 2.0, 100) == 0
    assert npol.settle("void", "away", 2.0, 100) == 0
    assert npol.settle("home", "home", 2.0, 100) == pytest.approx(100)
    assert npol.settle("away", "home", 2.0, 100) == pytest.approx(-100)
    # Cost is charged even when the bet pushes.
    assert npol.settle("tie", "home", 2.0, 100, cost_per_stake=.01) == pytest.approx(-1)


def test_push_aware_ev_differs_from_binary_and_break_even_is_exact():
    policy = {"probability_haircut": 0., "cost_per_stake": 0., "min_ev": 0.}
    p_home, p_tie, odds = .5, .04, 2.1
    best = npol.candidate(p_home, p_tie, odds, 1.9, policy)
    assert best["side"] == "home"
    p_win = p_home*(1-p_tie)
    p_lose = (1-p_home)*(1-p_tie)
    assert best["ev"] == pytest.approx(p_win*(odds-1)-p_lose)
    # Ignoring the push would use p_lose = 1 - p_win and understate EV.
    assert best["ev"] > p_win*(odds-1)-(1-p_win)
    at_min = npol.candidate(p_home, p_tie, best["min_odds"], 1.0001, policy)
    assert at_min["ev"] == pytest.approx(0, abs=1e-9)


def test_push_aware_kelly_reduces_to_binary_when_ties_are_impossible():
    policy = {"probability_haircut": 0., "cost_per_stake": 0., "min_ev": 0.}
    p_home, odds = .6, 2.0
    best = npol.candidate(p_home, 0., odds, 1.5, policy)
    binary_kelly = (p_home*(odds-1)-(1-p_home))/(odds-1)
    assert best["kelly"] == pytest.approx(binary_kelly)


def test_sport_registry_resolves_and_detects(tmp_path):
    nfl = sports.get("nfl")
    nba = sports.get("nba")
    assert nfl.allows_ties and not nba.allows_ties
    assert nfl.contract != nba.contract
    assert len(nfl.feature_names) == 10 and len(nba.feature_names) == 11
    with pytest.raises(ValueError, match="Unknown sport"):
        sports.get("mlb")
    data = nfl_fixture(tmp_path)
    assert sports.detect(data).key == "nfl"


def test_detect_treats_an_undeclared_dataset_as_nba(tmp_path):
    data = nfl_fixture(tmp_path)
    games = pd.read_csv(data/"games.csv").drop(columns=["sport", "contract"])
    games.to_csv(data/"games.csv", index=False)
    assert sports.detect(data).key == "nba"
