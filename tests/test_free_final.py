import numpy as np
import pandas as pd
import pytest
from test_free import fixture_data
from sports_method.free_data import FEATURES, build_features
from sports_method.free_final import BOUNDARIES, final_partition, freeze_final, evaluate_final
from sports_method.free_train import fit_free
from sports_method.free_validate import fold_boundaries
from sports_method.model import predict_logistic, calibrate
from sports_method.io import read_json

HOLDOUT_START = pd.Timestamp(BOUNDARIES['calibration'], tz='UTC')


def test_holdout_features_ignore_later_results(tmp_path):
    """Leakage: perturbing later outcomes, holdout ones included, cannot move earlier rows."""
    df = fixture_data(tmp_path)
    original = build_features(df)
    changed = df.copy()
    cut = len(df)-80
    changed.loc[changed.index >= cut, 'home_score'] += 500
    changed.loc[changed.index >= cut, 'y'] = 1
    modified = build_features(changed)
    pd.testing.assert_frame_equal(original.loc[:cut-1, FEATURES+['p_elo']],
                                  modified.loc[:cut-1, FEATURES+['p_elo']])


def test_fitting_rows_respect_availability_and_are_disjoint(tmp_path):
    parts = final_partition(build_features(fixture_data(tmp_path)))
    previous = None
    for name, end in BOUNDARIES.items():
        boundary = pd.Timestamp(end, tz='UTC')
        assert parts[name].decision_at.max() < boundary
        if name != 'holdout':
            assert parts[name].available_at.max() < boundary
        if previous is not None:
            assert previous.decision_at.max() < parts[name].decision_at.min()
            assert set(previous.game_id).isdisjoint(parts[name].game_id)
        previous = parts[name]
    assert parts['holdout'].decision_at.min() >= HOLDOUT_START
    assert parts['calibration'].available_at.max() < HOLDOUT_START


def test_development_guards_remain_intact(tmp_path):
    fixture_data(tmp_path)
    with pytest.raises(ValueError, match='development seasons'):
        fold_boundaries(2025)
    bad = fold_boundaries(2024)
    bad['validation'] = '2026-07-01'
    with pytest.raises(ValueError, match='holdout'):
        fit_free(tmp_path, tmp_path/'nope', boundaries=bad)
    assert not (tmp_path/'nope').exists()


def test_evaluation_requires_explicit_confirmation(tmp_path):
    fixture_data(tmp_path)
    run = tmp_path/'final'
    freeze_final(tmp_path, run)
    with pytest.raises(ValueError, match='irreversible'):
        evaluate_final(run, threads=1)
    assert not (run/'HOLDOUT_CONSUMED.json').exists()
    assert not (run/'holdout').exists()


def test_dataset_or_code_drift_refused(tmp_path):
    fixture_data(tmp_path)
    run = tmp_path/'final'
    freeze_final(tmp_path, run)
    with (tmp_path/'games.csv').open('a') as handle:
        handle.write('\n')
    with pytest.raises(ValueError, match='differs from the frozen record'):
        evaluate_final(run, threads=1, confirmed=True)
    assert not (run/'HOLDOUT_CONSUMED.json').exists()


def test_freeze_dry_run_then_single_scored_use(tmp_path):
    fixture_data(tmp_path)
    run = tmp_path/'final'
    record = freeze_final(tmp_path, run)
    assert record['holdout'] == 'NOT SCORED' and record['reserved_holdout_games'] > 0
    frozen = read_json(run/'freeze.json')
    assert frozen['candidate']['l2'] == .01 and frozen['candidate']['features'] == FEATURES

    dry = evaluate_final(run, threads=1, dry_run=True)
    assert dry['holdout'] == 'NOT SCORED'
    assert not (run/'HOLDOUT_CONSUMED.json').exists()
    unscored = pd.read_csv(run/'dryrun'/'holdout_predictions_unscored.csv', dtype={'game_id': str})
    assert 'y' not in unscored.columns and len(unscored) == dry['holdout_games']
    dry_features = pd.read_csv(run/'dryrun'/'features.csv')
    assert pd.to_datetime(dry_features.decision_at, utc=True).max() < HOLDOUT_START

    result = evaluate_final(run, threads=1, confirmed=True)
    assert result['holdout'].startswith('SCORED')
    consumed = read_json(run/'HOLDOUT_CONSUMED.json')
    assert consumed['code_sha256'] == frozen['code_sha256']
    report = read_json(run/'holdout'/'report.json')
    assert set(report['primary']) == {'logistic_log_loss', 'logistic_minus_elo'}
    assert set(report['exploratory']['delays']) == {'24', '48'}
    assert report['replay_max_absolute_difference'] <= 1e-12

    scored = pd.read_csv(run/'holdout'/'holdout_predictions.csv', dtype={'game_id': str})
    assert len(scored) == result['holdout_games']
    assert pd.to_datetime(scored.decision_at, utc=True).min() >= HOLDOUT_START
    pd.testing.assert_series_equal(scored.game_id, unscored.game_id, check_names=False)

    # Saved-model replay from disk reproduces the recorded predictions.
    bundle = read_json(run/'holdout'/'bundle.json')
    features = pd.read_csv(run/'holdout'/'features.csv', dtype={'game_id': str})
    held = features[pd.to_datetime(features.decision_at, utc=True) >= HOLDOUT_START]
    replay = calibrate(predict_logistic(bundle['logistic'], held[FEATURES].to_numpy(),
                                        np.full(len(held), .5)), bundle['calibrators']['logistic'])
    assert np.max(np.abs(replay-scored.p_logistic.to_numpy())) <= 1e-12

    # The single use cannot be repeated in this run directory.
    with pytest.raises(FileExistsError):
        evaluate_final(run, threads=1, confirmed=True)
