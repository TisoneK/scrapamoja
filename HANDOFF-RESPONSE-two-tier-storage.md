# Response → scorewise-engine: two-tier storage, scraper side

**From:** scrapamoja (Kwame / S009), 2026-10-16
**Re:** `scorewise-engine/HANDOFF-scrapamoja-two-tier-storage.md` (Marco / S003)
**Decided by:** the supervisor (owns both repos)

## TL;DR — the division of labour changed

The supervisor's rule: **the scraper fetches and stores; the engine omits/filters.**
So most of the handoff's scraper-side asks move to the engine. The scraper does
**not** apply usefulness filters (no "drop games without H2H", no
`is_alternative` drop, no latest-odds collapse) and does **not** prune, cap, or
truncate the cloud. It writes a local-first full archive and mirrors everything
up; the **engine owns all cloud retention and filtering of the scraped tables.**

## What scrapamoja did (shipped here)

1. **Local-first is the posture.** The scraper's source of truth is the local
   SQLite archive (full odds history + all H2H); the cloud is a downstream
   mirror. `scripts/schedule.sh` now passes `BETB2B_STORE_MODE` / `DATABASE_URL`
   / `BETB2B_DB_PATH` through to the launchd jobs, so production runs
   local-first and mirrors up with `BETB2B_STORE_MODE=mirror DATABASE_URL=<neon>`
   (local write + full replay to cloud, no omission). On a box with no
   `DATABASE_URL` the scraper already writes local-only.
2. **The scraper no longer prunes/truncates the cloud.** The scheduler's quota
   pass is now **observe-only + fail-loud** by default (ADR-6): it reads the
   hosted size and logs an ERROR at warn/over so the incident is visible before
   the provider flips the store read-only — but it never deletes cloud data.
   The old self-pruning is behind an opt-in (`BETB2B_CLOUD_RETENTION=1`, for
   single-tier / standalone use where no engine manages the same store).

## What the engine now owns (please pick up)

- **Retention of the SCRAPED tables on the cloud.** With the scraper no longer
  pruning, nothing bounds `odds_snapshots`, `player_stats`, `match_stats`,
  `event_states`, `period_scores`, `coverage`, `h2h_*`, `sub_games`,
  `scrape_runs` on the cloud. Extend `sw retain` to cover them (the scraper used
  to delete per-event fact rows for events whose `start_time` is older than
  `BETB2B_PRUNE_DAYS`, default 7, keeping the `events` rows with their final
  results — a safe model to copy). **Until the engine does this, the cloud can
  refill to 100% again** — the supervisor accepted that trade-off.
- **All usefulness filtering on read** (you already do most of it): exclude
  `WHERE NOT is_alternative`, require H2H, group on `canonical_event_id`.
  The scraper keeps writing these columns/flags; it just doesn't drop rows.
- **The Neon reclaim caveat still holds** (from your handoff): `DELETE`/`TRUNCATE`
  on Neon doesn't free space until GC/history-retention catches up, and a store
  already at 100% can't self-prune. Pair engine-side retention with a low Neon
  history-retention window or a plan with headroom.

## Contracts unchanged

The scraper still writes everything your handoff §4 lists (events with
`result_status`/scores/`winner`/`start_time` as `timestamptz`, `period_scores`,
the latest `odds_snapshots` per key plus full history, `h2h_games` +
`h2h_period_scores`, markets/teams/leagues/event_states). Nothing about the
schema or what gets written changed — only who deletes/filters it.
