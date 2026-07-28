# Shared DB Architecture — Supabase is the bus

**One Supabase Postgres instance is the shared data layer for all three ScoreWise
repos. Integration is DB-mediated: each service reads/writes the DB — never the
others directly** (no HTTP ingest, no webhooks between services).
Decisions: scrapamoja ADR-13/14 · scorewise-engine ADR-1 · scorewise-website ADR-4.

This file is identical in all three repos. Find your repo under "Per-repo role".

## Data flow

    scrapamoja/betb2b ──write──►  ┌───────────────┐  ◄──read──  scorewise-website
                                  │   Supabase     │             (+ writes its
    scorewise-engine ─read/write─►│  (shared DB)   │              own tables)
                                  └───────────────┘

- **scrapamoja (scraper)** WRITES the betb2b tables (odds/events/h2h). Reads nothing from the others.
- **scorewise-engine** READS betb2b odds/h2h/events, WRITES the `predictions` table. No `/api/ingest`, no webhook.
- **scorewise-website** READS betb2b + predictions, WRITES its own tables (users/overrides/…). UI + admin.

## The schema — three groups, by owner

### A. betb2b tables — owner: scrapamoja  ·  status: LIVE
Written by the scraper's persist path (scrapamoja ADR-6/13). Read by engine + website.
- **Dimensions:** `sports`, `countries`, `leagues`, `teams`, `markets`
- **Events:** `events` (`event_id` PK — backend id, shared across skins), `event_states` (time-series status/score/WP), `period_scores`
- **Odds:** `odds_snapshots` (one row per selection per run, change-only dedup; `market_id` → `markets`)
- **H2H:** `h2h_games`, `h2h_period_scores`
- **Meta:** `scrape_runs`, `scraper_jobs` (control-plane job queue + live `phase`), `statistics`

### B. predictions — owner: scorewise-engine  ·  status: TO DESIGN (engine ADR-1)
Written by the engine, read by the website.
- **`predictions`:** PK `(event_id, scope)`; `event_id` FK → `events`; `recommendation` / `team_winner` + confidences; calculation line (over/under total + odds); result fields.
- **scope enum:** `FULL_MATCH`, `FIRST_HALF`, `SECOND_HALF`, `QUARTER_1..4`, `HOME_TEAM_TOTAL`, `AWAY_TEAM_TOTAL`.

### C. website-owned tables — owner: scorewise-website  ·  status: TO DESIGN (website ADR-4)
Written + read by the website; NOT part of betb2b.
- `users` (+ Supabase Auth), admin overrides (reduced-risk lines, bet codes), manual results, service config, activity logs.

## Ownership matrix (write / read)

| Table group        | scrapamoja | scorewise-engine | scorewise-website |
|--------------------|:----------:|:----------------:|:-----------------:|
| A. betb2b          |  **WRITE** |       read       |        read       |
| B. predictions     |     —      |     **WRITE**    |        read       |
| C. website-owned   |     —      |        —         |  **WRITE + read** |

## Conventions (all repos)
- **Connect via the Supabase pooler** (pgBouncer, port `6543`); SQLAlchemy driver `postgresql+psycopg`; `connect_args={"prepare_threshold": None}` + `pool_pre_ping`. Reference impl: scrapamoja `src/core/db.py` (ADR-13).
- **Join key = `events.event_id`** (the betb2b backend id, shared across skins) — the match key everywhere. `predictions` and website tables reference it.
- **RLS:** client apps read-only on A + B; admin broader; C behind auth.
- **Realtime:** subscribe to *filtered* changes (a specific event/match), not whole tables — `odds_snapshots`, `predictions`, `scraper_jobs`.
- **Writes are synchronous psycopg** — do them off the request/event loop (scrapamoja runs persist via `asyncio.to_thread`) and **batch** inserts (`executemany`) to avoid per-row round-trips.

## Per-repo role ("where you fit")
- **scrapamoja** — you are the **producer of group A**. Write clean betb2b rows to Supabase; do NOT call the engine or website. (ADR-13 store cutover, ADR-14 DB-mediated link.)
- **scorewise-engine** — **read A, compute, write B**. You own the betb2b→`PredictRequest` mapping: match_total = the totals rung whose over-odds is nearest **1.85**; H2H per scope (FULL scores; QUARTER/HALF period aggregates; HOME/AWAY_TEAM_TOTAL zero the other team). (ADR-1.)
- **scorewise-website** — **read A + B, write C**, render. Full redesign around this schema; Realtime for live odds + scrape `phase`; Supabase Auth + RLS. (ADR-4.)

## Status snapshot
- **A (betb2b):** LIVE in Supabase — verified end-to-end (one run: 18 events / 2,041 odds / 102 h2h games).
- **B (predictions):** schema is the next task (design in the engine repo; scrapamoja + website reference it).
- **C (website tables):** designed during the website redesign.
