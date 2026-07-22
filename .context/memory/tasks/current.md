# Current Task — Idle

**Status:** Idle — no session in progress.

Session 27 (2026-07-22, GitHub Copilot / DeepSeek V4 Flash Free) fixed a
data-quality bug in the exporter: `_h2h_for_scope()` was sending full match
scores for HOME/AWAY_TEAM_TOTAL scopes, causing the engine to compute wrong
totals (full game vs individual line) → false HIGH predictions. Fix was 4
lines (zero-out non-relevant team's score). Committed at `20eda23`.

**Lesson for all future sessions:** Structured validation (fields present,
types correct) is NOT enough — you must simulate the downstream computation.
The engine always sums home+away. For team-total scopes, the sum must equal
only the relevant team's score. See ADR-8 for the H2H scope contract rule.

**Backlog items for the next agent:**

1. **Add semantic validation test for exporter** — parametrize over all 9
   scopes, asserting `home_score + away_score` equals the scope-relevant
   number. Add to the existing betb2b test suite.
2. **Map basketball quarter/half/individual-total market groups (G ids) in
   `markets.py`** — unblocks non-full scopes for the scoped ingestion path.
3. **Map the uncertain (G,T) market groups** — G=8/T=4,6; G=91/T=755,757;
   G=92/T=766,767; G=27/T=424-426 (from ADR-7 implementation notes).
4. **Build the `(G,T)` keyed lookup** in `rules.py::lookup_market` with
   fallback chain: `(G,T)` → T-only → G-only (from ADR-7 implementation notes).
5. **Wire the scoped sub-game fetching into the scraper** — `SG[]` enrichment
   with PredictionScope tags (from ADR-7 implementation notes).
6. **Re-ingest with `--ingest`** now that the team-total H2H bug is fixed,
   to refresh the engine's database with correct scores.

References: `reviews/2026-07-22-review.md`, `plans/decisions.md` ADR-7 + ADR-8.
