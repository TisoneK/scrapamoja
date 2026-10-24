# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Carry-over — the standing technical decisions of the previous office (2026-10-03)
- **Status:** accepted
- **Context:** the office closed; its ADRs are frozen in `history/office-001/plans/decisions.md`, which the new office does not read at session start.
- **Decision:** the following stay in force: control plane via Dockerfile with no scrape jobs in the API; transport separate from extraction mode; DOM extraction is the primary BetB2B path and the rotating auth header is never chased in code; `GetGameZip` is the market-depth path and the discovery pipeline is proxy-free; scraped odds live in a structured time-series store (local SQLite default, any Postgres optional, a stored match is scraped once); event ids are not stable across skins or time, sub-games are not matches, failed is not empty; team-total scopes zero the other team's H2H score; every request path goes through the security guard and is paced; a real browser may clear a vendor challenge but its JS is never reimplemented; hosted stores need retention and a quota monitor; import health is a tested invariant.
- **Consequences:** reverse any of these only with a new ADR that supersedes this one. Per-decision rationale and evidence: `history/office-001/plans/decisions.md`.

---
## ADR-2: Geo-restricted machines never load a site's pages without a proxy (2026-10-04)
- **Status:** accepted
- **Context:** betting sites country-block whole countries by redirecting a *page* request (HTTP 203 to `/en/block`); their data feeds are not country-gated. A browser/hybrid run from a blocked connection was recorded as a `geo_block` against the machine, and the per-site cooldown then also stopped the direct feed runs. An unattributed run on the operator's US Mac produced exactly this on 2026-10-04.
- **Decision:** on a machine outside the allowed countries, nothing loads a site's pages (browser bootstrap, DOM render, hybrid-mode scrape, profile warm-up, probe/compare/discover scripts, "testing the site") unless traffic goes through the allowed-country proxy. Data is fetched only on the page-free path (`scrape ... --direct`). Enforced in code (`src/security/egress.py`): `SCRAPAMOJA_GEO_RESTRICTED=1` in the machine's `.env`, or a page-level country block seen without a proxy (learned marker beside the block ledger), makes the browser paths raise `PageLoadsRefused`. A page-level geo-block without a proxy switches page loads off for the site and no longer starts a cooldown, so the feed path keeps running. `python -m src.security status|clear <site>` shows/lifts it.
- **Consequences:** agents must not unset the variable, clear the marker, or route around the refusal to make a run proceed; a task that needs a browser is handed to an allowed-country machine (the Kenyan machine, `docs/proposals/KENYA_MACHINE_BRIEF.md`). Tests must use offline fixtures. Feed-level geo-blocks still rest the site. Full rule: `overrides/project-guide.md` (BetB2B rule 18); standing override in `overrides/rules.md`.

---
## ADR-3: Store everything the source offers, and record what was offered, absent or never asked (2026-10-04)
- **Status:** accepted
- **Context:** the consumer needed totals lines for every subject x period, unambiguous labels, period scores, and gaps it could trust. A default scrape only fetched the main game, so "the source has none" and "we never looked" were indistinguishable; H2H was stored for ~28% of events although the source returns it for ~70%; the statistics table was empty because the feed is empty before a match.
- **Decision:** sub-games (periods and per-stat groups) are fetched by default and stored under a scope (`QUARTER_n`, `FIRST_HALF`, `SECOND_HALF`, `STAT_<NAME>[__<PERIOD>]`); every odds row carries `subject` (MATCH/HOME_TEAM/AWAY_TEAM, totals ladders only) and `period` (FULL_TIME/HALF_n/QUARTER_n/PERIOD_n) from one vocabulary (`src/sites/betb2b/labels.py`); H2H periods use QUARTER_n/HALF_n/OVERTIME_1 and a missing score stays empty (never filled with 0); a `coverage` table records, on change only, `offered | not_offered | not_attempted | fetch_failed` per subject x period, and for `h2h`, `stat_id`, `result`, `result_periods`, `match_stats`; played matches get final + per-period scores and team/player statistics (`match_stats`, `player_stats`) from a post-match pass; matches the source never resolves within a week are marked `result_status = -1`. Both stores (SQLite and ORM/Postgres) implement all of it.
- **Consequences:** a gap now means something; do not omit rows or switch a step off because it returns nothing — find out why (the statistics feed needed a post-match pass, not removal). New datasets get a coverage row. H2H history is not per-bookmaker and is stored once across skins; odds are per skin.

---
## ADR-4: Skip what is already stored, and remember the source's "no data" (2026-10-04)
- **Status:** accepted (skip basis amended 2026-10-16 by ADR-5)
- **Context:** re-scrapes re-probed every event (in-scrape H2H/stat-id steps, the stat-id backfill), doubled the H2H history, dumped hundreds of events of JSON to the terminal, and a hard timeout discarded a whole pass.
- **Decision:** a stored match is not fetched again by default (`--refetch` / `--skip-processed SECONDS` override; live scrapes are never filtered); a stored match whose totals coverage is `fetch_failed`/`not_attempted` is fetched again at most hourly; H2H and stat-id probes skip events that already have the data or got a "no data" answer in the last 24 h (`probe_state`, `probe_filter`); a re-scrape stores each H2H game once per result; a timeout keeps the events already fetched and reports the rest as failed ids; `scrape` prints a short summary (`--json` / `--output FILE` for the data).
- **Consequences:** odds of stored matches do not refresh (and line movement does not accumulate) unless `--skip-processed SECONDS`/`--refetch`; (the "skip list is per match, not per skin" clause was superseded by ADR-5).

---
## ADR-5: The skip filter is per skin (2026-10-16)
- **Status:** accepted (amends ADR-4)
- **Context:** BetB2B-family brands price their own odds (margins differ per skin), so a second skin's stored match is not this skin's data — yet the skip basis was "a match any skin stored", which left melbet/22bet/linebet with no odds of their own for everything an earlier skin had stored; the only workaround (`--skip-processed SECONDS`) was a full re-fetch (backlog B-2026-10-04-1).
- **Decision:** "already stored" in the skip filter means stored **by the running skin**: `store.unprocessed_ids(..., skin=...)` reads `event_states` (one row per run per skin) for last-seen, and that skin's `coverage` rows for the incomplete-retry rule; both the CLI (`--skip-processed` path) and the scheduler's scheduled pass pass their skin. Sub-game knowledge and the H2H/stat-id probe memory stay skin-independent. The raw store API without `skin` keeps the cross-skin basis (tools/tests).
- **Consequences:** the first run of each skin fetches the full discovered set once to lay down its own odds (~9 min / ~1,500 requests per skin — the same cost the old workaround had, minus the H2H/stat-id re-probes); work-sharing across machines sharing one remote store still holds, per skin.

---
## ADR-6: Two-tier storage — scraper stores, engine owns cloud retention/filtering (2026-10-16)
- **Status:** accepted
- **Context:** the shared cloud Postgres (Neon `betb2b`, ~1 GB) hit 100% and silently broke the engine — a full Postgres fails every write (`DiskFull` / read-only 25006), so grading `UPDATE`s rolled back and picks never settled. `odds_snapshots` was the hog (~762 MB, ~3.4M rows, unbounded). The engine's handoff (`HANDOFF-scrapamoja-two-tier-storage.md`, Marco/S003) asked the scraper to write local-first and push a lean, H2H-qualified, latest-odds-only, size-capped set to the cloud. The supervisor (owns both repos) instead ruled on the division of labour: **the scraper fetches and stores; the engine omits/filters.**
- **Decision:** the scraper is local-first (local SQLite = full archive: all odds history + all H2H) and mirrors everything to the cloud with **no omission** — no H2H / `is_alternative` / latest-odds filtering — and it never prunes, caps or truncates the cloud. The scheduler's quota pass is **observe-only + fail-loud** by default (reads the hosted size, logs an ERROR at warn/over, deletes nothing); the old self-pruning / hard-truncate escalation is gated behind `BETB2B_CLOUD_RETENTION=1` for single-tier / standalone use (`quota.retention_enabled` / `quota.retention_action`). The **engine** owns cloud retention and filtering of the scraped tables (extend its `sw retain`) and all usefulness filtering on read. `scripts/schedule.sh` passes `BETB2B_STORE_MODE` / `DATABASE_URL` / `BETB2B_DB_PATH` through so production runs local-first + full mirror (`BETB2B_STORE_MODE=mirror`).
- **Consequences:** until the engine extends `sw retain` to the scraped tables, the cloud can refill to 100% again — the supervisor accepted this trade-off. The scraper keeps writing `is_alternative` / `canonical_event_id` / `superseded_by` and both latest and historical odds; it just never drops rows. This refines ADR-1's "hosted stores need retention + a quota monitor" for the two-tier case: the monitor stays (observe + fail loud), the retention *action* moves to the engine. The Neon reclaim caveat (DELETE/TRUNCATE don't free space until GC; a 100% store can't self-prune) is now the engine's to pair with a low history-retention window. Response to the engine: `HANDOFF-RESPONSE-two-tier-storage.md`. Reverse only with a new ADR.

---
## ADR-7: Local-Postgres cutover — the scraper writes the shared local Postgres, not Neon (2026-10-24)
- **Status:** accepted (executes the ADR-6 target)
- **Context:** the Neon cap (1024 MB) kept the pipeline frozen — nothing wrote to the cloud after 2026-10-16 ~18:15 UTC, the scraper's own writes hit `DiskFull`, and the engine had 184 failed grade jobs. The engine (Samir/S006, `HANDOFF-scrapamoja-local-postgres-cutover.md`) moved both sides to one shared local Postgres (`postgresql://bao@localhost:5432/scorewise`, Postgres.app 18 on the Mac mini), seeded by a `pg_dump`/`pg_restore` of Neon, and repointed its own `DATABASE_URL`. Neon becomes a lean downstream fed only by the engine's local→remote push. The engine could not find where the scheduled scraper resolved its DB URL (plists, `launchctl getenv`, repo-root `.env`, `schedule.sh` all empty) yet the jobs still reached Neon.
- **Decision:** repoint the scraper's `DATABASE_URL` to the shared local Postgres. The resolution point the engine couldn't see is the **gitignored `src/sites/betb2b/.env`**, loaded by the CLI at `src/sites/betb2b/cli/main.py:32` (before the repo-root `.env`); it held the Neon URL. Changing that one line repoints both the on-demand and scheduled (`com.scrapamoja.*`) paths — the plists set no `DATABASE_URL`, and `_normalize` auto-pins bare `postgresql://` to psycopg v3. Old Neon URL parked as a comment there for rollback. The scraper does not push to cloud (ADR-6: engine owns the push + `sw retain`).
- **Consequences:** fresh odds/results now land in local Postgres on the scheduled cadence (verified 2026-10-24: 3 `scrape_runs` + 191 event results written locally). `DATABASE_URL` resolving from `src/sites/betb2b/.env` is the canonical scraper DB-URL source on an operator machine — future "where does it connect?" questions start there, not the plists. The scraper's local SQLite stores are now unused (it's on local Postgres, not the SQLite fallback). Rollback: restore the parked Neon line. Response to the engine: `HANDOFF-RESPONSE-local-postgres-cutover.md`.

