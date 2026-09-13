#!/bin/sh
# Install (or refresh) the two crontab lines that run prospective automation.
# Idempotent: lines are tagged and replaced, never duplicated. Remove with:
#   crontab -l | grep -v SPORTS_METHOD_AUTOMATION | crontab -
# Requires the Mac to be awake at poll times; consider `sudo pmset repeat` or
# Amphetamine on game days. The tick makes only free public NBA PDF requests.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "Missing venv at $PY" >&2; exit 1; }
TAG="# SPORTS_METHOD_AUTOMATION"
TICK="*/5 * * * * cd \"$ROOT\" && \"$PY\" scripts/prospective_tick.py >> logs/cron.out 2>&1 $TAG"
REFRESH="0 10 * * 1 cd \"$ROOT\" && sh scripts/refresh_results.sh >> logs/cron.out 2>&1 $TAG"
NFL="*/5 * * * * cd \"$ROOT\" && \"$PY\" scripts/nfl_tick.py >> logs/cron.out 2>&1 $TAG"
( crontab -l 2>/dev/null | grep -v "SPORTS_METHOD_AUTOMATION" ; \
  echo "$TICK"; echo "$REFRESH"; echo "$NFL" ) | crontab -
mkdir -p "$ROOT/logs"
echo "Installed. Current crontab:"
crontab -l | grep SPORTS_METHOD_AUTOMATION
