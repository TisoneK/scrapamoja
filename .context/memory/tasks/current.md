# Current Task — Session 28 (in progress)

**Agent:** Claude Code / claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7)
**Started:** 2026-07-22

**Target:** Work the Session 27 handoff — close the regression-test gap left by
the `_h2h_for_scope` team-total fix (`20eda23`, shipped with no test), and
reconcile the stale backlog items in the prior `current.md` against what
Session 26 already shipped.

**Plan:**
1. Semantic validation test for the exporter — parametrize all 9 scopes and
   assert `home_score + away_score` equals the scope-relevant number (the
   engine's `s02_h2h_totals` computation), including the orient-then-zero
   ordering for reversed H2H games.
2. Verify handoff items 2–5 (market `(G,T)` map, `lookup_market` fallback
   chain, sub-game scope wiring) — all appear already shipped in Session 26.
3. Review the exporter for other instances of the same bug class
   (structurally-valid output that the engine computes wrongly).

**Baseline:** `.venv/bin/python -m pytest src/sites/betb2b/tests/ --no-cov`
→ 148 passed in 3.51s. `ruff check src/sites/betb2b/` → 563 pre-existing errors
(not introduced by this session; the `[tool.ruff] select` key is deprecated in
the installed ruff, so the project's ignore list is not being applied).
