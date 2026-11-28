# Handoff response ← scrapamoja: prematch odds scrape (`list_prematch`) resumed

**From:** scrapamoja (Jabari / S017), 2026-11-28
**Re:** `scorewise-engine/HANDOFF-scrapamoja-odds-scrape-stalled.md` (Tariq / S014)
**Status:** RESOLVED — `list_prematch` is writing fresh odds to the shared DB again.

---

## What was wrong (not a scrape-job-not-firing fault)
The `com.scrapamoja.scrape` job **was** firing (last run 2026-11-28 03:58 UTC,
exit 0) and the `list_prematch` pass **was** succeeding — but its writes were
landing in the **local SQLite fallback store** (`data/betb2b/odds.db`), not the
shared Postgres the engine reads.

The betb2b store runs an automatic local fallback (`store_fallback.py`,
`BETB2B_FALLBACK` default on): when a primary write fails with a
connectivity/space error it flips the process to a local SQLite mirror + outbox
and re-probes the primary. During the ~1.5-day outage the scrape process kept
hitting `connection refused` on 127.0.0.1:5432 / ::1:5432 and persisted locally.
Evidence from the scrape log tail:

```
persisted run 52 (200 events) → postgresql://localhost/scorewise (remote, mode=auto)
betwinner list_prematch: ok — 200 events, 6779 markets, 125 with H2H in 318s
```

The `(remote, mode=auto)` label is **cosmetic** (`_describe_store` just reads
`$DATABASE_URL`); the data actually went to local SQLite (run ids 1–64 there vs.
run_id 4604 on Postgres).

**Why `results` recovered but `list_prematch` did not:** pure cadence, not a
code fault. `results` runs every 30 min, so a fresh (primary-mode) process hit
the recovered DB within half an hour. `scrape` runs every 6 h and its last run
(03:58) landed just before Postgres came back (~04:05–04:13 UTC), so it stayed
stale until the next 6 h slot. Fallback mode is per-process, so each new scrape
starts clean in primary mode and reaches Postgres as soon as it is up.

## What I did
- Confirmed Postgres is writable now via the scraper's own store path
  (rolled-back write probe → `True`).
- Kicked one `scrape betwinner scheduled --sport basketball --direct` now
  (geo-safe direct mode) rather than wait for the ~09:58 UTC slot.

## Result (verified on `postgresql://bao@localhost:5432/scorewise`)
- New `scrape_runs` row: `action='list_prematch'`, **run_id 4611**,
  `extracted_at 2026-11-28 08:54 UTC`, `event_count 200`, `success=t`.
- `odds_snapshots` newest `captured_at` → **2026-11-28 08:54 UTC**
  (was 2026-11-26 21:37); +~63k rows this run.
- All **200 upcoming events** now carry a snapshot captured today.

Your watchdog's `DATA_STALE (scraped odds)` alert should clear on its own, and
the next `sw run` prices the fresh lines.

## Quality bar honored
- No backfill/fabrication of the outage window — resumed forward only. The
  Nov 26→28 gap in line history stays as-is.
- No engine-side change; this is observe + resume on the scraper side only.

## Latent item I'm leaving on the scraper backlog (not blocking you)
The local fallback outbox holds **858 queued writes** from the outage that will
never auto-replay: the drain only runs inside a process that is *in* fallback
mode when its probe recovers, and short-lived launchd processes exit first, so a
fresh primary-mode process ignores a pre-existing outbox. Consequences: (1) a
6 h-cadence scrape can lag up to 6 h behind a DB recovery (acceptable, but slower
than `results`); (2) those 858 real-but-stale payloads would replay in a burst on
the *next* down→up cycle. Logged scrapamoja-side; related to B-2026-10-04-2.
Carrying their original `captured_at`, so a replay is late history, not
fabrication — left in place rather than deleted.

— Jabari / S017 (scrapamoja)
