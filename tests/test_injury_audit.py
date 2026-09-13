import json
import pandas as pd
import pytest
from sports_method.injury import parse_lines, availability_counts, parse_to_csv
from test_injury import frames


def test_multiline_header_updates_context_and_multiword_names():
    rows = parse_lines([
        '01/05/2023 07:00 (ET) MEM@ORL Memphis Grizzlies Injury/Illness - Right Big Toe',
        'Bane, Desmond Out',
        'Orlando Magic da Silva, Tristan Questionable Injury',
        'Smith Jr., John Out Injury',
        '08:00 (ET) NOP@HOU New Orleans Pelicans Injury/Illness - Injury',
        'Louzada Silva, Marcos Out Not With Team',
        'Houston Rockets',
        'Jones, Bob Probable Injury',
    ])
    assert len(rows) == 5
    assert rows[0]['matchup'] == 'MEM@ORL' and rows[0]['game_date'] == '01/05/2023'
    assert rows[1]['player'] == 'da Silva, Tristan'
    assert rows[2]['team'] == 'Orlando Magic'
    assert rows[3]['player'] == 'Louzada Silva, Marcos'
    assert rows[3]['team'] == 'New Orleans Pelicans'
    assert rows[4]['matchup'] == 'NOP@HOU' and rows[4]['team'] == 'Houston Rockets'


def test_game_identity_before_recency():
    games, reports, cutoff = frames()
    other = reports.iloc[[2]].copy()
    other['game_date'] = '01/11/2026'
    other['report_at'] = cutoff-pd.Timedelta(minutes=5)
    other2 = other.copy(); other2['game_date']='01/10/2026';other2['matchup']='TeamC@TeamA'
    lookup={'TeamA':'A','TeamB':'B','TeamC':'C'}
    result=availability_counts(games,pd.concat([reports,other,other2]),lookup).iloc[0]
    assert result.home_out == 1 and result.home_state == 'usable'
    result=availability_counts(games,pd.concat([other,other2]),lookup).iloc[0]
    assert result.home_state == 'missing' and result.home_out == 0


def test_missing_stale_not_submitted_and_cutoff():
    games,reports,cutoff=frames();lookup={'TeamA':'A','TeamB':'B'}
    r=reports.iloc[[2,3]].copy()
    r.loc[r.team=='TeamA','report_at']=cutoff-pd.Timedelta(hours=49)
    r.loc[r.team=='TeamB','status']='NotSubmitted'
    a=availability_counts(games,r,lookup).iloc[0]
    assert a.home_state=='stale' and a.home_out==0
    assert a.away_state=='not_submitted' and a.away_notsubmitted==1
    assert not a.availability_covered
    r.report_at=cutoff
    a=availability_counts(games,r,lookup).iloc[0]
    assert a.home_state==a.away_state=='missing'


def test_duplicate_player_or_sources_invalid():
    games,reports,_=frames();r=reports.iloc[[2,2,3]].copy()
    r['player']=['Smith,John','Smith,John','Jones,Jane'];r['source']='one.pdf'
    a=availability_counts(games,r,{'TeamA':'A','TeamB':'B'}).iloc[0]
    assert a.home_state=='invalid' and a.home_out==0


def test_resume_refuses_pdf_or_csv_drift(tmp_path,monkeypatch):
    from sports_method import injury
    archive=tmp_path/'archive';(archive/'pdf').mkdir(parents=True)
    p=archive/'pdf'/'one.pdf';p.write_bytes(b'%PDF-stub')
    def fake(path):
        return pd.DataFrame([{'source':path.name,'team':'BostonCeltics','status':'Out'}])
    monkeypatch.setattr(injury,'parse_report',fake)
    out=tmp_path/'parsed.csv';parse_to_csv(archive,out)
    assert json.loads(out.with_suffix('.csv.manifest.json').read_text())['parser_version']==injury.PARSER_VERSION
    assert set(['pdf_sha256','capture','retrieved_at','parser_version']).issubset(pd.read_csv(out).columns)
    p.write_bytes(b'%PDF-changed')
    with pytest.raises(ValueError,match='PDFs changed'):parse_to_csv(archive,out)


def test_legacy_csv_cannot_silently_resume(tmp_path):
    archive=tmp_path/'archive';(archive/'pdf').mkdir(parents=True)
    (archive/'pdf'/'one.pdf').write_bytes(b'%PDF-stub')
    out=tmp_path/'legacy.csv';out.write_text('source\none.pdf\n')
    with pytest.raises(ValueError,match='Legacy'):parse_to_csv(archive,out)


def test_comparison_provenance_and_frozen_holdout(tmp_path):
    from test_free import fixture_data
    from sports_method import injury
    from sports_method.io import digest, write_json, read_json
    from pathlib import Path
    games=fixture_data(tmp_path)
    team_log=tmp_path/'teams.csv'
    pd.DataFrame([{'TEAM_ID':s,'TEAM_NAME':s,'TEAM_ABBREVIATION':s} for s in ('A','B')]).to_csv(team_log,index=False)
    rows=[]
    for g in games.itertuples():
        for team in (g.home_id,g.away_id):
            rows.append({'game_date':g.scheduled_at.tz_convert('America/New_York').strftime('%m/%d/%Y'),
                         'matchup':f'{g.away_id}@{g.home_id}','team':team,'player':'Test,Player','status':'Questionable',
                         'report_at':g.decision_at-pd.Timedelta(hours=2),'source':g.game_id+'.pdf',
                         'capture':'backfill','retrieved_at':'2026-09-13T00:00:00Z','pdf_sha256':'testhash',
                         'parser_version':injury.PARSER_VERSION})
    parsed=tmp_path/'reports.csv';pd.DataFrame(rows).to_csv(parsed,index=False)
    write_json(parsed.with_suffix('.csv.manifest.json'),{'csv_sha256':digest(parsed),'parser_sha256':digest(Path(injury.__file__))})
    out=tmp_path/'comparison';injury.compare_availability(tmp_path,parsed,team_log,out)
    report=read_json(out/'report.json')
    assert report['injury_provenance']['parsed_csv_sha256']==digest(parsed)
    assert report['injury_provenance']['team_log_sha256']==digest(team_log)
    selected=pd.read_csv(out/'selected_reports.csv')
    assert selected.home_state.eq('usable').all()
    assert pd.to_datetime(selected.decision_at,utc=True).max()<pd.Timestamp('2025-07-01',tz='UTC')
    assert selected.home_pdf_sha256.eq('testhash').all()
    assert report['coverage_rate']==1
