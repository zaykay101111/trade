import json
import pandas as pd
import pytest
from sports_method import challenger as c
from sports_method.io import write_json, digest, now
from sports_method.free_data import FEATURES
from test_collect import settled_and_pending, collection_for, bundle_for, CUTOFF


def setup_pair(tmp_path):
    _, pending = settled_and_pending(tmp_path)
    collection = collection_for(tmp_path, pending)
    baseline = bundle_for(tmp_path)
    model = json.loads((baseline/'bundle.json').read_text())
    spec = {'features': FEATURES, 'logistic': model['logistic'],
            'calibrator': model['calibrators']['logistic']}
    pair = tmp_path/'pair'
    write_json(pair/'bundle.json', {'surface': c.surface(), 'created_at': '2026-01-01T00:00:00Z',
               'baseline_sha256': digest(baseline/'bundle.json'), 'team_lookup': {},
               'models': {'control': spec, 'injury': spec}})
    return collection, baseline, pair


def test_simulation_missing_and_repeat(tmp_path):
    collection, baseline, pair = setup_pair(tmp_path)
    out = tmp_path/'paired'
    result = c.poll(collection, pair, baseline, tmp_path, out, at=CUTOFF-pd.Timedelta(minutes=2))
    assert result['games'] == 2 and result['both_usable'] == 0
    assert result['network_requests'] == 0
    files = list((out/'simulated').glob('*.json'))
    payload = json.loads(files[0].read_text())
    assert payload['mode'] == 'simulation'
    assert payload['features']['home_missing'] == 1
    assert set(payload['predictions']) == {'p_deployed', 'p_control', 'p_injury'}
    assert not (out/'recorded').exists()
    assert c.poll(collection, pair, baseline, tmp_path, out, at=CUTOFF)['games'] == 0
    assert c.poll(collection, pair, baseline, tmp_path, out, at=CUTOFF+pd.Timedelta(seconds=1))['games'] == 0


def test_no_backdating_or_drift(tmp_path):
    collection, baseline, pair = setup_pair(tmp_path)
    with pytest.raises(ValueError, match='backdate'):
        c.poll(collection, pair, baseline, tmp_path, tmp_path/'out', at=CUTOFF, record=True)
    path = pair/'bundle.json'
    b = json.loads(path.read_text())
    b['surface']['injury'] = 'changed'
    write_json(path, b)
    with pytest.raises(ValueError, match='drifted'):
        c.poll(collection, pair, baseline, tmp_path, tmp_path/'out', at=CUTOFF)


def test_record_and_late_completion(tmp_path, monkeypatch):
    collection, baseline, pair = setup_pair(tmp_path)
    issue = CUTOFF-pd.Timedelta(minutes=2)
    monkeypatch.setattr(c, 'now', lambda: issue.isoformat())
    out = tmp_path/'out'
    assert c.poll(collection, pair, baseline, tmp_path, out, record=True)['mode'] == 'prospective'
    assert len(list((out/'recorded').glob('*.json'))) == 2
    times = iter([issue.isoformat(), (CUTOFF+pd.Timedelta(seconds=1)).isoformat()])
    monkeypatch.setattr(c, 'now', lambda: next(times))
    with pytest.raises(ValueError, match='crossed T-60'):
        c.poll(collection, pair, baseline, tmp_path, tmp_path/'late', record=True)
    assert not (tmp_path/'late').exists()


def test_archive_timestamp_and_hash_gates(tmp_path, monkeypatch):
    archive = tmp_path/'archive'
    (archive/'pdf').mkdir(parents=True)
    pdf = archive/'pdf'/'report.pdf'
    pdf.write_bytes(b'%PDF test fixture')
    entry = {'filename': pdf.name, 'capture': 'prospective',
             'retrieved_at': str(CUTOFF-pd.Timedelta(minutes=5)), 'sha256': digest(pdf)}
    def save(e):
        (archive/'index.jsonl').write_text(json.dumps(e)+'\n')
    save({**entry, 'capture': 'backfill'})
    assert c.captured_reports(archive, CUTOFF)[0].empty
    save({**entry, 'retrieved_at': str(CUTOFF)})
    assert c.captured_reports(archive, CUTOFF)[0].empty
    save({**entry, 'sha256': 'bad'})
    with pytest.raises(ValueError, match='hash mismatch'):
        c.captured_reports(archive, CUTOFF)
    save(entry)
    monkeypatch.setattr(c.injury, 'parse_report', lambda p: pd.DataFrame({
        'report_at': [CUTOFF-pd.Timedelta(minutes=10)], 'status': ['Out']}))
    rows, sources = c.captured_reports(archive, CUTOFF)
    assert len(rows) == 1 and len(sources) == 1
    monkeypatch.setattr(c.injury, 'parse_report', lambda p: pd.DataFrame({'report_at': [CUTOFF]}))
    with pytest.raises(ValueError, match='after retrieval'):
        c.captured_reports(archive, CUTOFF)


def test_observation_after_issue_rejected(tmp_path):
    collection, baseline, pair = setup_pair(tmp_path)
    path = pd.read_csv(str(collection)+'/schedule.csv')
    path['schedule_observed_at'] = str(CUTOFF)
    path.to_csv(str(collection)+'/schedule.csv', index=False)
    with pytest.raises(ValueError, match='observation'):
        c.poll(collection, pair, baseline, tmp_path, tmp_path/'out',
               at=CUTOFF-pd.Timedelta(minutes=1))


def test_freeze_matches_windows_and_ignores_later_labels(tmp_path, monkeypatch):
    _, baseline, _ = setup_pair(tmp_path)
    reports = tmp_path/'reports.csv'
    reports.write_text('placeholder\n1\n')
    write_json(str(reports)+'.manifest.json', {'csv_sha256': digest(reports),
                                             'parser_sha256': digest(c.injury.__file__)})
    team = tmp_path/'teams.csv'
    team.write_text('fixture\n')
    monkeypatch.setattr(c.injury, 'team_lookup', lambda path: {})
    def extra(games, reports, lookup):
        frame = c.availability(games, pd.DataFrame(), lookup)
        frame['availability_covered'] = 1
        frame['home_missing'] = frame['away_missing'] = 0
        return frame
    monkeypatch.setattr(c.injury, 'availability_frame', extra)
    baseline_hash = digest(baseline/'bundle.json')
    c.freeze(tmp_path, reports, team, baseline, tmp_path/'frozen')
    b = json.loads((tmp_path/'frozen'/'bundle.json').read_text())
    assert len(b['models']['injury']['features']) == 25
    assert len(b['models']['control']['features']) == 11
    assert 'metrics' not in b and digest(baseline/'bundle.json') == baseline_hash
    results = pd.read_csv(tmp_path/'results.csv', dtype={'game_id': str})
    later = pd.to_datetime(results.available_at, utc=True) >= pd.Timestamp('2025-07-01', tz='UTC')
    results.loc[later, 'home_score'] = 200
    results.to_csv(tmp_path/'results.csv', index=False)
    c.freeze(tmp_path, reports, team, baseline, tmp_path/'frozen2')
    b2 = json.loads((tmp_path/'frozen2'/'bundle.json').read_text())
    assert b['models'] == b2['models']
    with pytest.raises(FileExistsError):
        c.freeze(tmp_path, reports, team, baseline, tmp_path/'frozen')
    reports.write_text('changed\n1\n')
    with pytest.raises(ValueError, match='drifted'):
        c.freeze(tmp_path, reports, team, baseline, tmp_path/'frozen3')


def test_baseline_artifact_change_rejected(tmp_path):
    collection, baseline, pair = setup_pair(tmp_path)
    path = baseline/'bundle.json'
    path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError, match='Baseline bundle changed'):
        c.poll(collection, pair, baseline, tmp_path, tmp_path/'out', at=CUTOFF)
