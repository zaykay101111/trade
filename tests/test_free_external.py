import numpy as np
import pandas as pd
import pytest
from sports_method.free_data import FEATURES, build_features, load_games
from sports_method.free_external import (PAPER_ERA, era_partition, expected_calibration_error,
                                         replicate_external)
from sports_method.free_train import BOUNDARIES as DEV_BOUNDARIES
from sports_method.io import read_json


def era_fixture(tmp_path, start='2014-10-01', end='2019-06-01'):
    dates = pd.date_range(start, end, freq='2D', tz='UTC')
    rng = np.random.default_rng(11)
    games, results = [], []
    for i, date in enumerate(dates):
        gid = str(i).zfill(10)
        games.append(dict(game_id=gid, home_id='A' if i % 2 else 'B', away_id='B' if i % 2 else 'A',
                          scheduled_at=date, decision_at=date-pd.Timedelta(hours=1),
                          schedule_observed_at=date-pd.Timedelta(days=2), is_neutral=False,
                          season_type='regular', source_status='Final'))
        results.append(dict(game_id=gid, home_score=112 if rng.random() < .58 else 95,
                            away_score=101, available_at=date+pd.Timedelta(hours=24)))
    pd.DataFrame(games).to_csv(tmp_path/'games.csv', index=False)
    pd.DataFrame(results).to_csv(tmp_path/'results.csv', index=False)
    return load_games(tmp_path)


def test_ece_detects_miscalibration():
    rng = np.random.default_rng(0)
    p = rng.uniform(.1, .9, 4000)
    y = (rng.uniform(size=4000) < p).astype(int)
    good = expected_calibration_error(p, y)
    bad = expected_calibration_error(np.clip(p+.15, 0, 1), y)
    assert good['ece'] < .05 < bad['ece']
    # Binary classwise-ECE bins the same games, so it must agree with ECE.
    assert good['ece'] == pytest.approx(good['classwise_ece'])


def test_era_partition_is_chronological_and_available(tmp_path):
    parts = era_partition(build_features(era_fixture(tmp_path)), PAPER_ERA)
    previous = None
    for name, end in list(PAPER_ERA.items())[1:]:
        boundary = pd.Timestamp(end, tz='UTC')
        assert parts[name].decision_at.max() < boundary
        if name != 'evaluation':
            assert parts[name].available_at.max() < boundary
        if previous is not None:
            assert previous.decision_at.max() < parts[name].decision_at.min()
        previous = parts[name]


def test_era_must_be_increasing(tmp_path):
    features = build_features(era_fixture(tmp_path))
    bad = dict(PAPER_ERA, tune='2016-01-01')
    with pytest.raises(ValueError, match='strictly increasing'):
        era_partition(features, bad)
    with pytest.raises(ValueError, match='start, train, tune'):
        era_partition(features, {'start': '2014-07-01', 'train': '2017-07-01'})


def test_external_run_does_not_touch_reserved_dataset_boundaries(tmp_path):
    """The external era ends long before the 2020-2026 development window opens."""
    assert pd.Timestamp(PAPER_ERA['evaluation'], tz='UTC') < pd.Timestamp('2020-07-01', tz='UTC')
    assert pd.Timestamp(PAPER_ERA['evaluation'], tz='UTC') < pd.Timestamp(DEV_BOUNDARIES['train'], tz='UTC')


def test_replicate_end_to_end(tmp_path):
    era_fixture(tmp_path)
    out = tmp_path/'paper-years'
    result = replicate_external(tmp_path, out, threads=1, label='test era')
    report = read_json(out/'report.json')
    assert set(report['metrics']) >= {'home_rate', 'elo', 'logistic', 'boosted'}
    assert set(report['calibration_error']) >= {'logistic', 'elo'}
    predictions = pd.read_csv(out/'evaluation_predictions.csv', dtype={'game_id': str})
    assert len(predictions) == report['split_counts']['evaluation']
    assert pd.to_datetime(predictions.decision_at, utc=True).min() >= pd.Timestamp(PAPER_ERA['calibration'], tz='UTC')
    assert pd.to_datetime(predictions.decision_at, utc=True).max() < pd.Timestamp(PAPER_ERA['evaluation'], tz='UTC')
    assert (out/'PASTE_BACK.md').exists()
    with pytest.raises(FileExistsError):
        replicate_external(tmp_path, out, threads=1)
