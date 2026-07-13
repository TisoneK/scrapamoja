# Agent Sessions (append-only)

One entry per agent session, newest at the bottom. Never edit or delete
past entries — append corrections instead.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from the protocol package's roles/>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md, or "none">
- **Report:** .context/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-07-12 — Session 1
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Bootstrap `.context/` (first session) + general-sweep review & safe fixes.
- **Commits:** 4 (`3de04c3`..`HEAD`) — bootstrap, `fix(cli)` scorewise entry point, review report, context log.
- **Outcome:** partial — `.context/` bootstrapped; 1 High bug fixed (`c8a4179`); baseline (pytest/ruff/mypy) NOT run — machine lacks Python 3.12+, so review was static-only.
- **Open items:** 4 in tasks/backlog.md (install Py3.12+ toolchain; datetime.utcnow migration; bare-except audit; fire-and-forget task audit).
- **Report:** .context/reviews/2026-07-12-review.md

---
## 2026-07-12 — Session 2 (continuation)
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Install dependencies (user request) — unblock the Python 3.12 toolchain.
- **Commits:** 1 (`bb0e636`) `fix(deps)` + `.context` updates.
- **Outcome:** done — installed uv → CPython 3.12.13 → `.venv` → deps (with `--only-binary :all:`). Found `pyproject.toml` was missing 10 runtime deps (fastapi/numpy/scipy/aiohttp/requests/networkx/watchdog/jinja2/semantic-version/python-json-logger) that `src/` imports; declared them. Discovered 3 pre-existing import-time code bugs (see backlog).
- **Open items:** `playwright install` + run pytest/ruff/mypy baseline; 3 new import-crash bugs in tasks/backlog.md.
- **Report:** .context/reviews/2026-07-12-review.md (F1–F4); dep + toolchain work captured in this entry + system/environments.md.

---
## 2026-07-12 — Session 3 (continuation)
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Run the full test suite (incl. real/integration tests).
- **Commits:** 0 code (findings only) + `.context` updates.
- **Outcome:** partial/blocked — suite could not complete. `pytest` collected 1864 tests, 15 files error at collection; run reached only ~67/1864 before manual stop because ~24% of tests hang to the 60s per-test timeout (deadlock-like fixture teardown / live I/O). First 67: ~54 passed, ~13 failed. Installed `pytest-timeout` into the venv (ad hoc, not declared). Note: `--timeout-method=thread` aborts the whole run on first hang — use `signal`.
- **Open items:** 4 new backlog items (suite-can't-complete/hangs; `pytest.ini` `[tool:pytest]` header ignored; 15 collection errors; earlier 3 import-crash bugs).
- **Report:** delivered in chat; findings in tasks/backlog.md. No coverage/artifacts left (ran `--no-cov -p no:cacheprovider`).

---
## 2026-07-12 — Session 4
- **Agent:** Claude Code | **Model:** claude-fable-5 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Review the site-scraper template framework (`src/sites/base/template/`) against its one-framework philosophy; fix safe issues incl. the `test_template_framework` collection error.
- **Commits:** 8 (`1b558e3`..`HEAD`) — 5 `fix(template)`, 1 `docs(review)`, 2 `chore(context)`.
- **Outcome:** done — the "create → validate → generate" path was broken at 4 independent points; all fixed (`template create` smoke-tested working). Target-area tests: 14 passed/27 failed/22 errors + e2e uncollectable → 39 passed/33 failed/2 errors, e2e collects 11. Remaining failures = tests drifted from the canonical interface (backlogged, needs owner call).
- **Open items:** 6 new in tasks/backlog.md (test-API alignment; 6 missing .j2 templates; hierarchy ADR; Dependabot triage; CLI log file; progress note on collection errors — 14 files remain).
- **Report:** .context/reviews/2026-07-12-review-2.md
