import json
import pandas as pd
import pytest
from sports_method import challenger as c
from sports_method import pair_monitor as m
from test_collect import CUTOFF
from test_challenger import setup_pair


def recorded_pair(tmp_path, monkeypatch):
    collection, baseline, pair = setup_pair(tmp_path)
    out = tmp_path/'paired'
    issue = CUTOFF-pd.Timedelta(minutes=2)
    monkeypatch.setattr(c, 'now', lambda: issue.isoformat())
    c.poll(collection, pair, baseline, tmp_path, out, record=True)
    return collection, out


def settle_dataset(tmp_path, dest, home_scores):
    games = pd.read_csv(tmp_path/'games.csv', dtype={'game_id': str})
    results = pd.read_csv(tmp_path/'results.csv', dtype={'game_id': str})
    template = games.iloc[0].to_dict()
    for i, score in enumerate(home_scores):
        home, away = ('A', 'B') if i == 0 else ('B', 'A')
        games.loc[len(games)] = {**template, 'game_id': f'PENDING{i:04d}',
                                 'home_id': home, 'away_id': away,
                                 'scheduled_at': str(CUTOFF+pd.Timedelta(hours=1)),
                                 'decision_at': str(CUTOFF),
                                 'schedule_observed_at': str(CUTOFF-pd.Timedelta(days=2))}
        results.loc[len(results)] = {'game_id': f'PENDING{i:04d}', 'home_score': score,
                                     'away_score': 100,
                                     'available_at': str(CUTOFF+pd.Timedelta(days=1))}
    dest.mkdir()
    games.to_csv(dest/'games.csv', index=False)
    results.to_csv(dest/'results.csv', index=False)
    return dest


def test_pair_status_tracks_missed_and_recorded(tmp_path, monkeypatch):
    collection, baseline, pair = setup_pair(tmp_path)
    out = tmp_path/'out'
    issue = CUTOFF-pd.Timedelta(minutes=2)
    after = CUTOFF+pd.Timedelta(hours=1)
    s = m.pair_status(collection, out, at=after)
    assert s['past_cutoffs'] == 2 and s['recorded'] == 0 and s['missed_games'] == 2
    assert len(s['missed']) == 2
    monkeypatch.setattr(c, 'now', lambda: issue.isoformat())
    c.poll(collection, pair, baseline, tmp_path, out, record=True)
    s = m.pair_status(collection, out, at=after)
    assert s['missed_games'] == 0 and s['recorded'] == 2
    assert s['report_states'].get('missing', 0) > 0 and s['both_usable'] == 0
    archive = tmp_path/'archive'
    archive.mkdir()
    (archive/'index.jsonl').write_text(json.dumps({
        'filename': 'r.pdf', 'capture': 'prospective', 'retrieved_at': str(issue),
        'sha256': 'x'})+'\n')
    s = m.pair_status(collection, out, archive=archive, at=after)
    assert s['archive']['prospective_files'] == 1
    assert s['archive']['eligible_last_48h'] == 1


def test_settlement_scores_without_touching_records(tmp_path, monkeypatch):
    collection, records = recorded_pair(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in (records/'recorded').glob('*.json')}
    data = settle_dataset(tmp_path, tmp_path/'rolled', home_scores=[110, 90])
    report = m.pair_evaluate(records, collection, data, tmp_path/'eval')
    assert report['mode'] == 'recorded' and report['snapshots'] == 2
    assert report['settled'] == 2 and report['awaiting_result'] == []
    assert set(report['models']) == {'p_injury', 'p_control', 'p_deployed'}
    for v in report['models'].values():
        assert v['games'] == 2 and 0 < v['log_loss'] < 5
        assert 0 <= v['ece_10bin'] <= 1 and v['calibration']
    assert 'injury_minus_control' in report['contrasts']
    assert report['coverage']['missed_games'] == 0
    after = {p.name: p.read_bytes() for p in (records/'recorded').glob('*.json')}
    assert before == after
    assert (tmp_path/'eval'/'report.json').exists()
    assert 'Primary' in (tmp_path/'eval'/'PASTE_BACK.md').read_text()
    with pytest.raises(FileExistsError):
        m.pair_evaluate(records, collection, data, tmp_path/'eval')


def test_settlement_reports_pending_and_tamper(tmp_path, monkeypatch):
    collection, records = recorded_pair(tmp_path, monkeypatch)
    report = m.pair_evaluate(records, collection, tmp_path, tmp_path/'eval0')
    assert report['settled'] == 0 and len(report['awaiting_result']) == 2
    assert 'models' not in report
    victim = next((records/'recorded').glob('*.json'))
    victim.rename(victim.with_name('0'*64+'.json'))
    with pytest.raises(ValueError, match='does not match'):
        m.pair_evaluate(records, collection, tmp_path, tmp_path/'eval1')


def test_simulated_scoring_is_labelled_rehearsal(tmp_path, monkeypatch):
    collection, baseline, pair = setup_pair(tmp_path)
    out = tmp_path/'paired'
    c.poll(collection, pair, baseline, tmp_path, out, at=CUTOFF-pd.Timedelta(minutes=2))
    data = settle_dataset(tmp_path, tmp_path/'rolled', home_scores=[110, 90])
    report = m.pair_evaluate(out, collection, data, tmp_path/'eval', include_simulated=True)
    assert report['mode'] == 'simulated'
    assert 'never evidence' in report['warning']
