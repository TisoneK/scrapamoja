# Shared API / Control-Plane Contracts

Companion to `db-architecture.md`. That file covers the **DATA plane** (Supabase —
the shared bus). This one covers the **CONTROL plane**: the HTTP APIs services
expose so they can be **triggered and monitored**, plus user-facing app traffic.

**The rule (scrapamoja ADR-14 · engine ADR-1/2/3):** services do **NOT** exchange DATA
over HTTP. Data flows through Supabase. HTTP is only for **control** (queue a scrape,
run predictions, health) and for **users** (the website). Results of any control
call always land in **Supabase**, never returned as the integration contract.

Identical in all three repos. Find your repo under "Per-repo surface".
> **Engine refresh 2026-07-28 (ADR-2, corrected by ADR-3):** the engine's control
> surface is now concrete — retired endpoints listed, the new `POST /api/predictions/run`
> trigger + run-monitoring GETs specified. ADR-3 corrected the `event_id` type from
> uuid to **text** (the betb2b backend id is a string) — the `event_ids` field in
> the trigger body below is `[text]`, not `[uuid]`. The other two repos' copies
> will pick this up on their next sync.

## Two planes

| Plane   | Medium    | Carries                                  | Doc                  |
|---------|-----------|------------------------------------------|----------------------|
| DATA    | Supabase  | odds, events, h2h, predictions, users    | `db-architecture.md` |
| CONTROL | HTTP APIs | trigger/monitor jobs, health, user traffic | this file          |

## Per-repo surface

### scrapamoja — scraper control API · **LIVE**
Base `https://scrapamoja.up.railway.app` · Auth `x-api-key: $SCRAPER_API_KEY` (unset → 503, wrong → 401) · OpenAPI at `/docs`
- `POST /api/scraper/runs` — queue a scrape `{skin, action(live|prematch|all), sport?, subgames?, count?}` → `202` job
- `GET  /api/scraper/runs` · `GET /api/scraper/runs/{id}` — monitor (status `queued→running→succeeded/failed`, live `phase`)
- `GET  /api/scraper/skins` · `/sports` · `/counts`
- `GET  /api/scraper/odds/{event_id}` — latest odds (convenience; the same data is readable straight from Supabase)
- `GET  /health` (Railway healthcheck) · plus the pre-existing `/feature-flags/*`, `/failures/*`
**Produces:** betb2b rows → **Supabase** (not the HTTP response). **Called by:** the website admin UI.

### scorewise-engine — control surface · **DESIGNED (ADR-1/2/3, 2026-07-28)**
Base `https://scorewise-engine.up.railway.app` · Auth `x-api-key: $SCOREWISE_API_KEY` (unset → 503, wrong → 401) · OpenAPI at `/docs`.

**Retired (their work moved to Supabase):**
- `POST /api/ingest` — was scraper→engine *data*. Replaced by the engine reading betb2b tables straight from Supabase (ADR-3 §B-6; ADR-2 §B-4's original queries were wrong and are superseded).
- `POST /api/fetch-from-scraper` — engine pulling data from the scraper. Obsolete; the engine's source is now Supabase, not the scraper's HTTP API.
- `GET /api/scraper-status` — proxy of the scraper's `/api/status`. The website can hit the scraper's control API directly; the engine has no business proxying it.
- `api/webhook_sender.py` (outbound to website) — `predictions_updated` + `ingest_complete`. The website now subscribes to Supabase Realtime on `predictions`; no push channel needed.
- The in-process `_store` + `predictions.json` disk persistence (`api/routers/ingest.py` + `fetch.py`) — replaced by the `predictions` + `prediction_runs` tables (ADR-2 §B-1/2, FK types corrected by ADR-3: `event_id` is text, `team_id` is bigint).

**Kept (stateless compute / convenience reads / control):**
- `GET /health` — Railway healthcheck, no auth, returns `{"status":"ok"}`.
- `POST /predict` — single-match stateless compute. Stays for ad-hoc / partner / debug; the engine still produces `PredictionOutput` and the response shape is unchanged.
- `POST /predict/batch` — multi-match stateless compute (max 50). Stays; it is also what the new trigger runs internally.
- `POST /predict/file` — JSON file upload (dev/test only). Stays for now; can be removed in a future cleanup if programmatic consumers don't need it.
- `GET /api/predictions` · `GET /api/predictions/download` — convenience reads over the new `predictions` table (filterable by `?successful_only=true` → SQL `WHERE success`). The website reads Supabase directly per its ADR-4; these are kept for debug / partner / export. **Not** the delivery mechanism anymore.
- `GET/POST/DELETE /api/config` · `GET /api/config/{key}` — the config-push feature. **Out of scope** for ADR-2 (orthogonal to data flow); stays as-is. A future ADR may migrate it to a Supabase `service_config` table (group C).

**Added (the new control plane):**
- `POST /api/predictions/run` — **trigger a prediction batch.** The engine reads eligible events from Supabase (group A), builds `MatchInput`s per `(event_id, scope)`, runs the pipeline, and writes the results back to the `predictions` + `prediction_runs` tables (group B). Returns `202 Accepted` with `{run_id, status: "running", triggered_by, started_at}` — the work happens on a background task; the caller polls `GET /api/predictions/runs/{run_id}` or subscribes to the `prediction_runs` row for completion. Optional body: `{triggered_by?: "website_admin"|"cron"|"manual", event_ids?: [text]}` — `event_id` is the betb2b backend id as a **string** (e.g. `"738518814"`), NOT a uuid (ADR-3). Omit `event_ids` to process all eligible events; pass an explicit list to backfill specific matches. Auth: `x-api-key: $SCOREWISE_API_KEY`.
- `GET /api/predictions/runs` — list recent runs (default last 20). Returns `[{id, triggered_by, status, started_at, completed_at, stats}, …]` newest-first. Admin-only (RLS on the underlying table; the API gate is the same `x-api-key`).
- `GET /api/predictions/runs/{run_id}` — single-run status + stats + (optional) the predictions it produced (joined via `predictions.run_id`). Polling target for the website admin UI.

**Trigger sources (control plane only — the result always lands in Supabase):**
- Website admin clicks "Run predictions" → `POST /api/predictions/run` with `triggered_by="website_admin"`.
- Railway cron (optional, future) → same endpoint with `triggered_by="cron"`. The endpoint is idempotent — concurrent runs over the same events just overwrite the same `predictions` rows with a newer `updated_at` and `run_id`.
- Supabase Realtime on `odds_snapshots` (future enhancement, not committed) — the engine subscribes to odds changes and triggers a run when a scrape lands. Logged as `triggered_by="supabase_watch_future"` if/when implemented.

**Produces:** `predictions` + `prediction_runs` rows → **Supabase**. **Called by:** the website admin UI (to trigger a run) + the website's polling/Realtime subscription (to monitor). The scraper never calls the engine — both read/write Supabase independently.

### scorewise-website — Next.js API + UI · **TO REDESIGN (ADR-4)**
- **Keeps:** admin proxies to the scraper control API (`/api/admin/scraper/*` → scrapamoja `/api/scraper/*`); a proxy that calls `POST /api/predictions/run` on the engine when an admin clicks "Run predictions" (engine ADR-2 commit) — and polls `GET /api/predictions/runs/{id}` for the result.
- **RETIRED:** `/api/webhook/predictions`, `/api/webhook/result`, `engine-auto-sync` — data now comes from **Supabase** (Realtime), not webhooks/pull.
- Auth: NextAuth or **Supabase Auth** (ADR-4 open); RLS favors Supabase Auth.
**Reads:** betb2b + predictions from **Supabase** (Realtime). **Produces:** its own tables (group C) in Supabase.

## Who calls whom (control plane only)

    website admin ──HTTP──► scrapamoja /api/scraper/*      (queue/monitor scrapes)
    website admin ──HTTP──► engine POST /api/predictions/run  (run a prediction batch)
    website admin ──HTTP──► engine GET  /api/predictions/runs/{id}  (poll run status)
    (NO scraper→engine, NO engine→website HTTP — those are Supabase now)

## Conventions (all services)
- **Machine auth:** `x-api-key` header vs a per-service secret; fail closed (503 if unset, 401 if wrong).
- **`GET /health`** on every service (Railway healthcheck).
- **OpenAPI at `/docs`** for FastAPI services (scrapamoja, engine).
- A control call **triggers** work and returns a job/ack; the **result lands in Supabase** — never returned as the cross-service contract.
- Secrets live only in each repo's `.context/memory/secrets/` (gitignored), never in tracked files.

## Status
- **scrapamoja** control API: LIVE + documented (`/docs`).
- **engine** control surface: DESIGNED (ADR-1/2/3, 2026-07-28) — retired endpoints listed, the new `POST /api/predictions/run` trigger + run-monitoring GETs specified. ADR-3 corrected the `event_id` type (text, not uuid) — the trigger body's `event_ids` field is `[text]`. Implementation lands in the next feature-engineer session; until then the engine still serves the old `/api/ingest` + `/api/fetch-from-scraper` + webhook path.
- **website** API: to redesign (ADR-4) — retire webhooks, keep admin proxies (scraper + the new engine trigger proxy).
