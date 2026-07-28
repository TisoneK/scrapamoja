#!/usr/bin/env bash
set -euo pipefail

SKIN="${1:-linebet}"
ACTION="${2:-prematch}"
SPORT="${3:-basketball}"
BASE="${BASE:-https://scrapamoja.up.railway.app}"
API_KEY="${BETB2B_API_KEY:-}"

if [ -z "$API_KEY" ]; then
    echo "Set BETB2B_API_KEY env var" >&2
    exit 1
fi

# Trigger the scrape
echo "Triggering  skin=$SKIN  action=$ACTION  sport=$SPORT"
BODY=$(jq -n --arg skin "$SKIN" --arg action "$ACTION" --arg sport "$SPORT" \
    '{skin: $skin, action: $action, sport: $sport}')

JOB=$(curl -sS -X POST "$BASE/api/scraper/runs" \
    -H "x-api-key: $API_KEY" \
    -H "content-type: application/json" \
    -d "$BODY")

JOB_ID=$(echo "$JOB" | jq -r '.job_id')
echo "job_id=$JOB_ID"
echo

# Poll with live phase progression
while true; do
    R=$(curl -sS "$BASE/api/scraper/runs/$JOB_ID" -H "x-api-key: $API_KEY")
    STATUS=$(echo "$R" | jq -r '.status')
    PHASE=$(echo "$R" | jq -r '.phase // "—"')
    TS=$(date +%H:%M:%S)
    printf "%s  %-10s  %s\n" "$TS" "$STATUS" "$PHASE"

    if [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ]; then
        EVENTS=$(echo "$R" | jq -r '.event_count // "?"')
        ERROR=$(echo "$R" | jq -r '.error // ""')
        echo "events=$EVENTS  error=$ERROR"
        break
    fi

    sleep 5
done

echo
echo "--- Counts ---"
curl -sS "$BASE/api/scraper/counts" -H "x-api-key: $API_KEY" | jq .
