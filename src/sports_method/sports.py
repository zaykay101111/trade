"""Sport registry: the one shared seam between the NBA and NFL tracks.

Deliberately thin. It exists because two sports now need the same three things
resolved by name — a loader, a feature builder, and a market contract — and for
no other reason. Anything that only one sport needs stays in that sport's
module. This is not a framework and must not grow into one: add an entry only
when a second sport concretely needs the same call.

It lives outside the NBA forecast surface, so registering a sport cannot change
what a deployed NBA forecast means.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

NBA_CONTRACT = "nba_regular_fullgame_moneyline_ot"
NFL_CONTRACT = "nfl_regular_fullgame_moneyline_ot_tie_push"


@dataclass(frozen=True)
class Sport:
    key: str
    contract: str
    #: True when a regular-season game can end level, which decides whether a
    #: binary home-win model is a complete description of the outcome space.
    allows_ties: bool
    load: Callable
    features: Callable
    feature_names: tuple


def _nba():
    from .free_data import FEATURES, build_features, load_games
    return Sport("nba", NBA_CONTRACT, False, load_games, build_features, tuple(FEATURES))


def _nfl():
    from .nfl_data import NFL_FEATURES, build_nfl_features, load_nfl_games
    return Sport("nfl", NFL_CONTRACT, True, load_nfl_games, build_nfl_features,
                 tuple(NFL_FEATURES))


REGISTRY = {"nba": _nba, "nfl": _nfl}


def get(key):
    key = str(key).lower()
    if key not in REGISTRY:
        raise ValueError(f"Unknown sport {key!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[key]()


def detect(data):
    """Infer a dataset's sport from its own declarations, never from its path.

    NFL datasets carry explicit sport/contract columns. NBA datasets predate
    the multi-sport work and carry neither, so an absent declaration means NBA
    — which keeps every existing NBA dataset valid without rewriting it.
    """
    import pandas as pd
    path = Path(data)/"games.csv"
    if not path.exists():
        raise FileNotFoundError(f"No games.csv under {data}")
    header = pd.read_csv(path, nrows=1)
    if "sport" in header.columns:
        return get(str(header.sport.iloc[0]))
    if "contract" in header.columns and str(header.contract.iloc[0]).startswith("nfl_"):
        return get("nfl")
    return get("nba")
