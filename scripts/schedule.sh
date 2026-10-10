#!/usr/bin/env bash
# Install / remove / show the betb2b background jobs (macOS launchd). Two independent jobs:
#   com.scrapamoja.scrape   every 6 h : `scrape <skin> scheduled --sport <sport> --direct` (odds for new
#                                        games, then the results/period/statistics/H2H backfill passes)
#   com.scrapamoja.results  every 30 min: `results <skin> --auto` (final scores of finished games only;
#                                        no odds scrape — cheap, uncapped, see `results --help`)
# Both are direct mode (data fetching only, no page loads), so they are allowed on a geo-restricted
# machine; neither uses --ingest (the engine reads Neon itself). The Mac must be awake and you must be
# logged in for launchd jobs to fire.
#
#   scripts/schedule.sh install | uninstall | show
#   scripts/schedule.sh scrape | results      one run now, in the foreground
#   scripts/schedule.sh event <id>            results for just that stored match, now
#
# Overrides (environment, at install time): SCRAPE_SKIN (default betwinner), SCRAPE_SPORT (basketball),
# SCRAPE_EVERY (21600 s), RESULTS_EVERY (1800 s), SCRAPE_TIMEOUT (3600 s).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LA="$HOME/Library/LaunchAgents"
LOG="$HOME/Library/Logs/scrapamoja-scrape.log"
SKIN="${SCRAPE_SKIN:-betwinner}"
SPORT="${SCRAPE_SPORT:-basketball}"
EVERY="${SCRAPE_EVERY:-21600}"
RESULTS_EVERY="${RESULTS_EVERY:-1800}"
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

plist() { echo "$LA/com.scrapamoja.$1.plist"; }
install_job() {   # name interval-seconds
  cat > "$(plist "$1")" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.scrapamoja.$1</string>
  <key>ProgramArguments</key><array><string>$ROOT/scripts/schedule.sh</string><string>$1</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>SCRAPE_SKIN</key><string>$SKIN</string>
    <key>SCRAPE_SPORT</key><string>$SPORT</string>
    <key>SCRAPE_TIMEOUT</key><string>$TIMEOUT</string>
  </dict>
  <key>StartInterval</key><integer>$2</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
  launchctl bootout "gui/$(id -u)/com.scrapamoja.$1" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$(plist "$1")"
  echo "installed: $1 ($SKIN) every $(($2/60)) min"
}

case "${1:-show}" in
  install)
    [ -x "$PY" ] || { echo "no virtualenv at $PY"; exit 1; }
    mkdir -p "$LA" "$HOME/Library/Logs"
    # the single job of the first version (label com.scrapamoja.betb2b) is replaced by the two below
    launchctl bootout "gui/$(id -u)/com.scrapamoja.betb2b" 2>/dev/null || true
    rm -f "$LA/com.scrapamoja.betb2b.plist"
    install_job scrape "$EVERY"
    install_job results "$RESULTS_EVERY"
    echo "log: $LOG" ;;
  uninstall)
    for j in scrape results betb2b; do
      launchctl bootout "gui/$(id -u)/com.scrapamoja.$j" 2>/dev/null || true; rm -f "$(plist "$j")"
    done
    echo "uninstalled the scraper jobs" ;;
  scrape) scrape ;;
  results) results --auto ;;
  event) results --event "${2:?usage: scripts/schedule.sh event <id>}" ;;
  show)
    for j in scrape results; do
      [ -f "$(plist "$j")" ] && echo "installed: $j" || echo "not installed: $j"
      launchctl print "gui/$(id -u)/com.scrapamoja.$j" 2>/dev/null | grep -E "state =|run interval|last exit" || true
    done
    echo "log: $LOG" ;;
  *) echo "usage: scripts/schedule.sh install|uninstall|show|scrape|results|event <id>"; exit 2 ;;
esac
