"""Pins the frozen NBA forecast surface against multi-sport refactoring.

The package-wide code_hash legitimately drifts as research modules are added;
the NARROW forecast surface must not. Every issued NBA artifact below records
the surface it was produced under, and those recordings must keep matching the
live code. If one of these fails, a change touched free_data/model/collect/io
and either the change belongs in a NEW versioned release or it must be undone —
never update the stored hash to make this pass.
"""
import json
from pathlib import Path
import pytest
from sports_method.io import forecast_surface_hash, FORECAST_SURFACE

ROOT = Path(__file__).parents[1]
PINNED = [
    ("runs/release-2026-27-v2/bundle.json", "forecast_surface_sha256"),
]


@pytest.mark.parametrize("relative,key", PINNED)
def test_issued_nba_artifacts_still_match_the_live_surface(relative, key):
    path = ROOT/relative
    if not path.exists():
        pytest.skip(f"{relative} not present in this checkout")
    assert json.loads(path.read_text())[key] == forecast_surface_hash()


def test_injury_pair_release_surface_is_intact():
    path = ROOT/"runs"/"injury-pair-v1"/"bundle.json"
    if not path.exists():
        pytest.skip("injury-pair-v1 not present in this checkout")
    from sports_method import challenger
    assert json.loads(path.read_text())["surface"] == challenger.surface()


def test_forecast_surface_membership_is_deliberate():
    # Adding a sport must not enlarge the NBA forecast surface. A new sport's
    # modules belong outside it so its releases and NBA's cannot invalidate
    # each other.
    assert FORECAST_SURFACE == ("free_data.py", "model.py", "collect.py", "io.py")
    for name in FORECAST_SURFACE:
        assert (ROOT/"src"/"sports_method"/name).exists()
    assert not any("nfl" in name for name in FORECAST_SURFACE)
