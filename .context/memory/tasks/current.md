# Current Task — none

**Status:** idle — last session: 2026-08-05 Session 39 (market-group naming SOLVED via GS-indexed bets_model, ADR-19 addendum), committed + pushed.
**Next up (see tasks/backlog.md):** **HISTORICAL Supabase cleanup (operator-gated, ~2.1M rows)** — backfill `odds_snapshots.selection_name` placeholders (`G=<n> T=<n>` → real side via `raw_t`) + fix the stale `market_id=5` "To Win Match"→"Total Even" and its 53894 odds sides · live sub-game (G,GS,T) capture for quarter/half scopes · results-pass engine grading (ADR-16/20) · MEC persistence to store · paripesa 203 · scheduler stats `529` watch.
**Done this session (39):** market-group naming SOLVED (GS-indexed bets_model) + exotic selection-side labels (T-indexed `M` map) + backfill of existing `markets` rows RUN on Supabase (93 `G=<n>` renamed). Note: pooled Supabase role defaults sessions to `default_transaction_read_only=on` — writes need `SET TRANSACTION READ WRITE` (handled in `backfill_market_names.py`).
