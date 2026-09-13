import json
import numpy as np
import pandas as pd
import pytest
from sports_method.free_box import (BOX_FEATURES, EXTENDED, box_features, build_extended,
                                    compare_extension, load_box)
from sports_method.free_data import FEATURES, build_features, load_games
from sports_method.settle import merge_settled, settled_rows
from sports_method.io import read_json
from test_free import fixture_data


def season_raw(tmp_path, finals=40, include_unplayed=True, include_placeholder=True):
    """A cached ScheduleLeagueV2-shaped payload for a new season."""
    rows = []
    start = pd.Timestamp('2026-10-20T23:00:00Z')
    for i in range(finals):
        rows.append({'gameId': f'002260{i:04d}', 'homeTeam_teamId': 1610612737+(i % 3),
                     'awayTeam_teamId': 1610612740+(i % 2), 'homeTeam_teamName': f'Home{i%3}',
                     'awayTeam_teamName': f'Away{i%2}', 'gameDateTimeUTC': (start+pd.Timedelta(days=i)).isoformat(),
                     'gameStatusText': 'Final', 'isNeutral': False,
                     'homeTeam_score': 110+i % 5, 'awayTeam_score': 101})
    if include_unplayed:
        rows.append({'gameId': '0022609999', 'homeTeam_teamId': 1610612737, 'awayTeam_teamId': 1610612740,
                     'homeTeam_teamName': 'Home0', 'awayTeam_teamName': 'Away0',
                     'gameDateTimeUTC': (start+pd.Timedelta(days=200)).isoformat(),
                     'gameStatusText': '7:00 pm ET', 'isNeutral': False,
                     'homeTeam_score': None, 'awayTeam_score': None})
    if include_placeholder:
        rows.append({'gameId': '0022601229', 'homeTeam_teamId': 0, 'awayTeam_teamId': 0,
                     'homeTeam_teamName': None, 'awayTeam_teamName': None,
                     'gameDateTimeUTC': (start+pd.Timedelta(days=50)).isoformat(),
                     'gameStatusText': 'Final', 'isNeutral': True,
                     'homeTeam_score': 100, 'awayTeam_score': 99})
    raw = tmp_path/'season_raw'
    raw.mkdir(exist_ok=True)
    (raw/'schedule-2026-27.json').write_text(json.dumps(rows))
    return raw


def test_settled_rows_skips_unplayed_and_unassigned(tmp_path):
    games, results, skipped = settled_rows(season_raw(tmp_path))
    assert len(games) == len(results) == 40
    assert skipped['not_final'] == 1 and skipped['unassigned_teams'] == 1
    assert (pd.to_datetime(results.available_at, utc=True, format='mixed')
            > pd.to_datetime(games.scheduled_at, utc=True, format='mixed')).all()
    assert (pd.to_datetime(games.decision_at, utc=True, format='mixed')
            < pd.to_datetime(games.scheduled_at, utc=True, format='mixed')).all()


def test_merge_settled_appends_and_validates(tmp_path):
    fixture_data(tmp_path)
    base = tmp_path
    out = tmp_path/'merged'
    result = merge_settled(base, season_raw(tmp_path), out)
    assert result['added_games'] == 40
    assert result['total_games'] == result['base_games']+40
    merged = load_games(out)
    assert len(merged) == result['total_games']
    manifest = read_json(out/'manifest.json')
    assert manifest['validated_games'] == result['total_games']
    assert 'ASSUMED' in manifest['warning']
    with pytest.raises(FileExistsError):
        merge_settled(base, season_raw(tmp_path), out)


def test_merge_settled_is_idempotent(tmp_path):
    fixture_data(tmp_path)
    first = merge_settled(tmp_path, season_raw(tmp_path), tmp_path/'m1')
    again = merge_settled(tmp_path/'m1', season_raw(tmp_path), tmp_path/'m2')
    assert again['added_games'] == 0
    assert again['total_games'] == first['total_games']


def box_fixture(tmp_path, df):
    """Team logs matching the fixture games, with plausible box lines."""
    rng = np.random.default_rng(3)
    rows = []
    for game in df.itertuples():
        for team, pts, opp in ((game.home_id, game.home_score, game.away_score),
                               (game.away_id, game.away_score, game.home_score)):
            fga = 85+rng.integers(0, 15)
            rows.append({'GAME_ID': game.game_id, 'TEAM_ID': team, 'PTS': pts, 'FGA': fga,
                         'FGM': int(fga*.46), 'FG3M': 12+rng.integers(0, 8), 'FTA': 20+rng.integers(0, 10),
                         'OREB': 9+rng.integers(0, 5), 'TOV': 12+rng.integers(0, 6)})
    path = tmp_path/'team_logs.csv'
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_box_features_respect_availability(tmp_path):
    df = fixture_data(tmp_path)
    box = load_box(box_fixture(tmp_path, df))
    base = box_features(df, box)
    # Perturbing results that arrive later must not change earlier rows.
    changed = df.copy()
    cut = len(df)-60
    changed.loc[changed.index >= cut, 'home_score'] += 400
    changed.loc[changed.index >= cut, 'y'] = 1
    after = box_features(changed, box)
    pd.testing.assert_frame_equal(base.iloc[:cut-1], after.iloc[:cut-1])


def test_extended_frame_has_every_column(tmp_path):
    df = fixture_data(tmp_path)
    features = build_extended(df, load_box(box_fixture(tmp_path, df)))
    assert set(EXTENDED).issubset(features.columns)
    assert len(features) == len(build_features(df))
    assert not features[EXTENDED].isna().any().any()
    assert np.isfinite(features[EXTENDED].to_numpy()).all()


def test_missing_box_columns_rejected(tmp_path):
    df = fixture_data(tmp_path)
    path = box_fixture(tmp_path, df)
    frame = pd.read_csv(path).drop(columns=['TOV'])
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match='missing'):
        load_box(path)


def test_compare_extension_runs_and_refuses_overwrite(tmp_path):
    df = fixture_data(tmp_path)
    box = box_fixture(tmp_path, df)
    out = tmp_path/'box-compare'
    result = compare_extension(tmp_path, box, out, threads=1)
    report = read_json(out/'report.json')
    assert set(report['folds']) == {'2022-23', '2023-24', '2024-25'}
    assert set(report['pooled']) >= {'base', 'extended'}
    predictions = pd.read_csv(out/'2024-25-extended'/'validation_predictions.csv')
    assert pd.to_datetime(predictions.decision_at, utc=True).max() < pd.Timestamp('2025-07-01', tz='UTC')
    assert 'not confirmation' in (out/'PASTE_BACK.md').read_text()
    with pytest.raises(FileExistsError):
        compare_extension(tmp_path, box, out, threads=1)
