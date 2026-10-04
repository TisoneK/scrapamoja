# Parking Lot (deferred knowledge — not a queue)

The backlog is a work queue you act on; this file is the knowledge base
you **don't** act on yet. Research findings, open design questions,
advisory "should we…?" items, deferred work, and someday ideas live here
so the backlog stays a queue an agent can actually work from. Nothing
here is urgent, nothing here is capped, and nothing here blocks a gate.
The record of a finding is its own row plus the commit / session entry
that produced it; git history keeps every row, so promoting or dropping
one loses nothing.

**One rule keeps the two files honest: a parking-lot row is not a task.**
If an item becomes actionable — it now has a clear next step and someone
to take it — **promote** it: cut the row here, add an actionable row to
`backlog.md` (a fresh `B-` ID, one line, pointing back at this row's `P-`
ID if the context matters), and leave it here only as a one-line
"→ promoted to B-… " stub if you want the breadcrumb. An item that turns
out to be wrong or moot is just deleted — history remembers it.

Every row gets a stable **ID** — `P-<added YYYY-MM-DD>-<n>`, n = that
date's next sequence in the file — and a **Summary** cell with enough
context that a future session can pick it up cold. Keep status
qualifiers in the text ("advisory", "needs a decision", "blocked on X",
"deferred by owner"). There is **no cap** here and **no priority** —
items are grouped by *kind*, because the whole point is that these are
not competing for the top of a queue.

This file belongs to the **current office**. When the office closes, the
parking lot is **not** re-seeded wholesale: the closing session promotes
what is now actionable into the new backlog and records the rest in the
permanent record (`history/office-<NNN>.md`, "Open threads"). A cold
idea earns its way into the next office by becoming work, not by being
copied.

Full spec: `.context_ledger/core/schemas/ledger-schema.md` →
"The parking lot".

## Findings

What we learned that isn't work yet — observations, measurements, root
causes, "the current design does X because Y".

| ID | Summary |
|----|---------|

## Open questions

Advisory questions, decisions still up for grabs, "should we…?" — a
question is not a task until it has an owner and a next step (then it
becomes a backlog row or an ADR in `plans/decisions.md`).

| ID | Summary |
|----|---------|

## Deferred work

Real tasks, consciously parked — not now, but keepable. This is where a
backlog row goes when the cap forces a prune and the item still matters:
out of the queue, not into the void.

| ID | Summary |
|----|---------|
| P-2026-10-04-1 | (moved from the backlog at the cap, 2026-10-04; was B-2026-10-03-17) Capture a page screenshot in the security block evidence when a browser page is available (the guard's `inspect_page` path) — tonight's httpx-side challenge blocks have their bodies/headers in `python -m src.security evidence`, but no screenshot, which the operator expected the snapshot system to provide. |
| P-2026-10-04-2 | (moved from the backlog at the cap, 2026-10-04; was B-2026-10-03-18) The 95 `xfail(reason="B-24: ...")` tests in `tests/unit` (grep B-24): (a) `selectors/test_tab_scoped_resolution.py` — TDD-red for User Story 3, unbuilt; (b) `selectors/test_tab_context.py` — sync Mock pages vs the async TabContextManager, rewrite with AsyncMock; (c) `selectors/strategies/test_strategies.py` — stale strategy API / needs Playwright; (d) `selectors/test_engine.py` — and a real defect it exposes: `SelectorEngine` defines `register_selector` twice (`engine.py` ~490 `(name, selector)` with global-registry + hook, ~746 `(selector)`); the second shadows the first so the hook/global-registry path is dead and every caller uses the single-arg form — merge them (beware: the registered-hook firing from `hooks/registration.py` could recurse); (e) `test_validation.py`, `test_confidence.py`, `adaptive/.../test_confidence_scorer.py`, `test_custom_selector.py`, `test_view_service.py` — spec calibration (thresholds per context, risk levels, scores) that needs a product decision; (f) `plugins/test_plugin_base.py` — PluginMetadata validation/`description`, `PluginRegistry.get_statistics`; (g) `test_audit_trail_service.py` — mocks expect a different repository call. Each xfail is non-deleted evidence: decide spec vs test per cluster, then fix and drop the mark. |
| P-2026-10-04-3 | (moved from the backlog at the cap, 2026-10-04; was B-2026-10-03-19) Diagnostics coverage: route the remaining request paths through `src/observability/diagnostics.py` (`report_request` / `report_failure`) — browser lifecycle/navigation failures (use `SnapshotManager.capture_snapshot` with the live page), flashscore and other site scrapers, `selectors/adaptive` API client. Then give the control API a `/health` view over `health_summary()` + `python -m src.security evidence`. |
| P-2026-10-04-4 | (moved from the backlog at the cap, 2026-10-04; was B-2026-10-03-20) Delete the local safety branch `backup/pre-reset-main` once the operator is sure the four dropped `.context` rename commits are not needed (they were superseded by upstream's `.context_ledger` history). |

## Someday

Loose ideas with no owner and no hook yet. The lowest-pressure shelf.

| ID | Summary |
|----|---------|

<!-- TEMPLATE — add one row to the matching section:
| P-<YYYY-MM-DD>-<n> | <enough context that a future session can pick
      this up cold — status qualifiers in the text; promote to the
      backlog when it becomes actionable> |
-->
