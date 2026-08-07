# Current Task — none

**Status:** idle — last session: 2026-08-05 Session 39 (market naming + selection labels SOLVED; Supabase over-quota incident → 2 wipes → scheduled-only + read-only backoff shipped). Committed + pushed.

**Supabase state (2026-08-05):** DB **28 MB / 500 MB** (fine — wipe held) · **Egress 9.21 GB / 5 GB** (over — but it's a per-cycle flow, resets next cycle; ADR-23) · **grace period to 2026-09-06** (after which restrictions return 402/read-only). App degrades gracefully (read-only backoff, ADR-21 §1b) and is in **scheduled-only mode** (live OFF, `SCHED_LIVE_INTERVAL=0`) to keep both DB size + egress low.

**Next up (see tasks/backlog.md):**
- **Decide Pro vs stay-free before 2026-09-06** (ADR-21 §5 / ADR-23) — free tier viable only with live off + retention; full live needs Pro. Operator call.
- **Retention pass (ADR-22)** + **in-process last-odds dedup cache (ADR-23)** — both needed *before re-enabling live* on a metered plan (retention = DB size, cache = egress).
- **Fix results-fetch capture (ADR-20 addendum)** — capture `stat_game_id`/`entity.id` for ~every event so results work (today ~2%). HIGH when writable.
- live sub-game (G,GS,T) capture · MEC persistence to store · paripesa 203 · scheduler stats `529` watch.

**Done this session (39):** market-group naming (GS-indexed bets_model, ADR-19 addendum) + exotic selection-side labels (T-indexed `M` map) — 3 CDN tables + `fetch_market_names.py`. `markets` backfill ran on Supabase. App read-only-resilient (`e70f17a`). Two full wipes (2nd stuck via dashboard temp-write window; ADR-21 §4). Scheduled-only mode (live disabled when interval<=0; Railway default `SCHED_LIVE_INTERVAL=0`). Read-only write backoff (`store.is_read_only_error` + `scheduler._loop`, SQLSTATE 25006, ADR-21 §1b). ADRs 21/22/23 + ADR-19/20 addenda written. Gotcha: pooled Supabase role defaults to `default_transaction_read_only=on` — writes need `SET TRANSACTION READ WRITE` (handled in backfill scripts).
