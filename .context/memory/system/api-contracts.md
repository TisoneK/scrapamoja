# Shared API / Control-Plane Contracts

Companion to `db-architecture.md`. That file covers the **DATA plane** (Supabase —
the shared bus). This one covers the **CONTROL plane**: the HTTP APIs services
expose so they can be **triggered and monitored**, plus user-facing app traffic.

**The rule (scrapamoja ADR-14 · engine ADR-1):** services do **NOT** exchange DATA
over HTTP. Data flows through Supabase. HTTP is only for **control** (queue a scrape,
run predictions, health) and for **users** (the website). Results of any control
call always land in **Supabase**, never returned as the integration contract.

Identical in all three repos. Find your repo under "Per-repo surface".

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

### scorewise-engine — control surface · **TO REDESIGN (ADR-1)**
- **RETIRED:** `POST /api/ingest` (was scraper→engine *data*), the outbound webhook to the website.
- **Likely kept:** `GET /health`; a **trigger** to run a prediction batch (or a schedule / Supabase-watch instead of HTTP — the engine session decides); `/api/predictions` may remain as a convenience read, but the website reads Supabase.
- Auth `x-api-key: $SCOREWISE_API_KEY`.
**Produces:** `predictions` rows → **Supabase**. **Called by:** the website admin UI (to trigger a run), if a trigger endpoint is kept.

### scorewise-website — Next.js API + UI · **TO REDESIGN (ADR-4)**
- **Keeps:** admin proxies to the scraper control API (`/api/admin/scraper/*` → scrapamoja `/api/scraper/*`); a trigger to the engine if one exists.
- **RETIRED:** `/api/webhook/predictions`, `/api/webhook/result`, `engine-auto-sync` — data now comes from **Supabase** (Realtime), not webhooks/pull.
- Auth: NextAuth or **Supabase Auth** (ADR-4 open); RLS favors Supabase Auth.
**Reads:** betb2b + predictions from **Supabase** (Realtime). **Produces:** its own tables (group C) in Supabase.

## Who calls whom (control plane only)

    website admin ──HTTP──► scrapamoja /api/scraper/*   (queue/monitor scrapes)
    website admin ──HTTP──► engine trigger (TBD)         (run a prediction batch)
    (NO scraper→engine, NO engine→website HTTP — those are Supabase now)

## Conventions (all services)
- **Machine auth:** `x-api-key` header vs a per-service secret; fail closed (503 if unset, 401 if wrong).
- **`GET /health`** on every service (Railway healthcheck).
- **OpenAPI at `/docs`** for FastAPI services (scrapamoja, engine).
- A control call **triggers** work and returns a job/ack; the **result lands in Supabase** — never returned as the cross-service contract.
- Secrets live only in each repo's `.context/memory/secrets/` (gitignored), never in tracked files.

## Status
- **scrapamoja** control API: LIVE + documented (`/docs`).
- **engine** control surface: to redesign (ADR-1) — mainly *how a run is triggered*.
- **website** API: to redesign (ADR-4) — retire webhooks, keep admin proxies.
