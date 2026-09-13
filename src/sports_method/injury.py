"""Parse archived NBA injury report PDFs into typed availability rows.

Reads the archive produced by scripts/archive_injury_reports.py. Parsing is kept
separate from archiving so it can be re-run against an unchanged record.

Availability is joined to a game by taking the latest report whose own report
time is strictly before that game's decision cutoff, exactly the rule the feature
builder applies to results. A report published after the cutoff is never used,
and actual absence is never substituted for a declared status.
"""
import json
import re
from pathlib import Path
import pandas as pd

STATUSES = ("Out", "Doubtful", "Questionable", "Probable", "Available")
COUNTED = STATUSES+("NotSubmitted",)
HEADER = re.compile(r"Injury Report:\s*(\d{2}/\d{2}/\d{2})\s*(\d{1,2}:\d{2})\s*(AM|PM)", re.I)
# Two layouts exist. Reports up to roughly 2023 space their fields
# ("Brooklyn Nets", "Claxton, Nicolas", "07:00 (ET)"); later ones squash them
# ("BrooklynNets", "Claxton,Nicolas", "07:00(ET)"). Matching is anchored on the
# comma-bearing player name and the status keyword, so both parse identically.
STATUS_ALTERNATION = "|".join(STATUSES)
ROW = re.compile(
    r"^(?P<prefix>.*?)"
    # A surname may carry a spaced suffix ("Porter Jr., Michael"); without this
    # the suffix becomes the player and the surname is mistaken for a team.
    r"(?P<player>[A-Z][A-Za-z.'\-]+(?:\s+(?:Jr\.|Sr\.|II|III|IV))?,\s*[A-Za-z.'\- ]+?)\s+"
    r"(?P<status>" + STATUS_ALTERNATION + r")\b")
PREFIX = re.compile(
    r"^\s*(?:(?P<date>\d{2}/\d{2}/\d{4})\s+)?"
    r"(?:(?P<time>\d{1,2}:\d{2})\s*\(ET\)\s+)?"
    r"(?:(?P<matchup>[A-Z]{3}@[A-Z]{3})\s+)?"
    r"(?P<team>.*?)\s*$")
# A team that has filed nothing yet is not a team with nobody hurt.
NOT_SUBMITTED = re.compile(
    r"^(?P<prefix>.*?)NOT\s*YET\s*SUBMITTED\s*$", re.I)


def report_time(text):
    match = HEADER.search(text)
    if not match:
        return None
    stamp = pd.Timestamp(f"{match.group(1)} {match.group(2)} {match.group(3).upper()}")
    return stamp.tz_localize("America/New_York").tz_convert("UTC")


def _prefix_fields(prefix, current):
    parsed = PREFIX.match(prefix or "")
    if not parsed:
        return
    for key in ("date", "time", "matchup"):
        if parsed.group(key):
            current[key] = parsed.group(key)
    team = (parsed.group("team") or "").strip()
    if team:
        current["team"] = team


def parse_lines(lines):
    """Parse extracted text lines into availability rows. Layout-agnostic."""
    rows = []
    current = {"date": None, "time": None, "matchup": None, "team": None}
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("Game Date", "GameDate", "Injury Report:")) \
                or re.match(r"^Page\s*\d+\s*of\s*\d+$", line):
            continue
        blank = NOT_SUBMITTED.match(line)
        if blank:
            _prefix_fields(blank.group("prefix"), current)
            rows.append({"game_date": current["date"], "game_time_et": current["time"],
                         "matchup": current["matchup"], "team": current["team"],
                         "player": None, "status": "NotSubmitted"})
            continue
        match = ROW.match(line)
        if not match:
            continue
        _prefix_fields(match.group("prefix"), current)
        if not current["matchup"]:
            continue
        rows.append({"game_date": current["date"], "game_time_et": current["time"],
                     "matchup": current["matchup"], "team": current["team"],
                     "player": match.group("player").strip(), "status": match.group("status")})
    return rows


def parse_report(pdf_path):
    """Rows of (game, team, player, status) plus the report's own timestamp."""
    import pdfplumber
    lines, stamp = [], None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if stamp is None:
                stamp = report_time(text)
            lines.extend(text.splitlines())
    # One pass over the whole document: a game's rows continue across a page
    # break, so parsing page by page would drop every row before the next time
    # the matchup is printed.
    rows = parse_lines(lines)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["team"] = frame.team.astype(str).str.replace(" ", "", regex=False)
        frame["report_at"] = stamp
        frame["source"] = Path(pdf_path).name
    return frame


def parse_archive(archive, limit=None):
    """Parse every PDF in an archive directory, newest filename order last."""
    archive = Path(archive)
    index = {}
    index_path = archive/"index.jsonl"
    if index_path.exists():
        for line in index_path.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                index[record["filename"]] = record
    frames = []
    paths = sorted((archive/"pdf").glob("*.pdf"))
    for path in paths[:limit] if limit else paths:
        frame = parse_report(path)
        if frame.empty:
            continue
        record = index.get(path.name, {})
        frame["capture"] = record.get("capture", "unknown")
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["game_date", "matchup", "team", "player", "status",
                                     "report_at", "source", "capture"])
    return pd.concat(frames, ignore_index=True)


def team_lookup(team_log_csv):
    """Map the report's squashed team names and tricodes to canonical team IDs."""
    raw = pd.read_csv(team_log_csv, dtype={"TEAM_ID": str})
    lookup = {}
    for row in raw[["TEAM_ID", "TEAM_NAME", "TEAM_ABBREVIATION"]].drop_duplicates().itertuples():
        lookup[str(row.TEAM_NAME).replace(" ", "")] = str(row.TEAM_ID)
        lookup[str(row.TEAM_ABBREVIATION)] = str(row.TEAM_ID)
    return lookup


def availability_counts(games, reports, lookup):
    """Per game and side, counts by declared status from the latest usable report.

    'Latest usable' means the report whose own timestamp is strictly before the
    game's decision cutoff. Games with no such report get zero counts and are
    flagged, so absence of a report is never mistaken for a healthy roster.
    """
    if reports.empty:
        raise ValueError("No parsed injury rows supplied")
    reports = reports.dropna(subset=["report_at"]).copy()
    reports["team_id"] = reports.team.map(lookup)
    unmapped = reports.team_id.isna().sum()
    reports = reports.dropna(subset=["team_id"])
    reports["report_at"] = pd.to_datetime(reports.report_at, utc=True)
    output = []
    by_team = {team: frame.sort_values("report_at") for team, frame in reports.groupby("team_id")}
    for game in games.itertuples():
        row = {"game_id": game.game_id}
        covered = True
        for side, team in (("home", game.home_id), ("away", game.away_id)):
            frame = by_team.get(str(team))
            usable = frame[frame.report_at < game.decision_at] if frame is not None else None
            if usable is None or usable.empty:
                covered = False
                for status in COUNTED:
                    row[f"{side}_{status.lower()}"] = 0
                continue
            latest = usable[usable.report_at == usable.report_at.max()]
            counts = latest.status.value_counts()
            for status in COUNTED:
                row[f"{side}_{status.lower()}"] = int(counts.get(status, 0))
        row["availability_covered"] = covered
        output.append(row)
    frame = pd.DataFrame(output)
    frame.attrs["unmapped_team_rows"] = int(unmapped)
    return frame


def parse_to_csv(archive, out, limit=None, time_budget=None, chunk=50):
    """Parse an archive into one CSV, resumably.

    Already-parsed sources are skipped, so an interrupted run continues where it
    stopped and the command is safe to repeat. Parsing is separate from archiving
    so it can be re-run against an unchanged record after a parser fix.
    """
    import time
    # A missing parser is an environment problem, not a bad file: fail once, now,
    # rather than reporting the same error for every PDF in the archive.
    try:
        import pdfplumber  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required to parse injury reports; install it with "
                           "python -m pip install -e '.[pdf]'") from exc
    archive, out = Path(archive), Path(out)
    pdfs = sorted((archive/"pdf").glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"No PDFs under {archive/'pdf'}")
    done = set()
    if out.exists():
        done = set(pd.read_csv(out, usecols=["source"]).source.unique())
    todo = [p for p in pdfs if p.name not in done]
    if limit:
        todo = todo[:limit]
    started, buffer, failures, parsed = time.time(), [], [], 0
    for path in todo:
        try:
            frame = parse_report(path)
        except ImportError:                           # environment fault, never per-file
            raise
        except Exception as exc:                      # a malformed PDF must not lose prior work
            failures.append({"source": path.name, "error": str(exc)[:200]})
            continue
        if not frame.empty:
            buffer.append(frame)
            parsed += 1
        if len(buffer) >= chunk:
            pd.concat(buffer).to_csv(out, mode="a", header=not out.exists(), index=False)
            buffer = []
        if time_budget and time.time()-started > time_budget:
            break
    if buffer:
        pd.concat(buffer).to_csv(out, mode="a", header=not out.exists(), index=False)
    total = pd.read_csv(out, usecols=["source"]) if out.exists() else pd.DataFrame(columns=["source"])
    return {"parsed_now": parsed, "already_parsed": len(done), "remaining": len(pdfs)-len(done)-parsed,
            "reports_in_csv": int(total.source.nunique()), "rows_in_csv": len(total),
            "failures": failures, "out": str(out),
            "note": "Rerun to continue; parsed reports are never reparsed. Delete the CSV to reparse all."}

AVAILABILITY_FEATURES = ["out_diff", "doubtful_diff", "questionable_diff", "probable_diff",
                         "not_submitted_diff", "availability_covered"]


def availability_frame(games, reports, lookup):
    """Per-game home-minus-away status counts, plus a coverage indicator.

    Counts treat every listed player alike: this project has no player-level
    minutes or impact data, so a star and a two-way contract count the same. That
    is a real weakness of this feature group, not an oversight.
    """
    counts = availability_counts(games, reports, lookup)
    frame = pd.DataFrame({"game_id": counts.game_id})
    for status in COUNTED:
        key = status.lower()
        name = "not_submitted_diff" if status == "NotSubmitted" else f"{key}_diff"
        if status == "Available":
            continue
        frame[name] = counts[f"home_{key}"]-counts[f"away_{key}"]
    frame["availability_covered"] = counts.availability_covered.astype(int)
    frame.attrs["coverage_rate"] = float(counts.availability_covered.mean())
    frame.attrs["unmapped_team_rows"] = counts.attrs.get("unmapped_team_rows", 0)
    return frame


def compare_availability(data, parsed_csv, team_log, out, threads=2):
    """Base features versus base plus availability, on the development folds."""
    from .free_box import _fit
    from .free_data import FEATURES, build_features, load_games
    from .free_train import metrics, paired_interval, partition, WARNING
    from .free_validate import YEARS, fold_boundaries
    from .io import new_dir, write_json, digest, code_hash, now
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new run directory")
    frame = load_games(data)
    dev = frame[frame.decision_at < pd.Timestamp("2025-07-01", tz="UTC")].copy()
    reports = pd.read_csv(parsed_csv)
    reports["report_at"] = pd.to_datetime(reports.report_at, utc=True, format="mixed")
    availability = availability_frame(dev, reports, team_lookup(team_log))
    features = build_features(dev).merge(availability, on="game_id", validate="one_to_one")
    extended = list(FEATURES)+AVAILABILITY_FEATURES
    out = new_dir(out)
    features.to_csv(out/"development_features.csv", index=False)
    protocol = ("Base eleven features versus the same set plus five declared-availability "
        "differentials and a coverage indicator, on the three existing development folds. "
        "For each game the latest report whose own timestamp precedes the decision cutoff is "
        "used; a report published after the cutoff is never read, and actual absence is never "
        "substituted for a declared status. Counts are unweighted: no player-impact or minutes "
        "data is available, so every listed player counts the same. Reports were BACKFILLED, "
        "which supports development but cannot establish what was visible before a past game. "
        "These folds have been inspected repeatedly; this is not confirmation.")
    report = {"created_at": now(), "warning": WARNING, "protocol": protocol,
              "availability_features": AVAILABILITY_FEATURES,
              "coverage_rate": availability.attrs["coverage_rate"],
              "unmapped_team_rows": availability.attrs["unmapped_team_rows"],
              "reports_parsed": int(reports.source.nunique()), "report_rows": len(reports),
              "folds": {}, "pooled": {}, "code_sha256": code_hash(),
              "data_sha256": {f: digest(data/f) for f in ("games.csv", "results.csv")}}
    pooled = {"base": [], "extended": []}
    for year in YEARS:
        season = f"{year}-{str(year+1)[-2:]}"
        parts = partition(features, fold_boundaries(year))
        combined = pd.concat([parts["train"], parts["tune"]])
        cal, val = parts["calibration"], parts["validation"]
        fold = {"split_counts": {k: len(v) for k, v in parts.items()},
                "validation_coverage": float(val.availability_covered.mean()), "models": {}}
        predictions = {}
        for name, columns in (("base", list(FEATURES)), ("extended", extended)):
            model, calibrator, raw, p = _fit(combined, cal, val, columns)
            child = new_dir(out/f"{season}-{name}")
            write_json(child/"bundle.json", {"features": columns, "logistic": model,
                                             "calibrator": calibrator, "l2": .01})
            prediction = val[["game_id", "decision_at", "y"]].copy()
            prediction["p_raw"], prediction["p"] = raw, p
            prediction.to_csv(child/"validation_predictions.csv", index=False)
            pooled[name].append(prediction)
            predictions[name] = p
            fold["models"][name] = {"metrics": metrics(val.y, p), "raw_metrics": metrics(val.y, raw)}
        fold["extended_minus_base"] = paired_interval(val, predictions["extended"], predictions["base"])
        report["folds"][season] = fold
        print(f"{season}: base={fold['models']['base']['metrics']['log_loss']:.6f} "
              f"extended={fold['models']['extended']['metrics']['log_loss']:.6f} "
              f"(coverage {fold['validation_coverage']:.1%})", flush=True)
    base = pd.concat(pooled["base"], ignore_index=True)
    for name, frames in pooled.items():
        pooled_frame = pd.concat(frames, ignore_index=True)
        if not pooled_frame[["game_id", "y"]].equals(base[["game_id", "y"]]):
            raise ValueError("Variants must score identical games")
        report["pooled"][name] = {"games": len(pooled_frame),
                                  "metrics": metrics(pooled_frame.y, pooled_frame.p),
                                  "raw_metrics": metrics(pooled_frame.y, pooled_frame.p_raw)}
    report["pooled"]["extended_minus_base_log_loss"] = (report["pooled"]["extended"]["metrics"]["log_loss"]
                                                        - report["pooled"]["base"]["metrics"]["log_loss"])
    write_json(out/"report.json", report)
    lines = ["# Declared-availability feature comparison", "", WARNING, "", protocol, "",
             f"Reports parsed: {report['reports_parsed']} ({report['report_rows']} rows). "
             f"Game coverage: {report['coverage_rate']:.1%}. Unmapped team rows: {report['unmapped_team_rows']}.",
             "", "Per-fold calibrated log loss (lower is better):"]
    for season, fold in report["folds"].items():
        lines.append(f"- {season}, n={fold['split_counts']['validation']}, "
                     f"coverage={fold['validation_coverage']:.1%}: " + "; ".join(
                         f"{k}={v['metrics']['log_loss']:.6f}" for k, v in fold["models"].items()))
        ci = fold["extended_minus_base"]
        lines.append(f"  extended minus base: {ci['difference']:+.6f}; "
                     f"95% block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]"
                     + ("  (excludes zero)" if ci['ci95'][1] < 0 or ci['ci95'][0] > 0 else "  (includes zero)"))
    lines.extend(["", "Pooled descriptive metrics:"])
    for name in ("base", "extended"):
        m = report["pooled"][name]
        lines.append(f"- {name}: n={m['games']}; log loss={m['metrics']['log_loss']:.6f}; "
                     f"Brier={m['metrics']['brier']:.6f}; accuracy={m['metrics']['accuracy']:.2%}")
    lines.append(f"- pooled extended minus base: {report['pooled']['extended_minus_base_log_loss']:+.6f}")
    lines.extend(["", "Negative favors availability features. Unweighted counts ignore player impact,",
                  "so a null result here does not show that availability is uninformative, only that",
                  "counts of listed players are. Backfilled reports cannot support a claim about what",
                  "was obtainable before a past game. No feature set is promoted by this command."])
    (out/"PASTE_BACK.md").write_text("\n".join(lines)+"\n")
    return {"run": str(out), "coverage_rate": report["coverage_rate"],
            "pooled_extended_minus_base": report["pooled"]["extended_minus_base_log_loss"],
            "report_command": f'sports report --path "{out}"'}
