# Railway Deployment — Scrapamoja

This guide deploys the **FastAPI control plane** (`src/api/main.py`) to Railway as a long-running web service. The CLI (`src/main.py`) is for one-off scrape jobs — it ships inside the image for `railway run` use but is NOT the deployed process.

---

## What gets deployed

| Component | Status |
|---|---|
| FastAPI app (`src/api/main:app`) | ✅ Deployed (primary web service) |
| Playwright + Chromium | ✅ Baked into the image |
| SQLite DB (`data/adaptive.db`) | ⚠️ Requires a Railway Volume for persistence |
| React UI (`ui/app/`) | ❌ Not deployed by this config — deploy separately or add a build step |

**Public endpoints after deploy:**

- `/` — root (404 by default; FastAPI has no `/` route)
- `/health` — health check (`{"status": "ok", "service": "scrapamoja-api"}`)
- `/docs` — Swagger UI
- `/redoc` — ReDoc
- `/feature-flags` — feature-flag management REST API
- `/failures` — selector-failure escalation REST API
- `/ws/feature-flags` — WebSocket for real-time flag updates

---

## Quick deploy

### Option A — Railway CLI (recommended)

```bash
# 1. Install the Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Link this repo to a new Railway project (run from the project root)
railway link

# 4. Deploy
railway up
```

### Option B — Railway dashboard

1. Go to <https://railway.app/new>
2. Choose **Deploy from GitHub repo** → select `TisoneK/scrapamoja`
3. Railway auto-detects the `Dockerfile` and builds it.
4. Wait ~5–8 minutes (Playwright + Chromium install is the heavy step).

---

## Required configuration

### 1. Environment variables

Set these in the Railway service's **Variables** tab:

| Variable | Default | Required | Purpose |
|---|---|---|---|
| `PORT` | `8000` | auto-injected by Railway | Port to bind. Railway injects this automatically — do NOT set it yourself. |
| `GUNICORN_WORKERS` | `2` | **set to `1`** if you use the scraper control API | Number of uvicorn workers. The scrape-job runner is single-flight **per worker** — one worker keeps it globally single-flight (and one Chromium at a time). |
| `ADAPTIVE_DB_PATH` | `/app/data/adaptive.db` | recommended | Selector-engine SQLite DB. **Point at a Volume mount path** for persistence (see below). |
| `SCRAPER_API_KEY` | _(unset)_ | **required to enable** the scraper control API | Shared secret checked against the `x-api-key` header. Unset → all `/api/scraper/*` endpoints return `503` (fail closed). Generate a long random value. |
| `BETB2B_DB_PATH` | `data/betb2b/odds.db` | recommended | betb2b odds + job store. **Point at the Volume** (`/app/data/betb2b/odds.db`) so scrape results + job history survive redeploys. |
| `BETB2B_PROXY_URL` | _(unset)_ | **required for scraping** | Allowed-country proxy, e.g. `http://user:pass@host:port`. The Railway egress IP is WAF-blocked (HTTP 203), so **without a proxy every scrape job fails** with a clear status. |
| `BETB2B_PROXY_USER` / `BETB2B_PROXY_PASS` | _(unset)_ | optional | Proxy creds if not embedded in `BETB2B_PROXY_URL`. |
| `BETB2B_PROXY_COUNTRY` | _(unset)_ | optional | ISO code (e.g. `KE`) to validate proxy egress country before scraping. |

The Dockerfile sets sensible defaults for everything else; Railway injects `PORT` at runtime.

### 2. Persistent volume (REQUIRED for non-ephemeral data)

Railway's filesystem is **ephemeral** — every redeploy starts from a fresh image. The SQLite database at `data/adaptive.db` (which holds feature flags, audit events, failure events) will be lost on every redeploy unless you mount a Volume.

**To persist it:**

1. In the Railway service → **Settings** → **Volumes** → **Add Volume**
2. Mount path: `/app/data`
3. The app will create `adaptive.db` there on first boot.
4. Set `ADAPTIVE_DB_PATH=/app/data/adaptive.db` (already the default, but explicit is better).

If you skip the volume, the app still runs — but every redeploy wipes feature flags and resets the failure log to demo data.

---

## Health check

Railway probes `GET /health` (configured in `railway.json` → `deploy.healthcheckPath`).

The endpoint returns `200 {"status": "ok", "service": "scrapamoja-api"}`. If it returns non-200 or times out for ~30s, Railway marks the service unhealthy and restarts it (up to 5 retries per `restartPolicyMaxRetries`).

---

## Remote-controlling the scraper (control API)

The betb2b scraper is driven over HTTP under `/api/scraper/*` (see `/docs`).
Every endpoint requires the `x-api-key` header matching `SCRAPER_API_KEY`
(unset ⇒ `503`; wrong/missing ⇒ `401`). Scrapes run as **single-flight
background jobs** inside the web service and persist to the betb2b store; the
deployed egress **needs `BETB2B_PROXY_*`** or jobs fail with a clear reason
(the Railway IP is WAF-blocked). See ADR-12.

| Method & path | Purpose |
|---|---|
| `POST /api/scraper/runs` | Queue a scrape. Body: `{skin, action, sport?, subgames?, count?}`. `action` = `live`/`prematch`/`all` (or `list_live`/…). Returns `202` + the job. |
| `GET /api/scraper/runs` | List recent jobs (`?status=`, `?limit=`). |
| `GET /api/scraper/runs/{id}` | One job's status/outcome (`queued`→`running`→`succeeded`/`failed`). |
| `GET /api/scraper/skins` / `sports` | Available skins / sport slugs. |
| `GET /api/scraper/counts` | Odds-store row counts (coverage/health). |
| `GET /api/scraper/odds/{event_id}` | Latest odds per selection (cross-skin; `?skin=`). |

```bash
# Queue a live basketball scrape, then poll it:
curl -sX POST https://<your-app>.up.railway.app/api/scraper/runs \
  -H "x-api-key: $SCRAPER_API_KEY" -H "content-type: application/json" \
  -d '{"skin":"linebet","action":"live","sport":"basketball"}'
curl -s https://<your-app>.up.railway.app/api/scraper/runs/1 -H "x-api-key: $SCRAPER_API_KEY"
```

**Deploy checklist for the control API:** set `SCRAPER_API_KEY`,
`BETB2B_PROXY_URL` (+ creds/country), `BETB2B_DB_PATH=/app/data/betb2b/odds.db`
(on the Volume), and `GUNICORN_WORKERS=1`.

---

## Resource sizing

The Playwright + Chromium runtime is **memory-hungry**. Recommended Railway service size:

| Plan | RAM | CPU | OK for |
|---|---|---|---|
| Starter (512 MB) | 512 MB | 0.5 vCPU | ❌ Will OOM on first browser spawn |
| Developer (1 GB) | 1 GB | 1 vCPU | ⚠️ Tight — fine for API-only, may OOM under concurrent scrapes |
| Pro (8 GB) | 8 GB | 2 vCPU | ✅ Comfortable for API + occasional scrape jobs |

Start at **1 GB minimum**. Bump to Pro if you run scrapes inside the same service.

---

## Local build & test

```bash
# Build the image
docker build -t scrapamoja:latest .

# Run it locally (PORT defaults to 8000)
docker run --rm -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -e ADAPTIVE_DB_PATH=/app/data/adaptive.db \
    scrapamoja:latest

# Hit the health check
curl http://localhost:8000/health
# → {"status":"ok","service":"scrapamoja-api"}

# Open Swagger UI
open http://localhost:8000/docs
```

---

## Running the scraper CLI via Railway

The CLI ships inside the image (under `/app/src/main.py`). Run one-off scrape jobs without redeploying:

```bash
# From your laptop, using the Railway CLI:
railway run python -m src.main wikipedia scrape --limit 5

# Or open a shell inside the running service:
railway shell
$ python -m src.main flashscore scrape basketball live --limit 1
```

For scheduled scrape jobs, use Railway's **Cron Jobs** feature:

1. Railway service → **Settings** → **Cron Jobs** → **Add Cron Job**
2. Schedule: e.g. `*/30 * * * *` (every 30 min)
3. Command: `python -m src.main flashscore scrape basketball live --limit 50 --output json --file /app/data/scrape-$(date +%Y%m%d-%H%M).json`

---

## Troubleshooting

### Container crashes on startup with `playwright._impl._api_types.Error: Executable doesn't exist`

Chromium isn't installed. Confirm the Dockerfile's `RUN playwright install --with-deps chromium` layer ran. The `--with-deps` flag is critical — without it, the browser downloads but won't launch because the OS libraries it links against are missing.

### Health check fails with 502/503

The service probably didn't bind to `0.0.0.0`. The Dockerfile's CMD does this explicitly — don't override it with a custom start command that binds to `127.0.0.1` or `localhost`.

### Database resets after every redeploy

You didn't mount a Volume at `/app/data`. See **Persistent volume** above.

### Out of memory (OOMKilled)

Playwright + Chromium needs ~500 MB just to spawn one browser. Either:
- Bump the Railway plan (Pro = 8 GB recommended).
- Reduce `GUNICORN_WORKERS` to `1` so only one Chromium is alive at a time.
- Don't run scrapes inside the API service — run them as separate `railway run` jobs.

### Port already in use

Railway injects `$PORT` automatically. Don't set it in your Variables — if you do, Railway's proxy can't reach the container.

---

## Files added by this setup

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build: Python 3.12 + Playwright + Chromium + gunicorn/uvicorn |
| `.dockerignore` | Strips tests, `.context/`, caches, and the UI from the build context |
| `railway.json` | Railway-specific config: Dockerfile builder + healthcheck + restart policy |
| `Procfile` | Conventional web process declaration (used if you switch off the Dockerfile builder) |
| `RAILWAY.md` | This document |

---

## What's NOT deployed by this config

- **React UI (`ui/app/`)** — Deploy as a separate Railway service (static site) pointing at the API's public URL. Set `VITE_API_URL` to the API service's Railway domain during the UI build.
- **Background scrape workers** — Run as separate `railway run` jobs or as a separate Railway worker service. Don't run scrapes inside the API service in production; they'll compete with API requests for the same Chromium pool.
- **Telemetry storage (InfluxDB)** — The `influxdb-client` dep is installed but no InfluxDB is configured. Add one as a separate Railway service and set the InfluxDB connection env vars if you want telemetry persistence.
