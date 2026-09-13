"""Ingestion checks against a REAL saved provider payload.

The existing collect tests use synthetic events. These run the same code over a
payload actually returned by the-odds-api on 2026-09-13, so provider-shape
regressions (renamed fields, missing last_update, one-sided books) are caught.

No network access: the payload is read from data/raw/odds-live-*/events.json,
which was saved with its retrieval time, quota and SHA-256. Tests skip if no
payload has been captured in this checkout.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from sports_method.collect import (MIN_REFERENCE_BOOKS, build_reference, devig,
                                   extract_quotes, match_events)

ROOT = Path(__file__).parents[1]


def load_payload():
    captures = sorted((ROOT/"data"/"raw").glob("odds-live-*/events.json"))
    if not captures:
        pytest.skip("no saved live odds payload in this checkout")
    return json.loads(captures[-1].read_text()), captures[-1].parent


@pytest.fixture
def payload():
    return load_payload()[0]


def test_saved_payload_matches_its_recorded_hash():
    import hashlib
    events, folder = load_payload()
    meta = json.loads((folder/"source.json").read_text())
    raw = (folder/"events.json").read_text().rstrip("\n")
    assert hashlib.sha256(raw.encode()).hexdigest() == meta["sha256"]
    # Provenance that makes a later T-60 claim auditable at all.
    assert meta["retrieved_at"] and meta["quota"]["x-requests-remaining"]
    assert meta["credits_cost"] == 1


def test_devig_is_proportional_and_normalised(payload):
    for event in payload:
        for quote in extract_quotes(event):
            u_home = 1/quote["home_price"]
            u_away = 1/quote["away_price"]
            expected = u_home/(u_home+u_away)
            assert quote["q_home"] == pytest.approx(expected)
            assert quote["overround"] == pytest.approx(u_home+u_away-1)
            # A real two-way book always prices above fair.
            assert 0 < quote["q_home"] < 1
            assert quote["overround"] > 0


def test_execution_book_never_enters_its_own_reference(payload):
    checked = 0
    for event in payload:
        quotes = extract_quotes(event)
        books = {q["book"] for q in quotes}
        for execution in books:
            reference = build_reference(quotes, execution)
            others = [q for q in quotes if q["book"] != execution]
            assert reference["books_used"] == len(others)
            if reference["reference_q_home"] is None:
                assert len(others) < MIN_REFERENCE_BOOKS
                assert reference["abstain_reason"]
                continue
            checked += 1
            assert reference["reference_q_home"] == pytest.approx(
                float(np.median(sorted(q["q_home"] for q in others))))
    if not checked:
        pytest.skip("payload too thin for any non-abstaining reference")


def test_thin_coverage_abstains_with_a_recorded_reason(payload):
    """Most events this far from tip have one book; those must abstain."""
    abstained = 0
    for event in payload:
        quotes = extract_quotes(event)
        reference = build_reference(quotes, "draftkings")
        if reference["reference_q_home"] is None:
            abstained += 1
            assert reference["abstain_reason"]
    assert abstained > 0, "expected thin pre-season coverage to trigger abstention"


def test_every_quote_carries_the_books_own_timestamp(payload):
    """book_last_update is the provider's time; our retrieval time is separate."""
    for event in payload:
        for quote in extract_quotes(event):
            assert quote["book_last_update"], "a quote without the book's own time is unusable"


def test_real_events_map_to_canonical_ids_or_quarantine(payload):
    import pandas as pd
    schedule = ROOT/"collection"/"2026-27"/"schedule.csv"
    if not schedule.exists():
        pytest.skip("no 2026-27 collection in this checkout")
    games = pd.read_csv(schedule, dtype={"game_id": str})
    matched, quarantine = match_events(payload, games)
    assert len(matched)+len(quarantine) == len(payload), "every event is matched or quarantined"
    assert len({game_id for game_id, _ in matched}) == len(matched), "no game matched twice"
    for entry in quarantine:
        assert entry["reason"], "a quarantined event must record why"


def test_unknown_team_is_quarantined_not_guessed(payload):
    import pandas as pd
    schedule = ROOT/"collection"/"2026-27"/"schedule.csv"
    if not schedule.exists():
        pytest.skip("no 2026-27 collection in this checkout")
    games = pd.read_csv(schedule, dtype={"game_id": str})
    fake = dict(payload[0])
    fake["home_team"] = "Springfield Isotopes"
    fake["id"] = "fabricated"
    matched, quarantine = match_events([fake], games)
    assert not matched
    assert quarantine[0]["reason"] == "no schedule match"


def test_devig_rejects_impossible_prices():
    for bad in ((1.0, 2.0), (2.0, 1.0), (0.5, 2.0), (float("nan"), 2.0)):
        with pytest.raises(ValueError):
            devig(*bad)
