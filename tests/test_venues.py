import csv
import json
import pytest
from sports_method.venues import CORRECTIONS, correct_venues
from sports_method.io import digest


def fixture(tmp_path):
    source = tmp_path/'source'; source.mkdir(); (source/'raw').mkdir()
    rows = [{'game_id': gid, 'home_id': '1', 'away_id': '2', 'is_neutral': 'False', 'unchanged': 'original'} for gid in CORRECTIONS]
    rows.append(dict(rows[0], game_id='0022500001'))
    with (source/'games.csv').open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (source/'results.csv').write_text('preserved results\n')
    for year in ('22','23'):
        cache = [{'gameId':gid, 'arenaCity':city, 'isNeutral':False, 'homeTeam_teamId':1, 'awayTeam_teamId':2}
                 for gid,(city,_) in CORRECTIONS.items() if gid.startswith('002'+year)]
        (source/'raw'/f'schedule-20{year}-{int(year)+1}.json').write_text(json.dumps(cache))
    return source


def test_only_reviewed_flags_change(tmp_path):
    source = fixture(tmp_path); before = digest(source/'games.csv')
    out = tmp_path/'corrected'
    result = correct_venues(source, out)
    assert result['corrected'] == 6 and result['results_unchanged']
    assert digest(source/'games.csv') == before
    with (source/'games.csv').open() as f: original = list(csv.DictReader(f))
    with (out/'games.csv').open() as f: corrected = list(csv.DictReader(f))
    for a,b in zip(original, corrected):
        expected = dict(a)
        if a['game_id'] in CORRECTIONS: expected['is_neutral']='True'
        assert b == expected
    with pytest.raises(FileExistsError): correct_venues(source, out)


def test_unexpected_cache_fails_before_writing(tmp_path):
    source = fixture(tmp_path)
    p = source/'raw'/'schedule-2022-23.json'
    rows = json.loads(p.read_text()); rows[0]['arenaCity']='wrong'; p.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match='Unexpected raw'): correct_venues(source, tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
