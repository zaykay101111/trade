import numpy as np
import pandas as pd
import pytest
from test_free import fixture_data
from sports_method.model import fit_logistic
from sports_method.free_data import build_features, FEATURES
from sports_method.free_train import partition
from sports_method.free_regularize import select_penalty, regularize_free, PENALTIES
from sports_method.io import read_json


def test_default_preserved_and_shrinkage(tmp_path):
    df = partition(build_features(fixture_data(tmp_path)))['train']
    x, y, q = df[FEATURES].to_numpy(), df.y.to_numpy(), np.full(len(df), .5)
    original = fit_logistic(x,y,q)
    assert original == fit_logistic(x,y,q,l2=.01)
    strong = fit_logistic(x,y,q,l2=1.)
    assert np.linalg.norm(strong['coef'][1:]) <= np.linalg.norm(original['coef'][1:])
    for bad in (-1, float('inf'), float('nan')):
        with pytest.raises(ValueError, match='L2'):
            fit_logistic(x,y,q,l2=bad)


def test_selection_uses_only_tuning(tmp_path):
    parts = partition(build_features(fixture_data(tmp_path)))
    selected, trials = select_penalty(parts['train'], parts['tune'])
    assert tuple(t['l2'] for t in trials) == PENALTIES
    assert selected == min(trials,key=lambda t:(t['tune_log_loss'],-t['l2']))['l2']
    parts['validation']['y'] = 1-parts['validation']['y']
    assert (selected,trials) == select_penalty(parts['train'], parts['tune'])


def test_regularization_end_to_end(tmp_path):
    fixture_data(tmp_path)
    out = tmp_path/'regularize'
    regularize_free(tmp_path, out)
    r = read_json(out/'report.json')
    assert r['final_holdout'] == 'NOT SCORED' and len(r['folds']) == 3
    assert r['pooled']['fixed']['games'] == r['pooled']['selected']['games']
    for fold in r['folds'].values():
        assert fold['selected_l2'] in PENALTIES
        assert fold['models']['fixed']['l2'] == .01
    for p in out.glob('*/validation_predictions.csv'):
        df = pd.read_csv(p)
        assert pd.to_datetime(df.decision_at,utc=True).max() < pd.Timestamp('2025-07-01',tz='UTC')
    assert (out/'PASTE_BACK.md').exists()
    with pytest.raises(FileExistsError): regularize_free(tmp_path, out)
