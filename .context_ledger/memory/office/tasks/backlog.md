# Backlog (work queue — actionable items only)

The queue of work a session can pick up and **do**. One row per item, in
its priority table. It is a queue, not a knowledge base: the test for a
row is "can an agent start on this and finish it?" If the answer is no —
it's a finding, an open question, an advisory "should we…?", a deferred
"someday" idea — it belongs in [`parking-lot.md`](parking-lot.md), not
here. Writing discoveries into the backlog is how a queue turns into a
57-row document nobody can work from.

**Done = delete the row. Stale = delete the row.** The backlog holds
open, actionable work only. When an item is finished, delete its row —
the completion record is the finishing session's `agents/sessions.md`
entry and the commit, never a tombstone here. When an item stops
mattering, delete it too; if it still carries information worth keeping,
move it to the parking lot first. Git history keeps every removed row,
so deleting loses nothing. (The one thing you must not do is delete a row
whose work is genuinely still open and recorded nowhere else — a row
vanishing from the diff with no session entry or promotion behind it is a
dropped handoff, not cleanup. Legacy checkbox-format backlogs:
`ledger-mem closeout` sweeps checked-off `- [x]` tombstones a session
left behind — dry run by default; `--confirm` deletes.)

**The queue is capped at ~20 rows** (`backlog_cap` in
`workflows/history.conf`; `ledger-mem check` warns past it). Twenty is a
working set, not a limit to fill. When you'd add a 21st actionable item,
prune one first: the lowest-value open row goes to the parking lot
(deferred, still valuable) or is deleted (no longer relevant) — never a
row you can't justify dropping. A queue you can hold in your head beats
a comprehensive one you can't.

**Only actionable work, and context lives where the work is.** Every row
gets a stable **ID** — `B-<added YYYY-MM-DD>-<n>`, n = that date's next
sequence in the file — and a **Summary** cell that says what to *do*, not
everything known about it. A fresh agent should be able to start from the
one line; the deep context belongs in the linked issue, PR, ADR, or
parking-lot finding the row points at, not packed into the cell. Keep
status qualifiers short ("partial", "blocked on X"). Don't append
research narrative to a row to "preserve" it — that's the parking lot's
job.

**Priority is the table an item sits in (High / Medium / Low), and it is
dynamic.** Only the top of the queue really matters — when you start a
session, the handful of High rows (roughly the top 3–5) are the work; the
rest is context, and a row that has sat in Low for many sessions is a
candidate for the parking lot, not a permanent resident. When unsure
between two tables, pick the lower one; promoting a row later is cheap,
and a backlog where everything is High says nothing.

This backlog belongs to the **current office**. When the office closes,
open items do not carry over implicitly — the closing session re-seeds
into the new office's backlog **only items with an active owner or a
clear next step**; everything else is recorded in the permanent record
(`history/office-<NNN>.md`, "Open threads") or parked. A re-seeded row
describes the work in plain words and never cites the old office's
session numbers or codenames.

Full spec: `.context_ledger/core/schemas/ledger-schema.md` →
"The backlog: a capped work queue" and "The parking lot".

## Open Items

### High Priority

| ID | Summary |
|----|---------|
| B-2026-10-03-1 | **linebet live re-verification with the fixes in place, in a rested window.** The cookie-header fix (`ec05ca0`), the burst-halt (`fb32cd1`/`6fa14bb`) and the pre-harvest grid wait are in but not yet proven end-to-end: tonight's address was rested by the guard after repeated challenges. Run the stored run (`scrape linebet scheduled --sport basketball --timeout 3600`), then a second run with no person present, then watch `python -m src.security status` and the per-skin rows from the Kenya brief's section 7 query. Also re-run **melbet** (its loop run was killed mid-scrape by mistake; earlier data intact). |
| B-2026-10-03-2 | Run the H2H backfill and sub-game capture against Neon and watch request volume: sub-games cost up to ~12 requests per new event (was 1). Confirm the Postgres `ALTER`s for `odds_snapshots.subject/period` and the new `coverage` table applied (they run on connect; verify the schema). Existing stored events keep no sub-game odds until re-fetched — decide whether to refresh upcoming ones. |

### Medium Priority

| ID | Summary |
|----|---------|
| B-2026-10-03-3 | The CLI's results and backfill batches (`_record_pending_results`, `_backfill_period_scores`, `_backfill_match_stats` in `src/sites/betb2b/cli/main.py`) are concurrent/sequential loops with only a 6-failure breaker — a challenge on the statisticfeed path there still records one guard block per response before the breaker trips. Add the `scraper._direct_block_seen` check the scraper batches now use (skip the rest of the batch on the first block). |
| B-2026-10-03-4 | statisticfeed (H2H) is stricter than the feed path — measured: with a fresh clearance both answer JSON, at ~4 minutes the H2H endpoint served the interstitial while the feed still answered. The H2H pass also runs minutes into a scrape. Options: run it earlier (right after discovery), refresh the session (force re-bootstrap) before it, and retry the batch once after a refresh instead of leaving `not_attempted`. |
| B-2026-10-03-5 | The betb2b CLI hangs ~12 minutes **after** the scrape closes and the run is persisted, then exits 1 (reproduced twice on Lameck-Windows, direct mode, remote store). Data is safe — find what runs after `BetB2BScraper closed` (telemetry flush, SQLAlchemy engine disposal, a non-daemon thread) and why it fails. |
| B-2026-10-03-6 | `StealthSettings` has no `webgl_protection` field but `browser/models/stealth.py` presets (~line 481) pass it — `src.browser.authority` and `src.browser.configuration` cannot be imported. Decide: add the field or fix the presets. |
| B-2026-10-03-7 | `src/selectors/integration.py` imports `src.selectors.engine.configuration.{loader,discovery}` but `engine` is a module, not a package — unimportable. Find where the configuration loader/discovery really live (or write them). |
| B-2026-10-03-8 | Plugin permission system, remaining defects (module now imports and request/approve/export work): statistics were never implemented (`export_permissions` reads `self._stats`; the module-level `get_permission_statistics()` calls a missing `get_statistics()`); `import_plugin_permissions` compares against an undefined `permission_id`; `export_permissions` writes permissions as a dict keyed by id while `import_permissions` expects a list; `tests/integration/test_plugin_integration.py` imports a `PluginManager` that exists nowhere. |
| B-2026-10-03-9 | Adaptive dashboard API integration tests (`tests/integration/test_feature_flag_api.py`, `test_audit_api.py`, `test_audit_query_api.py`, `test_audit_export_formats.py`) were uncollectable; now they run and fail (mostly 404): they call routes such as `/test-feature-flags` that the app does not mount. Update them to the real routes/prefixes or re-add a test app. |
| B-2026-10-03-10 | 78 remaining undefined-name sites (`ruff check src --select F821`): latent NameErrors inside function bodies — `MessageType` (10, interrupt_handling), `request` (navigation/plugin code), `Adaptation`/`nx` (navigation/route_adaptation.py), `BrowserSession`, `params`, `get_component_info`... Each needs its function read; not mechanical. |
| B-2026-10-03-11 | `tests/unit` is green (817 passed, 95 xfailed, run with `--timeout=8`; some tests hang without it). The 95 xfails (reason prefix B-24) are tests written test-first against APIs that were never built or have since changed — see B-2026-10-03-18. Remaining work here: the test-isolation flaw in `test_feature_flag_service*.py` (reads local gitignored `data/adaptive.db` instead of an in-memory DB) — fix by isolating the DB path. |
| B-2026-10-03-12 | Rotate the bore.pub proxy password — it was shared in an agent chat. Lives in `memory/secrets/betb2b-proxy` and the (gitignored, commented-out) `src/sites/betb2b/.env`. Operator rule: the proxy is for the website/browser bypass only, never for API calls. |
| B-2026-10-03-13 | Storage-quota monitor limit for Neon — partial: `BETB2B_DB_LIMIT_MB=1000` is now set in the local `.env` and shipped in `.env.example`; any DEPLOYED worker/service env (Railway or other) still defaults to 500 MB (the Supabase limit) and needs it set. Neon free = 1 GB storage / 100 compute-hours. |
| B-2026-10-03-14 | `ledger-mem lint --tree` can never pass in this repo: it flags the `.context_ledger/` routing paths inside `AGENTS.md`/`CLAUDE.md` (the ledger's own entry-point files). 262 ADR citations were stripped from product files this session (0 left); the 40 entry-point path hits remain. See the flaws log for the suggested upstream fix. |
| B-2026-10-03-15 | Live-verify the security package on a real challenge: (a) operator runs `python -m src.browser.profiles warmup betb2b-<skin> <url>` from an allowed-country egress and confirms later headless runs reuse the validation; (b) exercise HUMAN_HANDOFF and the headed tier end to end (only fakes so far). Cannot be done from the US dev IP while the country block applies. |
| B-2026-10-03-16 | linebet: decide whether it is worth supporting. Its website is country-blocked (US) and Gcore WAAP browser validation challenges non-browser clients (ADR-28); the scraper's headless Chromium fails it. Keep linebet last in `BETB2B_FALLBACK_SKINS`; any browser-session approach (operator-validated headed browser, requests kept inside it) needs the operator's go-ahead. |

### Low Priority

| ID | Summary |
|----|---------|
| B-2026-10-03-17 | Capture a page screenshot in the security block evidence when a browser page is available (the guard's `inspect_page` path) — tonight's httpx-side challenge blocks have their bodies/headers in `python -m src.security evidence`, but no screenshot, which the operator expected the snapshot system to provide. |
| B-2026-10-03-18 | The 95 `xfail(reason="B-24: ...")` tests in `tests/unit` (grep B-24): (a) `selectors/test_tab_scoped_resolution.py` — TDD-red for User Story 3, unbuilt; (b) `selectors/test_tab_context.py` — sync Mock pages vs the async TabContextManager, rewrite with AsyncMock; (c) `selectors/strategies/test_strategies.py` — stale strategy API / needs Playwright; (d) `selectors/test_engine.py` — and a real defect it exposes: `SelectorEngine` defines `register_selector` twice (`engine.py` ~490 `(name, selector)` with global-registry + hook, ~746 `(selector)`); the second shadows the first so the hook/global-registry path is dead and every caller uses the single-arg form — merge them (beware: the registered-hook firing from `hooks/registration.py` could recurse); (e) `test_validation.py`, `test_confidence.py`, `adaptive/.../test_confidence_scorer.py`, `test_custom_selector.py`, `test_view_service.py` — spec calibration (thresholds per context, risk levels, scores) that needs a product decision; (f) `plugins/test_plugin_base.py` — PluginMetadata validation/`description`, `PluginRegistry.get_statistics`; (g) `test_audit_trail_service.py` — mocks expect a different repository call. Each xfail is non-deleted evidence: decide spec vs test per cluster, then fix and drop the mark. |
| B-2026-10-03-19 | Diagnostics coverage: route the remaining request paths through `src/observability/diagnostics.py` (`report_request` / `report_failure`) — browser lifecycle/navigation failures (use `SnapshotManager.capture_snapshot` with the live page), flashscore and other site scrapers, `selectors/adaptive` API client. Then give the control API a `/health` view over `health_summary()` + `python -m src.security evidence`. |
| B-2026-10-03-20 | Delete the local safety branch `backup/pre-reset-main` once the operator is sure the four dropped `.context` rename commits are not needed (they were superseded by upstream's `.context_ledger` history). |

<!-- TEMPLATE — add one ACTIONABLE row to the matching priority table
     (a finding, question, or someday idea goes in parking-lot.md instead):
| B-<YYYY-MM-DD>-<n> | <what to DO, one line, pointing at the issue/PR/
      parking-lot finding for detail — not the full context> |
-->
