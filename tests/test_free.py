import numpy as np
import pandas as pd
import pytest
from sports_method.free_data import FEATURES, build_features, load_games
from sports_method.free_train import fit_free, partition, paired_interval
from sports_method.io import read_json


def fixture_data(tmp_path):
    dates = pd.date_range('2020-10-01', '2026-06-01', freq='2D', tz='UTC')
    rng = np.random.default_rng(7)
    games, results = [], []
    for i, date in enumerate(dates):
        gid = str(i).zfill(10)
        games.append(dict(game_id=gid, home_id='A' if i%2 else 'B', away_id='B' if i%2 else 'A',
                          scheduled_at=date, decision_at=date-pd.Timedelta(hours=1),
                          schedule_observed_at=date-pd.Timedelta(days=2), is_neutral=False,
                          season_type='regular', source_status='Final'))
        results.append(dict(game_id=gid, home_score=110 if rng.random()<.6 else 90,
                            away_score=100, available_at=date+pd.Timedelta(hours=24)))
    pd.DataFrame(games).to_csv(tmp_path/'games.csv', index=False)
    pd.DataFrame(results).to_csv(tmp_path/'results.csv', index=False)
    return load_games(tmp_path)


def test_no_current_or_future_score_leakage(tmp_path):
    df = fixture_data(tmp_path)
    original = build_features(df)
    changed = df.copy()
    changed.loc[changed.index >= 50, 'home_score'] += 500
    changed.loc[changed.index >= 50, 'y'] = 1
    modified = build_features(changed)
    pd.testing.assert_frame_equal(original.loc[:50, FEATURES+['p_elo']], modified.loc[:50, FEATURES+['p_elo']])


def test_result_at_cutoff_is_not_visible(tmp_path):
    df = fixture_data(tmp_path).iloc[:3].copy()
    df.loc[0, 'available_at'] = df.loc[1, 'decision_at']
    df.loc[1:, 'available_at'] += pd.Timedelta(days=100)
    f = build_features(df)
    assert f.loc[1, 'elo_diff'] == 0
    assert f.loc[2, 'elo_diff'] != 0


def test_input_order_does_not_matter(tmp_path):
    df = fixture_data(tmp_path)
    pd.testing.assert_frame_equal(build_features(df), build_features(df.sample(frac=1, random_state=2)))


def test_duplicate_ids_rejected(tmp_path):
    fixture_data(tmp_path)
    df = pd.read_csv(tmp_path/'results.csv', dtype={'game_id':str})
    pd.concat([df, df.iloc[:1]]).to_csv(tmp_path/'results.csv', index=False)
    with pytest.raises(ValueError, match='duplicate'):
        load_games(tmp_path)


def test_partition_excludes_unavailable_training_labels(tmp_path):
    df = build_features(fixture_data(tmp_path))
    df.loc[0, 'available_at'] = pd.Timestamp('2026-01-01', tz='UTC')
    parts = partition(df)
    assert df.loc[0, 'game_id'] not in set(parts['train'].game_id)
    assert set(parts['train'].game_id).isdisjoint(parts['tune'].game_id)


def test_bootstrap_identical_predictions(tmp_path):
    df = build_features(fixture_data(tmp_path))
    result = paired_interval(df, df.p_elo, df.p_elo, repetitions=50)
    assert result['difference'] == 0
    assert result['ci95'] == [0, 0]


def test_end_to_end_free_and_holdout_sealed(tmp_path):
    fixture_data(tmp_path)
    out = tmp_path/'run'
    fit_free(tmp_path, out, threads=1)
    report = read_json(out/'report.json')
    assert report['coverage']['unscored_games_at_or_after_2025_07_01'] > 0
    assert set(report['metrics']) >= {'home_rate', 'elo', 'logistic', 'boosted'}
    for name in ['features.csv', 'validation_predictions.csv']:
        frame = pd.read_csv(out/name)
        assert pd.to_datetime(frame.decision_at, utc=True).max() < pd.Timestamp('2025-07-01', tz='UTC')
    assert not (out/'test').exists()
    assert (out/'PASTE_BACK.md').exists()
    with pytest.raises(FileExistsError):
        fit_free(tmp_path, out)

