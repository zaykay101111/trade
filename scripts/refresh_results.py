"""Weekly NBA results refresh, as a Python job.

Ported from refresh_results.sh because macOS denies /bin/sh execution of a
script under ~/Documents when launched by launchd, while the project's venv
interpreter is permitted. Same behaviour: download a fresh schedule payload,
merge newly settled games into a NEW dataset, advance the pointer only after a
validated merge, then fold schedule changes into the collection plan.

Recorded polls and snapshots are never touched.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT/".venv"/"bin"/"python")


def now():
    return datetime.now(timezone.utc).isoformat()


def append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(line.rstrip("\n")+"\n")


def fail(logs, stage, detail):
    append(logs/"alerts.log", f"{now()} CRITICAL NBA results refresh failed at {stage}: {detail}")
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            'display notification "NBA refresh failed: %s" '
                            'with title "Sports Method"' % stage], timeout=10, check=False)
        except Exception:
            pass
    raise SystemExit(2)


def run(args, logs, stage):
    result = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    append(logs/"refresh.log", f"{now()} {stage}\n{result.stdout}{result.stderr}")
    if result.returncode != 0:
        fail(logs, stage, result.stderr.strip()[-400:])
    return result


def main():
    logs = ROOT/"logs"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    raw = ROOT/"data"/"raw"/f"schedule-refresh-{stamp}"
    if raw.exists():
        append(logs/"refresh.log", f"{now()} already refreshed today: {raw}")
        print(json.dumps({"status": "already refreshed today"}))
        return
    run([PY, str(ROOT/"scripts"/"download_schedule.py"), "--seasons", "2026-27",
         "--out", str(raw)], logs, "download")
    pointer = ROOT/"configs"/"rolling-dataset.txt"
    base = ROOT/pointer.read_text().strip()
    out = Path("data")/"normalized"/f"rolling-{stamp}"
    run([PY, "-m", "sports_method.cli", "merge-settled", "--base", str(base),
         "--season-raw", str(raw/"raw"), "--out", str(ROOT/out)], logs, "merge-settled")
    pointer.write_text(str(out)+"\n")
    run([PY, "-m", "sports_method.cli", "collect-refresh",
         "--collection", str(ROOT/"collection"/"2026-27"),
         "--schedule", str(raw/"games.csv")], logs, "collect-refresh")
    append(logs/"refresh.log", f"{now()} refreshed: pointer -> {out}")
    print(json.dumps({"status": "refreshed", "pointer": str(out)}))


if __name__ == "__main__":
    main()
