"""One automation tick: capture injury PDFs, record paired forecasts, alert on failure.

Designed for cron every five minutes. Each tick is independent and safe to
repeat: off-window polls record nothing, the archiver never refetches a held
file, and every action appends to logs/prospective.jsonl. Failures append to
logs/alerts.log and raise a macOS notification; silence in alerts.log plus a
fresh heartbeat line in the JSONL is the healthy state. A tick makes only free
public NBA PDF requests — never a paid odds request.

The rolling dataset path lives in a pointer file (default
configs/rolling-dataset.txt) so a weekly merge-settled can advance history
without editing crontab. The pointer must name a directory containing
games.csv/results.csv.
"""
import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def now():
    return datetime.now(timezone.utc)


def append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(line.rstrip("\n")+"\n")


def alert(logs, message):
    stamp = now().isoformat()
    append(logs/"alerts.log", f"{stamp} {message}")
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            'display notification "%s" with title "Sports Method"'
                            % message.replace('"', "'")[:180]], timeout=10, check=False)
        except Exception:
            pass  # Alerting must never break the tick itself.


def game_day_today(collection):
    import pandas as pd
    schedule = pd.read_csv(collection/"schedule.csv")
    cutoffs = pd.to_datetime(schedule.decision_at, utc=True)
    eastern = cutoffs.dt.tz_convert("America/New_York").dt.date
    today = pd.Timestamp.now(tz="America/New_York").date()
    return (eastern == today).any()


def capture_pdfs(a, logs):
    """Throttled prospective PDF capture; at most one attempt per interval."""
    marker = logs/"last_capture_attempt.txt"
    if marker.exists() and time.time()-marker.stat().st_mtime < a.capture_interval_minutes*60:
        return {"skipped": "throttled"}
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(now().isoformat()+"\n")
    import pandas as pd
    day = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    run = subprocess.run([sys.executable, str(ROOT/"scripts"/"archive_injury_reports.py"),
                          "--start", day, "--end", day, "--out", a.archive, "--prospective",
                          "--hours", a.hours, "--max-files", "24"],
                         capture_output=True, text=True, timeout=900)
    if run.returncode != 0:
        raise RuntimeError("PDF capture failed: "+run.stderr.strip()[-400:])
    return json.loads(run.stdout)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--collection", default=str(ROOT/"collection"/"2026-27"))
    p.add_argument("--pair", default=str(ROOT/"runs"/"injury-pair-v1"))
    p.add_argument("--baseline", default=str(ROOT/"runs"/"release-2026-27-v2"))
    p.add_argument("--data-pointer", default=str(ROOT/"configs"/"rolling-dataset.txt"))
    p.add_argument("--archive", default=str(ROOT/"data"/"injury-prospective"))
    p.add_argument("--out", default=str(ROOT/"collection"/"injury-pair-v1"))
    p.add_argument("--logs", default=str(ROOT/"logs"))
    p.add_argument("--hours", default="11AM,12PM,01PM,02PM,03PM,04PM,05PM,06PM,07PM,08PM")
    p.add_argument("--capture-interval-minutes", type=float, default=30)
    a = p.parse_args()
    logs = Path(a.logs)
    tick = {"at": now().isoformat(), "capture": None, "poll": None, "status": None, "errors": []}
    collection = Path(a.collection)
    data = Path(a.data_pointer).read_text().strip()
    if not (ROOT/data).is_dir() and not Path(data).is_dir():
        alert(logs, f"CRITICAL rolling dataset pointer is broken: {data}")
        append(logs/"prospective.jsonl", json.dumps({**tick, "errors": ["broken data pointer"]}))
        raise SystemExit(2)
    data = str(ROOT/data) if (ROOT/data).is_dir() else data

    try:
        if game_day_today(collection):
            tick["capture"] = capture_pdfs(a, logs)
    except Exception as exc:
        tick["errors"].append("capture: "+str(exc))
        alert(logs, "WARN injury PDF capture failed: "+str(exc)[:200])

    try:
        sys.path.insert(0, str(ROOT/"src"))
        from sports_method.challenger import poll
        from sports_method.pair_monitor import pair_status
        tick["poll"] = poll(a.collection, a.pair, a.baseline, data, a.out,
                            archive=a.archive if Path(a.archive, "index.jsonl").exists() else None,
                            record=True)
        if tick["poll"].get("games", 0) and tick["poll"].get("both_usable", 0) == 0:
            alert(logs, "WARN recorded games have no usable injury report; check capture")
    except Exception as exc:
        tick["errors"].append("poll: "+str(exc))
        alert(logs, "CRITICAL paired poll failed: "+str(exc)[:200])
        append(logs/"prospective.jsonl", json.dumps(tick))
        traceback.print_exc()
        raise SystemExit(2)

    try:
        status = pair_status(a.collection, a.out, archive=a.archive
                             if Path(a.archive, "index.jsonl").exists() else None)
        tick["status"] = {k: status[k] for k in
                          ("past_cutoffs", "recorded", "missed_games", "both_usable", "next_cutoff")}
        seen_path = logs/"missed_games_alerted.txt"
        seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
        new_missed = [m["game_id"] for m in status["missed"] if m["game_id"] not in seen]
        if new_missed:
            alert(logs, f"WARN missed T-60 windows for games: {','.join(new_missed[:8])}"
                        + ("..." if len(new_missed) > 8 else ""))
            append(seen_path, "\n".join(new_missed))
    except Exception as exc:
        tick["errors"].append("status: "+str(exc))
        alert(logs, "WARN pair-status failed: "+str(exc)[:200])

    append(logs/"prospective.jsonl", json.dumps(tick))
    print(json.dumps(tick, indent=2))


if __name__ == "__main__":
    main()
