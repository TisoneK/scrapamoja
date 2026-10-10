#!/usr/bin/env bash
# Install / remove / show the betb2b results background job (macOS launchd).
# The job runs `results <skin> --auto` every 30 min: it asks the source only for matches that should
# have finished (2.5 h after start) and have no result yet, then fills their period scores and
# statistics. No odds scrape, no page loads (direct mode = data fetching only, allowed on a
# geo-restricted machine), no --ingest (the engine reads Neon itself). Odds for new games are a
# separate, manual step: `scripts/schedule.sh scrape` (one full scrape now, in the foreground).
# The Mac must be awake and you must be logged in for launchd jobs to fire.
#
#   scripts/schedule.sh install | uninstall | show | run | scrape
#   scripts/schedule.sh event <id>      results for just that stored match, now
#
# Overrides (environment, at install time): SCRAPE_SKIN (default betwinner), SCRAPE_SPORT
# (basketball), SCRAPE_EVERY seconds (1800), SCRAPE_TIMEOUT seconds (3600, `scrape` only).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.scrapamoja.betb2b"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/scrapamoja-scrape.log"
SKIN="${SCRAPE_SKIN:-betwinner}"
SPORT="${SCRAPE_SPORT:-basketball}"
EVERY="${SCRAPE_EVERY:-1800}"
TIMEOUT="${SCRAPE_TIMEOUT:-3600}"
PY="$ROOT/.venv/bin/python"

results() {
  cd "$ROOT"
  echo "=== $(date -u +%FT%TZ) results $SKIN $* start"
  local rc=0
  "$PY" -m src.sites.betb2b.cli results "$SKIN" --sport "$SPORT" "$@" || rc=$?
  echo "=== $(date -u +%FT%TZ) results $SKIN done rc=$rc"
  return $rc
}

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
  </dict>
  <key>StartInterval</key><integer>$EVERY</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "installed: results --auto for $SKIN every $((EVERY/60)) min"
    echo "log: $LOG" ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"; echo "uninstalled $LABEL" ;;
  run) results --auto ;;
  scrape) scrape ;;
  event) results --event "${2:?usage: scripts/schedule.sh event <id>}" ;;
  show)
    [ -f "$PLIST" ] && echo "installed: $PLIST" || echo "not installed"
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|run interval|last exit" || true
    echo "log: $LOG" ;;
  *) echo "usage: scripts/schedule.sh install|uninstall|show|run|scrape|event <id>"; exit 2 ;;
esac
