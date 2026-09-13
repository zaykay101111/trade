import numpy as np
import pandas as pd
import pytest
from sports_method import player_impact as pi
from test_injury import frames


def test_normalize_name_handles_suffixes_and_accents():
    assert pi.normalize_name('Porter Jr., Michael') == 'michael porter jr'
    assert pi.normalize_name('da Silva, Tristan') == 'tristan da silva'
    assert pi.normalize_name("Dončić, Luka") == 'luka doncic'
    assert pi.normalize_name('Michael Porter Jr.') == 'michael porter jr'


def player_logs_for(games, player, team, minutes):
    rows = []
    for i, m in enumerate(minutes):
        rows.append({'GAME_ID': f'{i:010d}', 'PLAYER_NAME': player, 'TEAM_ID': team,
                     'MIN': m, 'PTS': m/2})
    return pd.DataFrame(rows)


def test_history_respects_result_availability():
    games, reports, cutoff = frames()
    hist_games = pd.DataFrame({
        'game_id': [f'{i:010d}' for i in range(3)],
        'available_at': [cutoff-pd.Timedelta(days=3), cutoff-pd.Timedelta(days=2),
                         cutoff+pd.Timedelta(hours=1)]})
    logs = player_logs_for(hist_games, 'John Smith', 'A', [30, 20, 40])
    history, joined = pi.player_history(logs, hist_games)
    assert joined == 3
    stats = pi.prior_stats(history, 'A', 'Smith, John', cutoff)
    # The 40-minute game is available only after the cutoff and must not count.
    assert stats == (25.0, 12.5)
    assert pi.prior_stats(history, 'A', 'Smith, John', cutoff-pd.Timedelta(days=10)) is None
    assert pi.prior_stats(history, 'B', 'Smith, John', cutoff) is None


def test_impact_frame_weights_and_unmatched():
    games, reports, cutoff = frames()
    reports = reports.copy()
    reports['player'] = ['Smith, John', 'Jones, Jane', 'Smith, John',
                         'Away, Player', 'Smith, John', 'Jones, Jane']
    reports['source'] = 'one.pdf'
    lookup = {'TeamA': 'A', 'TeamB': 'B'}
    hist_games = pd.DataFrame({'game_id': ['0000000000'],
                               'available_at': [cutoff-pd.Timedelta(days=2)]})
    listed = reports[reports.status.isin(pi.STATUSES)]
    player = listed[listed.team == 'TeamA'].player.iloc[0]
    status = listed[listed.team == 'TeamA'].status.iloc[0]
    logs = player_logs_for(hist_games, pi.normalize_name(player).title(), 'A', [36])
    frame = pi.impact_frame(games, reports, lookup, logs, history_games=hist_games)
    row = frame.iloc[0]
    assert row[f'{status.lower()}_minutes_diff'] == pytest.approx(36)
    # Away listed players have no logs: unmatched, contributing zero minutes.
    assert row.unmatched_listed_diff < 0
    assert frame.attrs['matched_listed_players'] == 1
    assert set(pi.IMPACT_FEATURES).issubset(frame.columns)
