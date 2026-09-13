import pytest

from sports_method import agents

SOURCE = [{"url": "https://example.org/report", "retrieved_at": "2026-09-13T18:00:00Z"}]


def test_annotation_requires_sourced_evidence(tmp_path):
    store = tmp_path/"notes.jsonl"
    record = agents.annotate(store, kind="evidence", subject="2026_01_GB_MIN",
                             body={"claim": "stadium roof closed"}, sources=SOURCE,
                             agent="scout")
    assert record["adopted"] is False
    assert agents.read(store)[0]["subject"] == "2026_01_GB_MIN"
    with pytest.raises(ValueError, match="at least one source"):
        agents.annotate(store, kind="evidence", subject="x", body={"claim": "y"},
                        sources=[], agent="scout")
    with pytest.raises(ValueError, match="url and a retrieved_at"):
        agents.annotate(store, kind="evidence", subject="x", body={"claim": "y"},
                        sources=[{"url": "https://example.org"}], agent="scout")


@pytest.mark.parametrize("key", ["p_home", "probability", "odds", "stake", "kelly",
                                 "ev", "edge_estimate", "bet_size"])
def test_agents_cannot_carry_forecast_or_stake_fields(tmp_path, key):
    with pytest.raises(ValueError, match="may not carry"):
        agents.annotate(tmp_path/"n.jsonl", kind="scenario", subject="g",
                        body={key: 0.6}, sources=SOURCE, agent="debater")


def test_adoption_cannot_be_self_asserted(tmp_path):
    with pytest.raises(ValueError, match="measured improvement"):
        agents.annotate(tmp_path/"n.jsonl", kind="quality", subject="runs/x",
                        body={"flag": "stale"}, sources=SOURCE, agent="critic",
                        adopted=True)


def test_unknown_kind_rejected_and_summary_counts(tmp_path):
    store = tmp_path/"notes.jsonl"
    with pytest.raises(ValueError, match="Unknown annotation kind"):
        agents.annotate(store, kind="forecast", subject="g", body={"a": 1},
                        sources=SOURCE, agent="a")
    for kind in ("evidence", "quality", "narrative"):
        agents.annotate(store, kind=kind, subject="g", body={"note": kind},
                        sources=SOURCE, agent="a")
    report = agents.summarise(store)
    assert report["annotations"] == 3 and report["adopted"] == 0
    assert report["by_kind"]["quality"] == 1
