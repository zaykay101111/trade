import numpy as np
import pandas as pd
import pytest
from test_free import fixture_data
from sports_method.free_data import FEATURES, build_features
from sports_method.free_train import partition
from sports_method.free_ablate import GROUPS, variants, fit_variant, ablate_free
from sports_method.io import read_json
from sports_method.model import predict_logistic, calibrate


def test_groups_and_variants():
    assert sorted(sum(GROUPS.values(), [])) == sorted(FEATURES)
    assert len(variants()) == 7
    for group, removed in GROUPS.items():
        cols = variants()['without_'+group]
        assert set(cols).isdisjoint(removed)
        assert cols == [f for f in FEATURES if f not in removed]


def test_removed_features_cannot_change_fit(tmp_path):
    parts = partition(build_features(fixture_data(tmp_path)))
    train = pd.concat([parts['train'], parts['tune']])
    cal, val = parts['calibration'], parts['validation']
    cols = variants()['without_scoring']
    b, raw, p = fit_variant(train, cal, val, cols)
    changed = []
    for frame in (train, cal, val):
        frame = frame.copy()
        frame[GROUPS['scoring']] = 1000000.
        changed.append(frame)
    b2, raw2, p2 = fit_variant(*changed, cols)
    assert b == b2
    np.testing.assert_array_equal(p, p2)
    np.testing.assert_array_equal(raw, raw2)


def test_ablation_end_to_end_and_saved_model(tmp_path):
    fixture_data(tmp_path)
    out = tmp_path/'ablation'
    result = ablate_free(tmp_path, out)
    assert result['completed'] == 21
    r = read_json(out/'report.json')
    assert r['final_holdout'] == 'NOT SCORED'
    assert len(r['pooled']) == 7
    assert len({v['games'] for v in r['pooled'].values()}) == 1
    for fold in r['folds'].values():
        assert fold['variants']['full']['vs_full']['ci95'] == [0,0]
        assert fold['variants']['full']['mean_absolute_probability_change'] == 0
    features = pd.read_csv(out/'development_features.csv', dtype={'game_id': str})
    assert pd.to_datetime(features.decision_at, utc=True).max() < pd.Timestamp('2025-07-01', tz='UTC')
    child = out/'2024-25-without_scoring'
    bundle = read_json(child/'bundle.json')
    pred = pd.read_csv(child/'validation_predictions.csv', dtype={'game_id': str})
    x = features.set_index('game_id').loc[pred.game_id, bundle['features']].to_numpy()
    p = predict_logistic(bundle['logistic'], x, np.full(len(x), .5))
    np.testing.assert_allclose(calibrate(p, bundle['calibrator']), pred.p, atol=1e-12)
    with pytest.raises(FileExistsError):
        ablate_free(tmp_path, out)
