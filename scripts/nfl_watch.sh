#!/bin/sh
# Foreground watcher: run the NFL tick every 60s until --until (UTC ISO) passes.
# A stand-in for cron when installing a crontab is not possible. Safe to stop and
# restart: every tick is independent and snapshots are exclusive-create, so a
# restart can never duplicate or overwrite an issued forecast.
#   sh scripts/nfl_watch.sh 2026-09-14T04:00:00Z
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"
UNTIL="${1:?usage: nfl_watch.sh <UTC-ISO-stop-time>}"
STOP=$("$PY" -c "import pandas as pd,sys;print(int(pd.Timestamp(sys.argv[1]).timestamp()))" "$UNTIL")
echo "$(date -u +%FT%TZ) watcher started, running until $UNTIL"
while [ "$(date -u +%s)" -lt "$STOP" ]; do
  "$PY" "$ROOT/scripts/nfl_tick.py" >> "$ROOT/logs/nfl_watch.out" 2>&1
  sleep 60
done
echo "$(date -u +%FT%TZ) watcher finished"
