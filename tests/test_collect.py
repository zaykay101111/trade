import json
import numpy as np
import pandas as pd
import pytest
from sports_method.collect import (CREDIT_FLOOR, MIN_REFERENCE_BOOKS, build_reference, devig,
                                   due_polls, extract_quotes, forecast, initialise, match_events,
                                   pending_features, poll, status)
from sports_method.free_data import FEATURES, build_features, load_games
from sports_method.free_final import fit_candidate, final_partition
from sports_method.io import read_json, write_json, code_hash
from test_free import fixture_data

CUTOFF = pd.Timestamp('2026-10-20T23:00:00Z')


def settled_and_pending(tmp_path):
    settled = fixture_data(tmp_path)
    rows = []
    for i, (home, away) in enumerate((('A', 'B'), ('B', 'A'))):
        rows.append(dict(game_id=f'PENDING{i:04d}', home_id=home, away_id=away,
                         home_name='Alphas' if home == 'A' else 'Betas',
                         away_name='Betas' if home == 'A' else 'Alphas',
                         scheduled_at=CUTOFF+pd.Timedelta(hours=1),
                         decision_at=CUTOFF, schedule_observed_at=CUTOFF-pd.Timedelta(days=2),
                         is_neutral=False, neutral=0))
    return settled, pd.DataFrame(rows)


def test_placeholder_scores_cannot_reach_features(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    base = pending_features(settled, pending)
    flipped = pending.copy()
    out = pending_features(settled, flipped)
    pd.testing.assert_frame_equal(base[FEATURES], out[FEATURES])
    # A pending game must never enter another pending game's history.
    assert base.history_count_diff.nunique() <= len(base)
    assert not base[FEATURES].isna().any().any()


def test_pending_rows_must_not_be_settled(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    clash = pending.copy()
    clash['game_id'] = settled.game_id.iloc[0]
    with pytest.raises(ValueError, match='already have settled results'):
        pending_features(settled, clash)


def test_devig_and_reference():
    fair = devig(2.0, 2.0)
    assert fair['q_home'] == pytest.approx(.5)
    assert fair['overround'] == pytest.approx(0)
    juiced = devig(1.9091, 1.9091)
    assert juiced['overround'] > .04
    assert juiced['q_home'] == pytest.approx(.5)
    for bad in ((1.0, 2.0), (2.0, float('nan')), (0.5, 2.0)):
        with pytest.raises(ValueError):
            devig(*bad)
    quotes = [{'book': b, **devig(1.9, 2.0)} for b in ('alpha', 'beta', 'gamma', 'draftkings')]
    ref = build_reference(quotes, 'draftkings')
    assert ref['books_used'] == 3 and ref['abstain_reason'] is None
    assert 0 < ref['reference_q_home'] < 1
    thin = build_reference(quotes[:2]+[{'book': 'draftkings', **devig(1.9, 2.0)}], 'draftkings')
    assert thin['reference_q_home'] is None and thin['books_used'] < MIN_REFERENCE_BOOKS


def test_match_events_quarantines_rather_than_guessing(tmp_path):
    _, pending = settled_and_pending(tmp_path)
    games = pending.assign(scheduled_at=pending.scheduled_at)
    events = [
        {'id': 'ok', 'home_team': 'Anytown Alphas', 'away_team': 'Bigcity Betas',
         'commence_time': CUTOFF.isoformat()},
        {'id': 'unknown', 'home_team': 'Somewhere Gammas', 'away_team': 'Bigcity Betas',
         'commence_time': CUTOFF.isoformat()},
        {'id': 'far', 'home_team': 'Anytown Alphas', 'away_team': 'Bigcity Betas',
         'commence_time': (CUTOFF+pd.Timedelta(days=9)).isoformat()},
    ]
    matched, quarantine = match_events(events, games)
    assert [m[1]['id'] for m in matched] == ['ok']
    assert {q['event_id'] for q in quarantine} == {'unknown', 'far'}
    assert all(q['reason'] for q in quarantine)


def test_extract_quotes_skips_one_sided_books():
    event = {'home_team': 'Anytown Alphas', 'away_team': 'Bigcity Betas', 'bookmakers': [
        {'key': 'alpha', 'last_update': '2026-10-20T22:58:00Z', 'markets': [
            {'key': 'h2h', 'outcomes': [{'name': 'Anytown Alphas', 'price': 1.8},
                                        {'name': 'Bigcity Betas', 'price': 2.1}]}]},
        {'key': 'partial', 'markets': [
            {'key': 'h2h', 'outcomes': [{'name': 'Anytown Alphas', 'price': 1.8}]}]},
        {'key': 'other_market', 'markets': [{'key': 'spreads', 'outcomes': []}]},
    ]}
    rows = extract_quotes(event)
    assert [r['book'] for r in rows] == ['alpha']
    assert rows[0]['book_last_update'] == '2026-10-20T22:58:00Z'
    assert 0 < rows[0]['q_home'] < 1


def bundle_for(tmp_path):
    """A frozen bundle in the shape collect.forecast expects."""
    df = fixture_data(tmp_path)
    parts = final_partition(build_features(df))
    fitted = fit_candidate({k: parts[k] for k in ('train', 'tune', 'calibration')}, 1)
    run = tmp_path/'bundle'
    run.mkdir()
    write_json(run/'bundle.json', {'features': FEATURES, 'logistic': fitted['logistic'],
                                   'calibrators': fitted['calibrators'], 'home_rate': fitted['home_rate'],
                                   'code_sha256': code_hash()})
    return run


def collection_for(tmp_path, pending):
    schedule = tmp_path/'schedule.csv'
    pending.drop(columns=['neutral']).to_csv(schedule, index=False)
    return initialise(schedule, tmp_path/'collection', '2026-27')['collection']


def fake_payload(books=4):
    def fetcher():
        bookmakers = [{'key': f'book{i}', 'last_update': '2026-10-20T22:58:00Z', 'markets': [
            {'key': 'h2h', 'outcomes': [{'name': 'Anytown Alphas', 'price': 1.85+.02*i},
                                        {'name': 'Bigcity Betas', 'price': 2.05}]}]} for i in range(books)]
        bookmakers.append({'key': 'draftkings', 'last_update': '2026-10-20T22:59:00Z', 'markets': [
            {'key': 'h2h', 'outcomes': [{'name': 'Anytown Alphas', 'price': 1.95},
                                        {'name': 'Bigcity Betas', 'price': 2.0}]}]})
        events = [{'id': 'evt0', 'home_team': 'Anytown Alphas', 'away_team': 'Bigcity Betas',
                   'commence_time': (CUTOFF+pd.Timedelta(hours=1)).isoformat(),
                   'bookmakers': bookmakers}]
        return events, {'x-requests-remaining': '480', 'x-requests-used': '20', 'x-requests-last': '1'}
    return fetcher


def test_dry_run_makes_no_request_and_records_no_quotes(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)

    def explode():
        raise AssertionError('dry run must not call the provider')

    result = poll(collection, bundle, tmp_path, at=CUTOFF, execute=False, fetcher=explode)
    assert result['games'] == 2 and 'dry run' in result['status']
    assert not (tmp_path/'collection'/'quotes.csv').exists()
    assert not list((tmp_path/'collection'/'raw').glob('*.json'))


def test_poll_records_forecasts_quotes_and_reference(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)
    ledger = poll(collection, bundle, tmp_path, at=CUTOFF, execute=True, fetcher=fake_payload())
    assert ledger['games_matched'] == 1 and ledger['quarantined'] == 0
    assert ledger['credits_remaining'] == '480'
    quotes = pd.read_csv(tmp_path/'collection'/'quotes.csv', dtype={'game_id': str})
    assert len(quotes) == 5
    assert quotes.book_last_update.notna().all() and quotes.retrieved_at.notna().all()
    reference = pd.read_csv(tmp_path/'collection'/'reference.csv', dtype={'game_id': str})
    assert reference.reference_q_home.notna().all()
    # The execution book is excluded from its own reference.
    assert int(reference.books_used.iloc[0]) == 4
    forecasts = pd.read_csv(tmp_path/'collection'/'forecasts.csv', dtype={'game_id': str})
    assert len(forecasts) == 2 and forecasts.p_model.between(0, 1).all()
    raw = json.loads(next((tmp_path/'collection'/'raw').glob('*.json')).read_text())
    assert raw['quota']['x-requests-remaining'] == '480'
    # No stake, EV or wager field is ever written.
    for frame in (quotes, reference, forecasts):
        assert not {c for c in frame.columns if any(k in c.lower() for k in ('stake', 'bet', 'wager', 'kelly', 'edge'))}


def test_repeat_poll_refused(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)
    poll(collection, bundle, tmp_path, at=CUTOFF, execute=True, fetcher=fake_payload())
    with pytest.raises(FileExistsError, match='already recorded'):
        poll(collection, bundle, tmp_path, at=CUTOFF, execute=True, fetcher=fake_payload())


def test_late_poll_targets_nothing(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)
    late = poll(collection, bundle, tmp_path, at=CUTOFF+pd.Timedelta(minutes=45),
                execute=True, fetcher=fake_payload())
    assert late['games'] == 0 and 'no games' in late['status']
    assert not (tmp_path/'collection'/'quotes.csv').exists()


def test_thin_coverage_abstains_and_low_credits_warn(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)

    def thin():
        events, quota = fake_payload(books=1)()
        return events, {**quota, 'x-requests-remaining': str(CREDIT_FLOOR-1)}

    ledger = poll(collection, bundle, tmp_path, at=CUTOFF, execute=True, fetcher=thin)
    assert ledger['references_with_enough_books'] == 0
    assert 'warning' in ledger
    reference = pd.read_csv(tmp_path/'collection'/'reference.csv')
    assert reference.abstain_reason.notna().all()


def test_forecast_refuses_drifted_bundle(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    bundle = bundle_for(tmp_path)
    features = pending_features(settled, pending)
    good = forecast(bundle, features)
    assert len(good) == 2
    drifted = read_json(bundle/'bundle.json')
    drifted['code_sha256'] = '0'*64
    write_json(bundle/'bundle.json', drifted)
    with pytest.raises(ValueError, match='Source changed'):
        forecast(bundle, features)


def test_status_and_due_polls(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    bundle = bundle_for(tmp_path)
    assert due_polls(collection, CUTOFF) and not due_polls(collection, CUTOFF+pd.Timedelta(hours=3))
    before = status(collection)
    assert before['executed_polls'] == 0 and 'no expected value' in before['warning'].lower()
    poll(collection, bundle, tmp_path, at=CUTOFF, execute=True, fetcher=fake_payload())
    after = status(collection)
    assert after['executed_polls'] == 1 and after['games_matched'] == 1
    assert after['forecasts_issued'] == 2 and after['latest_credits_remaining'] in ('480', 480)


def test_release_bundle_fits_without_scoring(tmp_path):
    from sports_method.collect import release
    fixture_data(tmp_path)
    out = tmp_path/'release'
    result = release(tmp_path, out, train_end='2024-07-01', tune_end='2025-01-01',
                     calibration_end='2025-07-01', threads=1, label='test release')
    bundle = read_json(out/'bundle.json')
    assert bundle['features'] == FEATURES and bundle['l2'] == .01
    assert bundle['code_sha256'] == code_hash()
    assert set(bundle['split_counts']) == {'train', 'tune', 'calibration'}
    text = (out/'RELEASE.md').read_text()
    assert 'no season was scored' in text.lower()
    # A release must not emit any metric that could be read as evaluation.
    assert not any(k in bundle for k in ('metrics', 'log_loss', 'brier', 'accuracy'))
    with pytest.raises(FileExistsError):
        release(tmp_path, out, train_end='2024-07-01', tune_end='2025-01-01',
                calibration_end='2025-07-01', threads=1)
    with pytest.raises(ValueError, match='strictly increasing'):
        release(tmp_path, tmp_path/'bad', train_end='2025-01-01', tune_end='2024-07-01',
                calibration_end='2025-07-01', threads=1)


def test_code_drift_is_refused_then_recorded(tmp_path):
    settled, pending = settled_and_pending(tmp_path)
    bundle = bundle_for(tmp_path)
    features = pending_features(settled, pending)
    drifted = read_json(bundle/'bundle.json')
    drifted['code_sha256'] = '0'*64
    write_json(bundle/'bundle.json', drifted)
    with pytest.raises(ValueError, match='freeze a new bundle'):
        forecast(bundle, features)
    recorded = forecast(bundle, features, allow_code_drift=True)
    assert recorded.code_drift.all()
    assert (recorded.bundle_code_sha256 == '0'*64).all()
    assert (recorded.code_sha256_at_issue == code_hash()).all()
