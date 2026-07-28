# Shared DB Architecture — Supabase is the bus

**One Supabase Postgres instance is the shared data layer for all three ScoreWise
repos. Integration is DB-mediated: each service reads/writes the DB — never the
others directly** (no HTTP ingest, no webhooks between services).
Decisions: scrapamoja ADR-13/14 · scorewise-engine ADR-1/2/3 · scorewise-website ADR-4.

This file is identical in all three repos. Find your repo under "Per-repo role".
> **Engine refresh 2026-07-28 (ADR-2):** group B is now concrete (schema, indexes,
> RLS, Realtime). The other two repos' copies will pick this up on their next
> sync — until then their group B section still says "TO DESIGN" and they should
> treat this file as the source of truth.
>
> **Correction 2026-07-28 (ADR-3):** ADR-2's group-A read queries + group-B FK
> types were verified against scrapamoja's live schema (`src/sites/betb2b/models.py`,
> the DDL `create_all` builds in Supabase) and were **wrong** — assumed uuid ids,
> a `status`/`sport` column on `events`, and `TOTALS`/`MONEYLINE`/`OVER` values.
> §B-1/§B-6 below are corrected to the real schema: text `event_id`, integer
> `team_id`, status via `event_states`, lowercase enum values, H2H by `event_id`
> with `team1/team2_backend_id`. Fix the queries here before implementing them.

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
- **Dimensions:** `sports`, `countries`, `leagues`, `teams`, `markets`, `sub_games` (named per-period/per-stat groups — scrapamoja ADR-19)
- **Events:** `events` (`event_id` PK — backend id, shared across skins), `event_states` (time-series status/score/WP), `period_scores`
- **Odds:** `odds_snapshots` (one row per selection per run, change-only dedup; `market_id` → `markets`)
- **H2H:** `h2h_games`, `h2h_period_scores`
- **Meta:** `scrape_runs`, `scraper_jobs` (control-plane job queue + live `phase`), `statistics`

### B. predictions — owner: scorewise-engine  ·  status: DESIGNED (engine ADR-2, 2026-07-28)
Written by the engine, read by the website. Two tables — the durable output and the run/audit log.

#### B-1. `predictions` — durable, latest-wins output

One row per `(event_id, scope)`. PK `(event_id, scope)` — the ADR-10 keying, now durable. The engine writes by `INSERT … ON CONFLICT (event_id, scope) DO UPDATE SET … updated_at = now()`; the website reads by `SELECT * FROM predictions WHERE event_id = $1`. All columns map 1:1 to `PredictionOutput.to_dict()` so no reshape is needed at either end.

| Column | Type | Notes |
|---|---|---|
| `event_id` | **text**, FK→`events.event_id` | join key, shared across skins. NOT uuid — the betb2b backend id is text (e.g. `"738518814"`) — ADR-3 |
| `scope` | enum `prediction_scope` | `FULL_MATCH`, `FIRST_HALF`, `SECOND_HALF`, `QUARTER_1..4`, `HOME_TEAM_TOTAL`, `AWAY_TEAM_TOTAL` — exactly `engine.models.input.PredictionScope` |
| `home_team_id`, `away_team_id` | **bigint**, FK→`teams.team_id` | denormalised for the website's hot read path. NOT uuid — `teams.team_id` is an integer surrogate PK. (To bridge to H2H, map through `teams.backend_id` — the hash id H2H games reference.) — ADR-3 |
| `run_id` | uuid, FK→`prediction_runs.id`, nullable | the run that produced this row; NULL survives its run being pruned |
| `success` | bool, NOT NULL | false = engine rejected the input (validation errors) |
| `validation_errors` | text[], default `'{}'` | empty on success; populated when `success=false` — the row is stored either way |
| `recommendation` | enum `recommendation` | `OVER`, `UNDER`, `NO_BET`; nullable when `success=false` |
| `team_winner` | enum `team_winner` | `HOME_TEAM`, `AWAY_TEAM`, `NO_WINNER_PREDICTION`; nullable when `success=false` |
| `recommendation_confidence` | enum `confidence` | `HIGH`, `MEDIUM`, `LOW`; nullable |
| `team_winner_confidence` | enum `confidence` | same; nullable |
| `confidence` | enum `confidence` | backward-compatible aggregate per `output.py::from_context` (winner's conf when a winner is predicted, else recommendation's); kept because the website reads it today |
| `bookmaker_line` | numeric(6,1), CHECK `((bookmaker_line * 10) % 10) = 5` | the `.5` invariant enforced at the DB, not just in `s01_validate` |
| `over_odds`, `under_odds`, `home_odds`, `away_odds` | numeric(6,2), nullable | passthrough from `odds_snapshots` |
| `reduced_over_total`, `reduced_over_odds` | numeric(6,1) / numeric(6,2), nullable | set only when `recommendation = 'OVER'` (off-side dropped per `output.py`) |
| `reduced_under_total`, `reduced_under_odds` | numeric(6,1) / numeric(6,2), nullable | set only when `recommendation = 'UNDER'` |
| `average_rate` | numeric(7,2) | time-weighted mean of rate values (s04) |
| `matches_above`, `matches_below` | int | counts vs the line (s05) |
| `decrement_test`, `increment_test` | int | sensitivity test counts (s06) |
| `h2h_totals` | int[] | computed total per H2H game (s02) |
| `rate_values` | numeric(7,2)[] | `total − line` per H2H game (s03) |
| `winning_streak_data` | jsonb | the `WinningStreakData` struct verbatim (s07) — let the website reconstruct a prediction without re-running the engine |
| `created_at`, `updated_at` | timestamptz, default `now()` | `updated_at` bumped by `ON CONFLICT DO UPDATE` — the freshness column |

CHECK constraints:
- `((bookmaker_line * 10) % 10) = 5` (the `.5` line invariant)
- Off-side reduced-risk pair must be NULL: `(recommendation = 'OVER'  AND reduced_under_total IS NULL) OR (recommendation = 'UNDER' AND reduced_over_total IS NULL) OR (recommendation = 'NO_BET' AND reduced_over_total IS NULL AND reduced_under_total IS NULL) OR (success = false)`

#### B-2. `prediction_runs` — audit / control-plane log

One row per engine invocation. PK `id` (uuid). Admin-only (RLS). This is the durable replacement for the in-process `ingestion_count` counter that died on every Railway redeploy.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid, PK, default `gen_random_uuid()` | referenced by `predictions.run_id` |
| `triggered_by` | enum `prediction_run_trigger` | `website_admin`, `cron`, `manual`, `supabase_watch_future` |
| `source` | text, informational | `'supabase'` for the new path; retained for traceability with the old `_store["source"]` field |
| `started_at` | timestamptz, default `now()` | |
| `completed_at` | timestamptz, nullable | set when run finishes (success or failure) |
| `status` | enum `prediction_run_status` | `running`, `succeeded`, `failed` |
| `error` | text, nullable | set on `failed` |
| `stats` | jsonb | `{total, succeeded, failed, added, updated, store_total}` — same shape `IngestResponse` returns today, so the website's activity-log rendering is unchanged |

#### B-3. `scope` enum

`prediction_scope` enum values match `engine.models.input.PredictionScope` exactly — `FULL_MATCH`, `FIRST_HALF`, `SECOND_HALF`, `QUARTER_1`, `QUARTER_2`, `QUARTER_3`, `QUARTER_4`, `HOME_TEAM_TOTAL`, `AWAY_TEAM_TOTAL`. Engine writes the enum value as a string; the website reads it as a string; no enum drift across services.

#### B-4. Indexes

- `predictions` PK `(event_id, scope)` — the merge key, the lookup key, the website's primary access pattern.
- `predictions(run_id)` — "show me everything this run produced" (admin/debug).
- `predictions(updated_at DESC)` — the website's "fresh predictions" feed.
- `predictions(recommendation) WHERE recommendation IN ('OVER','UNDER')` — partial index for the "actionable bets" view (NO_BET rows skipped).
- `predictions(team_winner) WHERE team_winner IN ('HOME_TEAM','AWAY_TEAM')` — partial index for the "actionable winners" view.
- `prediction_runs(started_at DESC)` — recent-runs listing.

#### B-5. RLS + Realtime

- `predictions` — anon + authenticated read (predictions contain no secrets — odds and lines are public). Engine service role has write. No per-row policy (no user owns a prediction).
- `prediction_runs` — admin-only (Supabase Auth role `admin`). The website's admin dashboard reads it for the activity log; anon cannot.
- **Realtime:** the website subscribes to `predictions` changes **filtered by `event_id`** (per the conventions below — never whole-table subscriptions). A prediction landing in Supabase triggers a Realtime event; the website's match-detail page invalidates and refetches. No webhook, no `engine-auto-sync` healer (those are retired by ADR-1).

#### B-6. The engine's read queries over group A (INPUT side)

The engine reads group A, never writes it. The betb2b→`PredictRequest` mapping (formerly the scraper's exporter, scrapamoja ADR-7/8) is now engine-side. Full query plan + SQL in **ADR-2 §B-4 as CORRECTED by ADR-3** (verified against scrapamoja `src/sites/betb2b/models.py` — the live DDL). The queries below reflect the **actual** schema; the ADR-2 originals assumed a shape that does not exist:

1. **Eligible events** — `events` has **no `status` and no `sport`** column: status is the latest `event_states` row, sport is `sport_id` (3 = basketball). Values are `'not_started'/'live'/'finished'` — there is **no `'prematch'`**.
   ```sql
   SELECT e.event_id, e.home_team_id, e.away_team_id, e.start_time
   FROM events e
   JOIN LATERAL (SELECT status FROM event_states s
                 WHERE s.event_id = e.event_id
                 ORDER BY s.captured_at DESC LIMIT 1) st ON true
   WHERE e.sport_id = 3 AND e.start_time > now()
     AND st.status IN ('not_started','live')
   ORDER BY e.start_time ASC;
   ```
2. **Calculation + reduced-risk lines** — `market_type` is the **lowercase** enum value `'totals'`; selections are `'Over'`/`'Under'` (title-case); the odds column is **`price`** (not `odds`) and the timestamp is **`captured_at`** (not `recorded_at`). `odds_snapshots` is a change-only time-series with a `skin` column, so take the **latest** row per `(market_id, selection_name, line)`.
   ```sql
   SELECT os.line, os.price FROM odds_snapshots os
   JOIN markets m ON m.market_id = os.market_id
   JOIN LATERAL (SELECT max(captured_at) mx FROM odds_snapshots x
                 WHERE x.event_id=os.event_id AND x.market_id=os.market_id
                   AND x.selection_name=os.selection_name
                   AND x.line IS NOT DISTINCT FROM os.line) l ON os.captured_at = l.mx
   WHERE os.event_id = $1 AND m.market_type = 'totals' AND os.selection_name = 'Over'
   ORDER BY abs(os.price - 1.85) ASC;   -- reduced UNDER: selection_name = 'Under'
   ```
3. **Moneyline odds** — there is **no `'MONEYLINE'`** market_type; winner markets extract as `'1x2'` (3-way) or `'h2h'` (2-way, basketball). Selections are `'1'`/`'2'`/`'X'` — **no `'HOME'`/`'AWAY'`**. Map `selection_name='1'`→`home_odds`, `'2'`→`away_odds`. Latest by `captured_at`. Caveat: some basketball winner markets fall to `market_type='other'` (unmapped group `G=14` "To Win Match") — be lenient (see scrapamoja ADR-19 market-naming limits).
4. **H2H games** — `h2h_games` are stored **per event** already, so filter by `event_id` (no team-pair join): `SELECT * FROM h2h_games WHERE event_id = $1 ORDER BY date_start DESC LIMIT 100`. Participants are `team1_backend_id`/`team2_backend_id` (TEXT hash ids → `teams.backend_id`, **not** `team_id`); full scores are `score1`/`score2` (team1/team2). There are no `home_team_id`/`away_team_id`/`game_date`/`full_*_score` columns.
5. **H2H scope aggregation** — `h2h_period_scores` has `h2h_game_id` (int FK, **not** `game_id`), `period_key` (int) + `period_name` (text), and `home_score`/`away_score` = **team1/team2** scores. Period keys: 18–21 = quarters 1–4, 1/2 = 1st/2nd half, 22/23 = OT. So: FULL → `score1`/`score2`; `QUARTER_n` → `period_key IN (18,19,20,21)`; `FIRST_HALF` → `period_key=1` if present else `18+19`; `SECOND_HALF` → `period_key=2` else `20+21`. `HOME_TEAM_TOTAL` → the **event home team's** score per game via `CASE WHEN h.team1_backend_id = <event home team's teams.backend_id> THEN score1 ELSE score2 END`, zero the other; `AWAY_TEAM_TOTAL` mirrors. Bulk-fetch with `WHERE h2h_game_id = ANY($1::int[])` (ids are **int**, not uuid).

The pooler-safe connection settings are non-negotiable: `postgresql+psycopg`, port `6543`, `connect_args={"prepare_threshold": None}`, `pool_pre_ping`. Same as scrapamoja's `src/core/db.py` (its ADR-13). Synchronous psycopg calls are wrapped in `asyncio.to_thread` so the FastAPI event loop is never blocked.

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
- **scorewise-engine** — **read A, compute, write B**. You own the betb2b→`PredictRequest` mapping: match_total = the totals rung whose over-odds is nearest **1.85**; H2H per scope (FULL scores; QUARTER/HALF period aggregates; HOME/AWAY_TEAM_TOTAL zero the other team). Schema + read-query plan pinned down in ADR-2 §B and **corrected to the live scrapamoja schema by ADR-3** (text `event_id`, bigint `team_id`, status via `event_states`, lowercase market types, H2H by `event_id`). (ADR-1, ADR-2, ADR-3.)
- **scorewise-website** — **read A + B, write C**, render. Full redesign around this schema; Realtime for live odds + scrape `phase`; Supabase Auth + RLS. (ADR-4.)

## Status snapshot
- **A (betb2b):** LIVE in Supabase — verified end-to-end (one run: 18 events / 2,041 odds / 102 h2h games).
- **B (predictions):** DESIGNED (engine ADR-2/3, 2026-07-28) — schema, indexes, RLS, Realtime, and the betb2b read queries are pinned down. ADR-3 corrected ADR-2's FK types (text `event_id`, bigint `team_id`) + all 5 read queries against scrapamoja's live `models.py` — the ADR-2 originals assumed a shape that does not exist. Implementation lands in the next feature-engineer session; until then the engine still runs its old HTTP ingest + disk-store path. The other two repos' copies of this file will be synced externally.
- **C (website tables):** designed during the website redesign.
