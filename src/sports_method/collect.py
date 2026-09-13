"""Prospective T-60 collection: frozen-model forecasts beside live market quotes.

COLLECTION ONLY. This module computes no expected value, no stake, no admission
decision and no wager. It records what a forecast was and what prices existed at
the moment the forecast was made, with the book's own update time and our
retrieval time stored separately, so a later evaluation can establish that a
price was observed rather than assumed.

Records are append-only. Raw payloads are kept verbatim. Nothing here reads a
game's outcome: pending games carry placeholder scores whose availability is set
to the far future, so the point-in-time feature builder can never reveal them.
"""
import json
import os
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import numpy as np
import pandas as pd
from .free_data import FEATURES, build_features, load_games
from .model import predict_logistic, calibrate
from .io import read_json, write_json, now, code_hash, digest

LIVE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
MARKET = "h2h"
DEFAULT_REGIONS = "us"
MIN_REFERENCE_BOOKS = 3
# Pandas nanosecond timestamps top out in 2262; this is far beyond any decision
# time while staying representable.
FAR_FUTURE = pd.Timestamp("2200-01-01", tz="UTC")
# Free tier is 500 credits per month; stop well before exhaustion.
CREDIT_FLOOR = 25
# NBA Cup knockout rows ship with team id 0 and no arena until the bracket is set.
PLACEHOLDER_TEAM = "0"


def _parse_times(frame, columns):
    """Parse timestamp columns tolerantly.

    A schedule may be rewritten by different tools, mixing "...T01:00:00+00:00"
    and "... 01:00:00+00:00" in one file; a single strict format would fail.
    """
    for column in columns:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True, format="mixed")
    return frame


def _ts(value):
    return pd.Timestamp(value, tz="UTC") if pd.Timestamp(value).tzinfo is None else pd.Timestamp(value)


def pending_features(settled, pending):
    """Features for unplayed games, using only results already available.

    Placeholder scores are attached to pending rows because the shared feature
    builder expects them; their availability is set to the year 2200 so no
    pending row can ever enter another row's history. Perturbing those
    placeholders cannot change any feature (see tests).
    """
    if pending.empty:
        raise ValueError("No pending games supplied")
    overlap = set(pending.game_id) & set(settled.game_id)
    if overlap:
        raise ValueError(f"{len(overlap)} pending games already have settled results")
    frame = pending.copy()
    frame["home_score"] = 1.
    frame["away_score"] = 0.
    frame["y"] = 1
    frame["available_at"] = FAR_FUTURE
    combined = pd.concat([settled, frame], ignore_index=True, sort=False)
    combined = combined.sort_values(["decision_at", "game_id"]).reset_index(drop=True)
    features = build_features(combined)
    out = features[features.game_id.isin(set(pending.game_id))].copy()
    if len(out) != len(pending):
        raise ValueError("Pending feature rows do not match pending games")
    return out.drop(columns=["y"]).reset_index(drop=True)


def forecast(bundle_dir, features, *, allow_code_drift=False):
    """Apply a frozen bundle. Parameters are never refitted here.

    Source drift halts forecasting by default. Mid-season an unrelated edit
    should not silently change what a "frozen" forecast means, so the override
    is explicit and is recorded on every row it produces.
    """
    bundle = read_json(Path(bundle_dir)/"bundle.json")
    if bundle["features"] != FEATURES:
        raise ValueError("Feature schema differs from the frozen bundle")
    drift = bundle.get("code_sha256") != code_hash()
    if drift and not allow_code_drift:
        raise ValueError("Source changed since the bundle was frozen; freeze a new bundle "
                         "or pass allow_code_drift to record the drift explicitly")
    raw = predict_logistic(bundle["logistic"], features[FEATURES].to_numpy(), np.full(len(features), .5))
    return pd.DataFrame({"game_id": features.game_id.to_numpy(),
                         "decision_at": features.decision_at.to_numpy(),
                         "p_model_raw": raw,
                         "p_model": calibrate(raw, bundle["calibrators"]["logistic"]),
                         "p_elo": features.p_elo.to_numpy(),
                         "bundle_code_sha256": bundle.get("code_sha256"),
                         "code_sha256_at_issue": code_hash(),
                         "code_drift": bool(drift)})


def devig(home_price, away_price):
    """Proportional de-vig of one book's two-sided quote. Estimate, not truth."""
    for price in (home_price, away_price):
        if not np.isfinite(price) or price <= 1:
            raise ValueError("Decimal prices must be finite and above 1")
    u_home, u_away = 1/home_price, 1/away_price
    total = u_home+u_away
    return {"q_home": u_home/total, "overround": total-1}


def build_reference(quotes, execution_book):
    """Median de-vigged home probability across books, excluding the execution book.

    Books are not independent opinions; the median limits outlier influence and
    creates no independent samples. Abstains below MIN_REFERENCE_BOOKS.
    """
    usable = [q for q in quotes if q["book"] != execution_book]
    if len(usable) < MIN_REFERENCE_BOOKS:
        return {"reference_q_home": None, "books_used": len(usable),
                "abstain_reason": f"fewer than {MIN_REFERENCE_BOOKS} reference books"}
    values = sorted(q["q_home"] for q in usable)
    return {"reference_q_home": float(np.median(values)), "books_used": len(usable),
            "spread": float(values[-1]-values[0]),
            "mean_overround": float(np.mean([q["overround"] for q in usable])),
            "abstain_reason": None}


def _token(name):
    return str(name).strip().lower().split()[-1] if str(name).strip() else ""


def match_events(events, games):
    """Map provider events to canonical game IDs, or quarantine them.

    Matches on last-token team names plus a commence time within a day of the
    scheduled start. Ambiguous or unmatched events are quarantined, never guessed.
    """
    index = {}
    for game in games.itertuples():
        index.setdefault((_token(game.home_name), _token(game.away_name)), []).append(game)
    matched, quarantine = [], []
    for event in events:
        key = (_token(event.get("home_team")), _token(event.get("away_team")))
        candidates = index.get(key, [])
        if not candidates:
            quarantine.append({"reason": "no schedule match", "event_id": event.get("id"),
                               "home_team": event.get("home_team"), "away_team": event.get("away_team"),
                               "commence_time": event.get("commence_time")})
            continue
        commence = _ts(event["commence_time"])
        near = [g for g in candidates if abs((_ts(g.scheduled_at)-commence).total_seconds()) <= 86400]
        if len(near) != 1:
            quarantine.append({"reason": f"{len(near)} schedule candidates within a day",
                               "event_id": event.get("id"), "home_team": event.get("home_team"),
                               "away_team": event.get("away_team"), "commence_time": event.get("commence_time")})
            continue
        matched.append((near[0].game_id, event))
    return matched, quarantine


def extract_quotes(event):
    """One de-vigged record per book offering both sides of the moneyline."""
    rows = []
    for book in event.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != MARKET:
                continue
            prices = {o.get("name"): o.get("price") for o in market.get("outcomes", [])}
            home, away = prices.get(event.get("home_team")), prices.get(event.get("away_team"))
            if home is None or away is None:
                continue
            try:
                fair = devig(float(home), float(away))
            except ValueError:
                continue
            rows.append({"book": book.get("key"), "home_price": float(home), "away_price": float(away),
                         "book_last_update": book.get("last_update") or market.get("last_update"),
                         **fair})
    return rows


def fetch_live(regions, api_key=None, timeout=45):
    """One live request. Costs markets x regions credits. Key never logged."""
    key = api_key or os.environ.get("ODDS_API_KEY")
    if not key:
        raise ValueError("Set ODDS_API_KEY in the environment; never paste it into reports")
    params = {"apiKey": key, "regions": regions, "markets": MARKET, "oddsFormat": "decimal"}
    try:
        with urlopen(Request(LIVE_URL+"?"+urlencode(params), headers={"Accept": "application/json"}), timeout=timeout) as response:
            body = json.load(response)
            quota = {k: response.headers.get(k) for k in
                     ("x-requests-remaining", "x-requests-used", "x-requests-last")}
    except (HTTPError, URLError) as exc:
        raise RuntimeError("Quote request failed; HTTP status "+str(getattr(exc, "code", "network"))
                           + "; request URL suppressed to protect key") from None
    return body, quota


def _append(path, rows):
    if not rows:
        return
    frame = pd.DataFrame(rows)
    frame.to_csv(path, mode="a", header=not Path(path).exists(), index=False)


def split_schedule(games):
    """Separate fully specified games from rows awaiting team assignment.

    NBA Cup knockout games are published with team id 0 and no arena until the
    bracket is decided, and roughly thirty further games are unscheduled at
    release. Forecasting either would corrupt ratings, so they are held aside
    and added by `refresh` once the NBA assigns them.
    """
    ids = games[["home_id", "away_id"]].astype(str)
    unassigned = (ids.home_id == PLACEHOLDER_TEAM) | (ids.away_id == PLACEHOLDER_TEAM)
    for column in ("home_name", "away_name"):
        if column in games:
            unassigned |= games[column].astype(str).str.strip().isin(("", "None", "nan", "TBD"))
    same = ids.home_id == ids.away_id
    if (same & ~unassigned).any():
        raise ValueError("Schedule contains a game with identical team IDs")
    return games[~unassigned].copy(), games[unassigned].copy()


def _poll_times(games):
    return [pd.Timestamp(t).isoformat() for t in sorted(games.decision_at.unique())]


def initialise(schedule_csv, out, season):
    """Create a collection directory from a season schedule. No network access."""
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"Collection exists: {out}; choose a new directory")
    games = _parse_times(pd.read_csv(schedule_csv, dtype={"game_id": str, "home_id": str, "away_id": str}),
                         ("scheduled_at", "decision_at", "schedule_observed_at"))
    if games.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs in schedule")
    usable, pending = split_schedule(games)
    if usable.empty:
        raise ValueError("No fully specified games in schedule")
    (out/"raw").mkdir(parents=True)
    usable.to_csv(out/"schedule.csv", index=False)
    if not pending.empty:
        pending.to_csv(out/"pending_assignment.csv", index=False)
    times = _poll_times(usable)
    write_json(out/"collection.json", {
        "created_at": now(), "season": season, "mode": "prospective_collection",
        "revision": 1, "games": len(usable), "awaiting_assignment": len(pending),
        "poll_times": times, "planned_polls": len(times), "market": MARKET,
        "estimated_credits_per_region": len(times),
        "schedule_sha256": digest(schedule_csv), "code_sha256": code_hash(),
        "warning": "Collection only: no expected value, stake, admission decision or "
                   "wager is computed or recorded by this workflow."})
    return {"collection": str(out), "games": len(usable),
            "awaiting_assignment": len(pending), "planned_polls": len(times),
            "estimated_credits_per_region": len(times),
            "note": "Rows awaiting team assignment are held in pending_assignment.csv; "
                    "run collect-refresh once the NBA assigns them."}


def refresh(collection, schedule_csv):
    """Fold an updated schedule into a collection without disturbing records.

    Adds newly assigned games, records start-time revisions, and never edits an
    executed poll. Already-recorded forecasts, quotes and ledger rows are
    immutable; only the forward plan changes.
    """
    collection = Path(collection)
    meta = read_json(collection/"collection.json")
    columns = ("scheduled_at", "decision_at", "schedule_observed_at")
    current = _parse_times(pd.read_csv(collection/"schedule.csv",
                                       dtype={"game_id": str, "home_id": str, "away_id": str}), columns)
    incoming = _parse_times(pd.read_csv(schedule_csv,
                                        dtype={"game_id": str, "home_id": str, "away_id": str}), columns)
    usable, pending = split_schedule(incoming)
    known = set(current.game_id)
    added = usable[~usable.game_id.isin(known)]
    revisions = []
    existing = current.set_index("game_id")
    for game in usable[usable.game_id.isin(known)].itertuples():
        before = existing.loc[game.game_id]
        if before.scheduled_at != game.scheduled_at:
            revisions.append({"game_id": game.game_id, "field": "scheduled_at",
                              "before": before.scheduled_at.isoformat(),
                              "after": game.scheduled_at.isoformat(), "observed_at": now()})
    withdrawn = current[~current.game_id.isin(set(usable.game_id))]
    merged = pd.concat([current[current.game_id.isin(set(usable.game_id))].drop(columns=[]),
                        added], ignore_index=True)
    merged = merged.drop(columns=["scheduled_at", "decision_at"]).merge(
        usable[["game_id", "scheduled_at", "decision_at"]], on="game_id", validate="one_to_one")
    merged = merged.sort_values(["decision_at", "game_id"]).reset_index(drop=True)
    merged.to_csv(collection/"schedule.csv", index=False)
    if not pending.empty:
        pending.to_csv(collection/"pending_assignment.csv", index=False)
    elif (collection/"pending_assignment.csv").exists():
        (collection/"pending_assignment.csv").unlink()
    _append(collection/"schedule_revisions.csv", revisions)
    for row in withdrawn.itertuples():
        _append(collection/"schedule_revisions.csv", [{"game_id": row.game_id, "field": "withdrawn",
            "before": row.scheduled_at.isoformat(), "after": "", "observed_at": now()}])
    times = _poll_times(merged)
    meta.update({"revision": meta.get("revision", 1)+1, "games": len(merged),
                 "awaiting_assignment": len(pending), "poll_times": times,
                 "planned_polls": len(times), "estimated_credits_per_region": len(times),
                 "schedule_sha256": digest(schedule_csv), "refreshed_at": now()})
    write_json(collection/"collection.json", meta)
    return {"collection": str(collection), "revision": meta["revision"], "games": len(merged),
            "added": len(added), "start_time_revisions": len(revisions),
            "withdrawn": len(withdrawn), "awaiting_assignment": len(pending),
            "planned_polls": len(times),
            "note": "Executed polls, forecasts and quotes are untouched."}


def due_polls(collection, at, window_minutes=5):
    """Planned poll times inside the tolerance window around `at`."""
    meta = read_json(Path(collection)/"collection.json")
    at = _ts(at)
    window = pd.Timedelta(minutes=window_minutes)
    return [t for t in meta["poll_times"] if abs((_ts(t)-at).total_seconds()) <= window.total_seconds()]


def poll(collection, bundle_dir, data, *, at=None, regions=DEFAULT_REGIONS,
         execution_book="draftkings", execute=False, fetcher=None, window_minutes=5,
         allow_code_drift=False):
    """One collection cycle: forecast pending games, record quotes, write records."""
    collection = Path(collection)
    meta = read_json(collection/"collection.json")
    at = _ts(now() if at is None else at)
    schedule = _parse_times(pd.read_csv(collection/"schedule.csv",
                                        dtype={"game_id": str, "home_id": str, "away_id": str}),
                            ("scheduled_at", "decision_at", "schedule_observed_at"))
    targets = schedule[(schedule.decision_at-at).abs() <= pd.Timedelta(minutes=window_minutes)].copy()
    if targets.empty:
        return {"poll_id": None, "status": "no games at this cutoff", "games": 0}
    # Identify the poll by the cutoff it serves. A scheduler firing every few
    # minutes hits the same window repeatedly; keying on wall-clock time would
    # buy the same snapshot twice.
    served_path = collection/"served_cutoffs.csv"
    served = set()
    if served_path.exists():
        served = set(pd.read_csv(served_path).cutoff.astype(str))
    targets["cutoff"] = targets.decision_at.map(lambda t: pd.Timestamp(t).isoformat())
    outstanding = targets[~targets.cutoff.isin(served)]
    if outstanding.empty:
        return {"poll_id": None, "status": "cutoff already served; records are append-only",
                "games": 0, "cutoffs_already_served": sorted(set(targets.cutoff))}
    targets = outstanding
    poll_id = min(targets.cutoff).replace(":", "").replace("+", "_")
    settled = load_games(data)
    pending = targets.copy()
    pending["neutral"] = pending.is_neutral.astype(str).str.lower().isin(("true", "1")).astype(int)
    features = pending_features(settled, pending)
    forecasts = forecast(bundle_dir, features, allow_code_drift=allow_code_drift)
    forecasts.insert(0, "poll_id", poll_id)
    forecasts["issued_at"] = at.isoformat()
    forecasts["bundle"] = str(bundle_dir)
    if not execute:
        _append(collection/"forecasts_dry_run.csv", forecasts.to_dict("records"))
        return {"poll_id": poll_id, "status": "dry run: forecasts written, no request made",
                "games": len(forecasts), "would_cost_credits": len(regions.split(","))}
    if (collection/"raw"/f"{poll_id}.json").exists():
        raise FileExistsError(f"Poll {poll_id} already recorded; records are append-only "
                              "and a repeat request would spend credits twice")
    body, quota = (fetcher or (lambda: fetch_live(regions)))()
    remaining = quota.get("x-requests-remaining")
    write_json(collection/"raw"/f"{poll_id}.json",
               {"retrieved_at": at.isoformat(), "regions": regions, "quota": quota, "body": body})
    matched, quarantine = match_events(body, targets)
    quote_rows, reference_rows = [], []
    for game_id, event in matched:
        quotes = extract_quotes(event)
        for q in quotes:
            quote_rows.append({"poll_id": poll_id, "game_id": game_id, "retrieved_at": at.isoformat(),
                               "provider_event_id": event.get("id"),
                               "commence_time": event.get("commence_time"), **q})
        reference_rows.append({"poll_id": poll_id, "game_id": game_id, "retrieved_at": at.isoformat(),
                               "execution_book": execution_book, "books_offered": len(quotes),
                               **build_reference(quotes, execution_book)})
    _append(collection/"forecasts.csv", forecasts.to_dict("records"))
    _append(collection/"quotes.csv", quote_rows)
    _append(collection/"reference.csv", reference_rows)
    for row in quarantine:
        row.update({"poll_id": poll_id, "retrieved_at": at.isoformat()})
    _append(collection/"quarantine.csv", quarantine)
    _append(served_path, [{"cutoff": c, "poll_id": poll_id, "executed_at": at.isoformat()}
                          for c in sorted(set(targets.cutoff))])
    ledger = {"poll_id": poll_id, "cutoffs_served": len(set(targets.cutoff)),
              "planned_at": min(targets.cutoff), "executed_at": at.isoformat(),
              "seconds_late": round((at-pd.Timestamp(min(targets.cutoff))).total_seconds(), 1), "regions": regions, "events_returned": len(body),
              "games_targeted": len(targets), "games_matched": len(matched),
              "quarantined": len(quarantine), "quotes_recorded": len(quote_rows),
              "references_with_enough_books": sum(r["reference_q_home"] is not None for r in reference_rows),
              "credits_last": quota.get("x-requests-last"), "credits_used": quota.get("x-requests-used"),
              "credits_remaining": remaining}
    _append(collection/"polls.csv", [ledger])
    if remaining is not None and str(remaining).isdigit() and int(remaining) < CREDIT_FLOOR:
        ledger["warning"] = f"Only {remaining} credits remain; pause collection before exhausting the quota"
    return ledger


def status(collection):
    """Coverage and quota summary. Reads recorded files only."""
    collection = Path(collection)
    meta = read_json(collection/"collection.json")
    report = {"collection": str(collection), "season": meta["season"],
              "planned_polls": meta["planned_polls"], "games_in_schedule": meta["games"],
              "warning": meta["warning"]}
    polls_path = collection/"polls.csv"
    if not polls_path.exists():
        report.update({"executed_polls": 0, "note": "No executed poll recorded yet."})
        return report
    polls = pd.read_csv(polls_path)
    report.update({"executed_polls": len(polls),
                   "completion_rate": round(len(polls)/meta["planned_polls"], 4),
                   "games_matched": int(polls.games_matched.sum()),
                   "games_targeted": int(polls.games_targeted.sum()),
                   "match_rate": round(float(polls.games_matched.sum()/max(1, polls.games_targeted.sum())), 4),
                   "quarantined": int(polls.quarantined.sum()),
                   "quotes_recorded": int(polls.quotes_recorded.sum()),
                   "references_with_enough_books": int(polls.references_with_enough_books.sum()),
                   "latest_credits_remaining": polls.credits_remaining.dropna().iloc[-1]
                   if polls.credits_remaining.notna().any() else None})
    if (collection/"forecasts.csv").exists():
        forecasts = pd.read_csv(collection/"forecasts.csv", dtype={"game_id": str})
        report["forecasts_issued"] = len(forecasts)
        report["distinct_games_forecast"] = int(forecasts.game_id.nunique())
    return report


def release(data, out, *, train_end, tune_end, calibration_end, threads=2, label="release"):
    """Fit the frozen recipe for deployment. No evaluation, no held-out season.

    Same eleven features, lambda 0.01, sigmoid calibration and secondary boosted
    trees as every other fit in this project, and the same fold shape: train,
    tune, refit on train+tune, calibrate on a later disjoint slice. It produces a
    bundle to forecast with; it scores nothing and must not be read as evidence.
    """
    import platform
    import sklearn
    import xgboost as xgb
    from .free_final import CANDIDATE, PENALTY, fit_candidate
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"Release exists: {out}; choose a new directory")
    stamps = [_ts(v) for v in (train_end, tune_end, calibration_end)]
    if sorted(stamps) != stamps or len(set(stamps)) != 3:
        raise ValueError("Release boundaries must be strictly increasing")
    raw = load_games(data)
    features = build_features(raw)
    parts, lower = {}, features.decision_at.min()
    for name, upper in (("train", stamps[0]), ("tune", stamps[1]), ("calibration", stamps[2])):
        part = features[(features.decision_at >= lower) & (features.decision_at < upper)]
        part = part[part.available_at < upper]
        if len(part) < 30 or part.y.nunique() != 2:
            raise ValueError(f"{name}: need at least 30 games and both outcomes")
        parts[name] = part
        lower = upper
    fitted = fit_candidate(parts, threads)
    out.mkdir(parents=True)
    write_json(out/"bundle.json", {
        "mode": "deployment_release", "label": label, "features": FEATURES,
        "logistic": fitted["logistic"], "home_rate": fitted["home_rate"],
        "calibrators": fitted["calibrators"], "selected_params": fitted["selected_params"],
        "l2": PENALTY, "candidate": CANDIDATE, "refit_games": fitted["refit_games"],
        "boundaries": {"train": str(train_end), "tune": str(tune_end),
                       "calibration": str(calibration_end)},
        "split_counts": {k: len(v) for k, v in parts.items()},
        "created_at": now(), "code_sha256": code_hash(),
        "data_sha256": {f: digest(Path(data)/f) for f in ("games.csv", "results.csv")},
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "pandas": pd.__version__, "sklearn": sklearn.__version__,
                     "xgboost": xgb.__version__}})
    write_json(out/"trials.json", fitted["trials"])
    (out/"RELEASE.md").write_text("\n".join([
        f"# Deployment release: {label}", "",
        "Fitted for prospective forecasting only. Nothing here is an evaluation:",
        "no season was scored, and no metric in this directory describes performance.",
        "", f"Boundaries: train < {train_end}; tune < {tune_end}; calibration < {calibration_end}",
        f"Split counts: {({k: len(v) for k, v in parts.items()})}",
        f"Refit games: {fitted['refit_games']}", f"Code sha256: {code_hash()}",
        "", "Forecasts issued from this bundle are recorded by the collection workflow,",
        "which computes no expected value, stake or wager.", ""]))
    return {"release": str(out), "split_counts": {k: len(v) for k, v in parts.items()},
            "refit_games": fitted["refit_games"], "code_sha256": code_hash(),
            "note": "Deployment bundle only; no season was scored."}
