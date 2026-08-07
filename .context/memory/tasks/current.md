# Current Task — none

**Status:** idle — last session: 2026-08-05 Session 39 (market naming + selection labels SOLVED; prod over-quota incident → fresh-start wipe). Committed + pushed.

**BLOCKER (operator action):** Supabase is **read-only until you lift it in the dashboard**. Post-wipe the DB is 11 MB (under the 500 MB limit) but `transaction_read_only` was still `on`; click "restore"/disable read-only on the Supabase banner. Until then the app serves reads only — no scraping/results/writes. (See ADR-21.)

**Next up (see tasks/backlog.md), all gated on the read-only lift:**
- **Build `odds_snapshots` retention (ADR-22)** — MANDATORY; the unbounded tick history is what blew past the free-tier quota (1.3 GB/week). HIGH.
- **Fix results-fetch capture (ADR-20 addendum)** — capture `entity.id`/`stat_game_id` for (nearly) every event so results actually work; today only ~2% of events get results. HIGH.
- live sub-game (G,GS,T) capture for quarter/half scopes · MEC persistence to store · paripesa 203 · scheduler stats `529` watch.

**Done this session (39):** market-group naming SOLVED (GS-indexed bets_model, ADR-19 addendum) + exotic selection-side labels (T-indexed `M` map) — three CDN tables under `data/` + `fetch_market_names.py` regenerator. `markets` backfill RAN on Supabase (93 `G=<n>` renamed) before the wipe. App made read-only-resilient (`e70f17a`). Fresh-start wipe executed (ADR-21). **Scheduled-only ingestion mode shipped** (ADR-22): live pass disabled when interval<=0; Railway worker now defaults `SCHED_LIVE_INTERVAL=0` (live OFF = low-storage); set it to `15` on a paid tier to re-enable live/full categories. ADRs 21/22 + ADR-19/20 addenda written. Gotcha: pooled Supabase role defaults to `default_transaction_read_only=on` — writes need `SET TRANSACTION READ WRITE` (handled in the backfill scripts).
