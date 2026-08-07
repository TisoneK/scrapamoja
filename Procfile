web: sh -c "gunicorn src.api.main:app --workers ${GUNICORN_WORKERS:-2} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 300 --graceful-timeout 30 --access-logfile - --error-logfile - --forwarded-allow-ips '*'"
# ADR-18: dedicated always-on scheduler worker — a SEPARATE Railway service, not
# the web one. Same image; override the service's start command to this. Needs
# DATABASE_URL (Supabase pooler) + BETB2B_DIRECT=1; cadences via the SCHED_* vars.
# ADR-22 low-storage mode: SCHED_LIVE_INTERVAL defaults to 0 → the live pass
# (the dominant data producer, 15s odds ticks) is DISABLED — scheduled-only.
# On a paid tier, set SCHED_LIVE_INTERVAL=15 (Railway env) to re-enable live.
worker: sh -c "python -m src.sites.betb2b.cli schedule ${SCHED_SKIN:-linebet} --sport ${SCHED_SPORT:-basketball} --scheduled-interval ${SCHED_PREMATCH_INTERVAL:-10800} --live-interval ${SCHED_LIVE_INTERVAL:-0} --results-interval ${SCHED_RESULTS_INTERVAL:-600} --refresh-window ${SCHED_REFRESH_WINDOW:-10800}"
