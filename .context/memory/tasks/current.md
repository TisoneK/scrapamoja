# Current Task — Idle

**Status:** Idle — no session in progress.

Session 26 (2026-07-21, Claude Code) investigated betb2b DB → scorewise-engine
scoped ingestion. Result: ADR-7 (design) + store now captures H2H per-quarter
scores (`d0117eb`, new `h2h_period_scores` table) — the enabling gap for
QUARTER/HALF/TEAM scopes. FULL_MATCH ingestion is buildable now.

**Next agent:** two backlog items carry the work forward —
1. Map basketball quarter/half/individual-total market groups (G ids) in
   `markets.py` — unblocks non-full scopes.
2. Build the scorewise-engine ingest exporter (ADR-7): betb2b Event → N
   PredictRequests (one per scope) → POST /api/ingest.
Engine contract + scope details in `plans/decisions.md` ADR-7.
