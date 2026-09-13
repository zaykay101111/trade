import pandas as pd
import pytest
from test_free import fixture_data
from sports_method.free_data import build_features
from sports_method.free_train import partition, fit_free
from sports_method.free_validate import fold_boundaries, validate_free
from sports_method.io import read_json


def test_fold_boundaries_and_holdout_guard(tmp_path):
    df = build_features(fixture_data(tmp_path))
    for year in (2022, 2023, 2024):
        parts = partition(df, fold_boundaries(year))
        assert parts['calibration'].available_at.max() < parts['validation'].decision_at.min()
        assert parts['train'].decision_at.max() < parts['tune'].decision_at.min()
    with pytest.raises(ValueError, match='development seasons'):
        fold_boundaries(2025)
    b = fold_boundaries(2024)
    b['validation'] = '2026-07-01'
    with pytest.raises(ValueError, match='holdout'):
        fit_free(tmp_path, tmp_path/'bad', boundaries=b)
    assert not (tmp_path/'bad').exists()


def test_delay_changes_visibility_not_decisions(tmp_path):
    df = fixture_data(tmp_path).iloc[:3].copy()
    normal = build_features(df)
    df.available_at += pd.Timedelta(hours=48)
    delayed = build_features(df)
    assert normal.loc[1,'elo_diff'] != 0
    assert delayed.loc[1,'elo_diff'] == 0
    pd.testing.assert_series_equal(normal.decision_at, delayed.decision_at)
    pd.testing.assert_series_equal(normal.y, delayed.y)
    for bad in (-1, float('nan'), float('inf')):
        with pytest.raises(ValueError, match='Delay'):
            fit_free(tmp_path, tmp_path/'bad', delay_hours=bad)


def test_rolling_end_to_end(tmp_path):
    fixture_data(tmp_path)
    out = tmp_path/'rolling'
    result = validate_free(tmp_path, out, threads=1)
    assert result['completed'] == 9
    report = read_json(out/'report.json')
    assert report['final_holdout'] == 'NOT SCORED'
    assert set(report['folds']) == {'2022-23', '2023-24', '2024-25'}
    assert len({r['games'] for r in report['pooled'].values()}) == 1
    for season, scenarios in report['folds'].items():
        assert set(scenarios) == {'0', '24', '48'}
        for v in scenarios['0']['change_vs_no_extra_delay'].values():
            assert v['mean_absolute_probability_change'] == 0
            assert abs(v['log_loss_change']) < 1e-6
    for p in out.glob('*/validation_predictions.csv'):
        df = pd.read_csv(p)
        assert pd.to_datetime(df.decision_at, utc=True).max() < pd.Timestamp('2025-07-01', tz='UTC')
    with pytest.raises(FileExistsError):
        validate_free(tmp_path, out)
