import pandas as pd
import pytest
from sports_method.injury import (AVAILABILITY_FEATURES, COUNTED, availability_counts,
                                  availability_frame, parse_lines, report_time, team_lookup)

SPACED = [
    "Injury Report: 12/21/20 05:30 PM",
    "Game Date Game Time Matchup Team Player Name Current Status Reason",
    "12/22/2020 07:00 (ET) GSW@BKN Brooklyn Nets Claxton, Nicolas Out Injury/Illness - Right Knee",
    "Golden State Warriors Green, Draymond Out Injury/Illness - Right foot; soreness",
    "Porter Jr., Michael Out Injury/Illness - Low back",
    "10:00 (ET) LAC@LAL LA Clippers NOT YET SUBMITTED",
    "Page 1 of 1",
]
SQUASHED = [
    "Injury Report: 11/05/25 05:30 PM",
    "GameDate GameTime Matchup Team PlayerName CurrentStatus Reason",
    "11/05/2025 07:00(ET) BKN@IND BrooklynNets Highsmith,Haywood Out Injury/Illness-RightKnee",
    "Powell,Drake Out Injury/Illness-RightAnkle;Sprain",
    "IndianaPacers Dennis,RayJ Probable Injury/Illness-LowBack;Sprain",
    "PHI@CLE Philadelphia76ers Barlow,Dominick Out Injury/Illness-RightElbow",
    "Page1of8",
]


def test_both_layouts_parse():
    spaced = pd.DataFrame(parse_lines(SPACED))
    assert list(spaced.status) == ["Out", "Out", "Out", "NotSubmitted"]
    assert spaced.matchup.tolist() == ["GSW@BKN", "GSW@BKN", "GSW@BKN", "LAC@LAL"]
    # A spaced suffix must stay with the player, not become the team.
    porter = spaced[spaced.player.astype(str).str.startswith("Porter")].iloc[0]
    assert porter.player == "Porter Jr., Michael"
    assert porter.team == "Golden State Warriors"
    squashed = pd.DataFrame(parse_lines(SQUASHED))
    assert squashed.matchup.tolist() == ["BKN@IND"]*3+["PHI@CLE"]
    assert squashed.team.tolist() == ["BrooklynNets", "BrooklynNets", "IndianaPacers", "Philadelphia76ers"]


def test_not_submitted_is_distinct_from_no_injuries():
    rows = pd.DataFrame(parse_lines(SPACED))
    assert (rows.status == "NotSubmitted").sum() == 1
    assert rows[rows.status == "NotSubmitted"].player.isna().all()
    assert "NotSubmitted" in COUNTED


def test_report_time_is_eastern_converted_to_utc():
    stamp = report_time("Injury Report: 11/05/25 05:30 PM")
    assert stamp == pd.Timestamp("2025-11-05T22:30:00Z")
    assert report_time("no header here") is None


def build(games, reports):
    lookup = {"TeamA": "A", "TeamB": "B"}
    return availability_counts(games, reports, lookup)


def frames():
    cutoff = pd.Timestamp("2026-01-10T23:00:00Z")
    games = pd.DataFrame([{"game_id": "G1", "home_id": "A", "away_id": "B", "decision_at": cutoff}])
    reports = pd.DataFrame([
        {"team": "TeamA", "status": "Out", "report_at": cutoff-pd.Timedelta(hours=6)},
        {"team": "TeamA", "status": "Out", "report_at": cutoff-pd.Timedelta(hours=6)},
        {"team": "TeamA", "status": "Out", "report_at": cutoff-pd.Timedelta(hours=2)},
        {"team": "TeamB", "status": "Questionable", "report_at": cutoff-pd.Timedelta(hours=2)},
        {"team": "TeamA", "status": "Out", "report_at": cutoff+pd.Timedelta(minutes=30)},
        {"team": "TeamA", "status": "Out", "report_at": cutoff+pd.Timedelta(minutes=30)},
    ])
    return games, reports, cutoff


def test_only_the_latest_report_before_the_cutoff_is_used():
    games, reports, _ = frames()
    counts = build(games, reports)
    row = counts.iloc[0]
    # The 2-hour-prior report supersedes the 6-hour one; the later report is invisible.
    assert row.home_out == 1
    assert row.away_questionable == 1
    assert bool(row.availability_covered)


def test_reports_after_the_cutoff_never_count():
    games, reports, cutoff = frames()
    late = reports[reports.report_at > cutoff]
    counts = build(games, pd.concat([reports[reports.report_at < cutoff-pd.Timedelta(hours=5)], late]))
    assert counts.iloc[0].home_out == 2


def test_missing_report_is_flagged_not_assumed_healthy():
    games, reports, cutoff = frames()
    counts = build(games, reports[reports.report_at > cutoff])
    row = counts.iloc[0]
    assert row.home_out == 0 and row.away_out == 0
    assert not bool(row.availability_covered)


def test_availability_frame_shape():
    games, reports, _ = frames()
    frame = availability_frame(games, reports, {"TeamA": "A", "TeamB": "B"})
    assert set(AVAILABILITY_FEATURES).issubset(frame.columns)
    assert frame.out_diff.iloc[0] == 1
    assert frame.questionable_diff.iloc[0] == -1
    assert frame.attrs["coverage_rate"] == 1.0


def test_empty_reports_rejected():
    games, _, _ = frames()
    with pytest.raises(ValueError, match="No parsed injury rows"):
        availability_counts(games, pd.DataFrame(columns=["team", "status", "report_at"]), {})


def test_parse_to_csv_is_resumable(tmp_path, monkeypatch):
    """An interrupted parse continues; a completed one never reparses."""
    from sports_method import injury
    archive = tmp_path/'archive'
    (archive/'pdf').mkdir(parents=True)
    names = [f'Injury-Report_2025-11-0{i}_05PM.pdf' for i in range(1, 5)]
    for name in names:
        (archive/'pdf'/name).write_bytes(b'%PDF-1.4 stub')

    def fake_parse(path):
        frame = pd.DataFrame(parse_lines(SQUASHED))
        frame['report_at'] = pd.Timestamp('2025-11-05T22:30:00Z')
        frame['source'] = pd.Path(path).name if hasattr(pd, 'Path') else __import__('pathlib').Path(path).name
        return frame

    monkeypatch.setattr(injury, 'parse_report', fake_parse)
    out = tmp_path/'parsed.csv'
    first = injury.parse_to_csv(archive, out, limit=2)
    assert first['parsed_now'] == 2 and first['remaining'] == 2
    second = injury.parse_to_csv(archive, out)
    assert second['parsed_now'] == 2 and second['already_parsed'] == 2
    assert second['reports_in_csv'] == 4
    third = injury.parse_to_csv(archive, out)
    assert third['parsed_now'] == 0 and third['remaining'] == 0


def test_parse_to_csv_survives_a_bad_pdf(tmp_path, monkeypatch):
    from sports_method import injury
    archive = tmp_path/'archive'
    (archive/'pdf').mkdir(parents=True)
    for name in ('good.pdf', 'bad.pdf'):
        (archive/'pdf'/name).write_bytes(b'%PDF-1.4 stub')

    def flaky(path):
        if __import__('pathlib').Path(path).name == 'bad.pdf':
            raise RuntimeError('corrupt xref')
        frame = pd.DataFrame(parse_lines(SQUASHED))
        frame['report_at'] = pd.Timestamp('2025-11-05T22:30:00Z')
        frame['source'] = 'good.pdf'
        return frame

    monkeypatch.setattr(injury, 'parse_report', flaky)
    result = injury.parse_to_csv(archive, tmp_path/'p.csv')
    assert result['parsed_now'] == 1
    assert [f['source'] for f in result['failures']] == ['bad.pdf']


def test_no_pdfs_rejected(tmp_path):
    from sports_method.injury import parse_to_csv
    (tmp_path/'archive'/'pdf').mkdir(parents=True)
    with pytest.raises(ValueError, match='No PDFs'):
        parse_to_csv(tmp_path/'archive', tmp_path/'out.csv')
