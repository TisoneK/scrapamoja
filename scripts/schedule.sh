#!/usr/bin/env bash
# Install / remove / show the betb2b scraper background job (macOS launchd).
# Runs `scrape <skin> scheduled --sport basketball --direct` every 6 h: odds, then the results,
# period, statistics and H2H backfill passes (they run as part of every scrape). Data fetching only
# (--direct), so it is allowed on a geo-restricted machine; no --ingest (the engine reads Neon itself).
# The Mac must be awake and you must be logged in for launchd jobs to fire.
#
#   scripts/schedule.sh install | uninstall | show | run     (run = one scrape now, in the foreground)
#
# Overrides (environment, at install time): SCRAPE_SKIN (default betwinner), SCRAPE_SPORT
# (basketball), SCRAPE_EVERY seconds (21600), SCRAPE_TIMEOUT seconds (3600).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.scrapamoja.betb2b"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/scrapamoja-scrape.log"
SKIN="${SCRAPE_SKIN:-betwinner}"
SPORT="${SCRAPE_SPORT:-basketball}"
EVERY="${SCRAPE_EVERY:-21600}"
TIMEOUT="${SCRAPE_TIMEOUT:-3600}"
PY="$ROOT/.venv/bin/python"

scrape() {
  cd "$ROOT"
  echo "=== $(date -u +%FT%TZ) scrape $SKIN $SPORT start"
  local rc=0
  "$PY" -m src.sites.betb2b.cli scrape "$SKIN" scheduled --sport "$SPORT" --direct --timeout "$TIMEOUT" || rc=$?
  echo "=== $(date -u +%FT%TZ) scrape $SKIN $SPORT done rc=$rc"
  return $rc
}

case "${1:-show}" in
  install)
    [ -x "$PY" ] || { echo "no virtualenv at $PY"; exit 1; }
    mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
    cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$ROOT/scripts/schedule.sh</string><string>run</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>SCRAPE_SKIN</key><string>$SKIN</string>
    <key>SCRAPE_SPORT</key><string>$SPORT</string>
    <key>SCRAPE_TIMEOUT</key><string>$TIMEOUT</string>
  </dict>
  <key>StartInterval</key><integer>$EVERY</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "installed: $SKIN $SPORT every $((EVERY/60)) min"
    echo "log: $LOG" ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"; echo "uninstalled $LABEL" ;;
  run) scrape ;;
  show)
    [ -f "$PLIST" ] && echo "installed: $PLIST" || echo "not installed"
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|run interval|last exit" || true
    echo "log: $LOG" ;;
  *) echo "usage: scripts/schedule.sh install|uninstall|show|run"; exit 2 ;;
esac
