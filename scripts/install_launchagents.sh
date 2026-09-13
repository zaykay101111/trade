#!/bin/sh
# Install launchd agents for prospective collection. The macOS-native alternative
# to cron: no cron spool to be blocked by TCC, survives reboot, runs as you.
#
# Installs three agents:
#   com.sportsmethod.nfltick   every 5 min  - NFL paired capture
#   com.sportsmethod.nbatick   every 5 min  - NBA paired capture
#   com.sportsmethod.refresh   Mondays 10am - NBA results refresh
#
# Remove with:  sh scripts/install_launchagents.sh --uninstall
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"
AGENTS="$HOME/Library/LaunchAgents"
LABELS="com.sportsmethod.nfltick com.sportsmethod.nbatick com.sportsmethod.refresh"

uninstall() {
  for label in $LABELS; do
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    rm -f "$AGENTS/$label.plist"
  done
  echo "Removed sportsmethod launch agents."
}

[ "${1:-}" = "--uninstall" ] && { uninstall; exit 0; }
[ -x "$PY" ] || { echo "Missing venv at $PY" >&2; exit 1; }
mkdir -p "$AGENTS" "$ROOT/logs"

emit_plist() {
  label=$1; shift
  schedule=$1; shift
  cat > "$AGENTS/$label.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
$(for a in "$@"; do printf '    <string>%s</string>\n' "$a"; done)
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd.err</string>
  <key>RunAtLoad</key><true/>
$schedule
</dict>
</plist>
PLIST
}

emit_plist com.sportsmethod.nfltick \
  "  <key>StartInterval</key><integer>300</integer>" \
  "$PY" "$ROOT/scripts/nfl_tick.py"
emit_plist com.sportsmethod.nbatick \
  "  <key>StartInterval</key><integer>300</integer>" \
  "$PY" "$ROOT/scripts/prospective_tick.py"
# Invoked through the venv interpreter, not /bin/sh: macOS denies a system shell
# execution of a script under ~/Documents when launched by launchd.
emit_plist com.sportsmethod.refresh \
  "  <key>StartCalendarInterval</key><dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>" \
  "$PY" "$ROOT/scripts/refresh_results.py"

for label in $LABELS; do
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$label.plist"
  echo "loaded $label"
done
echo
echo "Verify (expect three lines):"
launchctl list | grep sportsmethod || echo "  none listed - see logs/launchd.err"
