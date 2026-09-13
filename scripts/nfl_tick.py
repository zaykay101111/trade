"""One NFL automation tick: refresh schedule when due, record paired forecasts, alert.

Designed for cron every five minutes. Each tick is independent and safe to
repeat: off-window polls record nothing, exclusive-create snapshots make a
double fire harmless, and nothing is ever backdated or overwritten. Every tick
appends one JSON line to logs/nfl_prospective.jsonl; failures append to
logs/alerts.log and raise a macOS notification.

Only free public nflverse requests are made, and only by the schedule refresh
(at most once per --refresh-interval-minutes). No odds request is ever made.

Recording is transient-tolerant: the poll is retried a few times inside the
five-minute window before the tick gives up, because a T-60 window missed is a
game that can never be recorded again.
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
sys.path.insert(0, str(ROOT/"src"))


def now():
    return datetime.now(timezone.utc)


def append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(line.rstrip("\n")+"\n")


def alert(logs, message):
    append(logs/"alerts.log", f"{now().isoformat()} [nfl] {message}")
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            'display notification "%s" with title "Sports Method NFL"'
                            % message.replace('"', "'")[:180]], timeout=10, check=False)
        except Exception:
            pass  # Alerting must never break the tick itself.


def refresh_schedule(a, logs):
    """Rebuild the dataset from a fresh nflverse pull, then fold it into the plan."""
    marker = logs/"nfl_last_refresh.txt"
    if marker.exists() and time.time()-marker.stat().st_mtime < a.refresh_interval_minutes*60:
        return {"skipped": "throttled"}
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(now().isoformat()+"\n")
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    dataset = ROOT/"data"/"normalized"/f"nfl-rolling-{stamp}"
    run = subprocess.run([sys.executable, str(ROOT/"scripts"/"download_nfl.py"),
                          "--out", str(dataset), "--prospective"],
                         capture_output=True, text=True, timeout=600)
    if run.returncode != 0:
        raise RuntimeError("NFL schedule download failed: "+run.stderr.strip()[-400:])
    from sports_method.nfl_collect import refresh_nfl_collection
    folded = refresh_nfl_collection(a.collection, dataset)
    # Advance the pointer only after a successful download AND fold.
    Path(a.data_pointer).write_text(str(dataset.relative_to(ROOT))+"\n")
    return {"dataset": str(dataset), **folded}


def record_with_retries(a, data, logs, attempts, pause):
    from sports_method.nfl_collect import poll_nfl
    last = None
    for attempt in range(1, attempts+1):
        try:
            return poll_nfl(a.collection, a.pair, data, a.out, record=True,
                            window_minutes=a.window_minutes)
        except Exception as exc:
            last = exc
            # Crossing T-60 is terminal: a later retry could only backdate.
            if "crossed T-60" in str(exc) or "backdate" in str(exc):
                raise
            append(logs/"nfl_prospective.jsonl", json.dumps(
                {"at": now().isoformat(), "retry": attempt, "error": str(exc)}))
            if attempt < attempts:
                time.sleep(pause)
    raise last


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--collection", default=str(ROOT/"collection"/"nfl-2026"))
    p.add_argument("--pair", default=str(ROOT/"runs"/"nfl-pair-v1"))
    p.add_argument("--data-pointer", default=str(ROOT/"configs"/"nfl-rolling-dataset.txt"))
    p.add_argument("--out", default=str(ROOT/"collection"/"nfl-pair-v1"))
    p.add_argument("--logs", default=str(ROOT/"logs"))
    p.add_argument("--window-minutes", type=float, default=5)
    p.add_argument("--refresh-interval-minutes", type=float, default=720)
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--retry-pause-seconds", type=float, default=5)
    a = p.parse_args()
    logs = Path(a.logs)
    tick = {"at": now().isoformat(), "sport": "nfl", "refresh": None,
            "poll": None, "status": None, "errors": []}

    try:
        tick["refresh"] = refresh_schedule(a, logs)
    except Exception as exc:
        tick["errors"].append("refresh: "+str(exc))
        alert(logs, "WARN schedule refresh failed: "+str(exc)[:200])

    data = Path(a.data_pointer).read_text().strip()
    resolved = ROOT/data if (ROOT/data).is_dir() else Path(data)
    if not resolved.is_dir():
        alert(logs, f"CRITICAL NFL dataset pointer is broken: {data}")
        tick["errors"].append("broken data pointer")
        append(logs/"nfl_prospective.jsonl", json.dumps(tick))
        raise SystemExit(2)

    try:
        tick["poll"] = record_with_retries(a, str(resolved), logs, a.attempts,
                                           a.retry_pause_seconds)
        if tick["poll"].get("games"):
            alert(logs, f"recorded {tick['poll']['games']} NFL forecast(s)")
    except Exception as exc:
        tick["errors"].append("poll: "+str(exc))
        alert(logs, "CRITICAL NFL paired poll failed: "+str(exc)[:200])
        append(logs/"nfl_prospective.jsonl", json.dumps(tick))
        traceback.print_exc()
        raise SystemExit(2)

    try:
        from sports_method.nfl_monitor import nfl_status
        status = nfl_status(a.collection, a.out)
        tick["status"] = {k: status[k] for k in
                          ("past_cutoffs", "recorded", "missed_games", "next_cutoff")}
        seen_path = logs/"nfl_missed_alerted.txt"
        seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
        fresh = [m["game_id"] for m in status["missed"] if m["game_id"] not in seen]
        if fresh:
            alert(logs, f"WARN missed NFL T-60 windows: {','.join(fresh[:8])}"
                        + ("..." if len(fresh) > 8 else ""))
            append(seen_path, "\n".join(fresh))
    except Exception as exc:
        tick["errors"].append("status: "+str(exc))
        alert(logs, "WARN nfl-status failed: "+str(exc)[:200])

    append(logs/"nfl_prospective.jsonl", json.dumps(tick))
    print(json.dumps(tick, indent=2))


if __name__ == "__main__":
    main()
