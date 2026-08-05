# Current Task — none

**Status:** idle — last session: 2026-08-05 Session 39 (market-group naming SOLVED via GS-indexed bets_model, ADR-19 addendum), committed + pushed.
**Next up (see tasks/backlog.md):** exotic selection-SIDE labels from bets_model `M` map (optional) · live sub-game (G,GS,T) capture for quarter/half scopes · results-pass engine grading (ADR-16/20) · MEC persistence to store · paripesa 203 · scheduler stats `529` watch.
**Done this session (39):** market-group naming SOLVED (GS-indexed bets_model) + backfill of existing rows RUN against Supabase (93 `G=<n>` markets renamed, 0 remaining). Note: the pooled Supabase role defaults sessions to `default_transaction_read_only=on` — writes need `SET TRANSACTION READ WRITE` (now handled in `backfill_market_names.py`).
