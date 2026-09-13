#!/bin/sh
# Weekly results-refresh loop: download the current 2026-27 schedule payload,
# fold newly settled games into a NEW rolling dataset, advance the dataset
# pointer, and fold schedule changes into the collection plan. Recorded polls
# and snapshots are never touched. Failures append to logs/alerts.log; the
# pointer only advances after a fully validated merge.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"
STAMP=$(date +%Y%m%d)
LOG="$ROOT/logs/refresh.log"
mkdir -p "$ROOT/logs"
fail() {
  echo "$(date -u +%FT%TZ) CRITICAL results refresh failed at: $1" >> "$ROOT/logs/alerts.log"
  command -v osascript >/dev/null && osascript -e \
    'display notification "Results refresh failed: '"$1"'" with title "Sports Method"' || true
  exit 2
}
RAW="$ROOT/data/raw/schedule-refresh-$STAMP"
if [ -e "$RAW" ]; then echo "Already refreshed today: $RAW" >> "$LOG"; exit 0; fi
"$PY" "$ROOT/scripts/download_schedule.py" --seasons 2026-27 --out "$RAW" \
  >> "$LOG" 2>&1 || fail download
BASE=$(cat "$ROOT/configs/rolling-dataset.txt")
OUT="data/normalized/rolling-$STAMP"
"$PY" -m sports_method.cli merge-settled --base "$ROOT/$BASE" \
  --season-raw "$RAW/raw" --out "$ROOT/$OUT" >> "$LOG" 2>&1 || fail merge-settled
printf '%s\n' "$OUT" > "$ROOT/configs/rolling-dataset.txt"
"$PY" -m sports_method.cli collect-refresh --collection "$ROOT/collection/2026-27" \
  --schedule "$RAW/games.csv" >> "$LOG" 2>&1 || fail collect-refresh
echo "$(date -u +%FT%TZ) refreshed: pointer -> $OUT" >> "$LOG"
