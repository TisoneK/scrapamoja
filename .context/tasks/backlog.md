# Backlog (append-only)

Open items for future sessions. Append at the bottom; never delete or
reorder. When an item is done, check it off and note the session/commit —
don't remove the line.

<!-- TEMPLATE — copy below the last entry:
---
- [ ] **<short title>** (added YYYY-MM-DD by <agent>) — <enough context that
      a fresh agent can act on this without any chat history. Severity if known.>
-->

---
- [ ] **Install Python 3.12+ toolchain on Baos-Mac-mini** (added 2026-07-12 by Claude Code) —
      This machine only has system Python 3.9.6; project requires >=3.12, so
      pytest/ruff/mypy could not be run. Install `python@3.12` (e.g. Homebrew),
      create `.venv`, `pip install -e ".[dev]"`, `playwright install`, then record
      the verified commands in `.context/system/environments.md`. Blocks any
      test-backed review. Infra/Low.
- [ ] **Migrate `datetime.utcnow()` (1081 uses) to tz-aware `datetime.now(timezone.utc)`** (added 2026-07-12 by Claude Code) —
      Deprecated in Python 3.12 (the project's floor). NOT a blind sed: `utcnow()`
      is naive, `now(timezone.utc)` is aware — changes `.isoformat()` output
      (`+00:00`) and can raise `TypeError` on naive/aware comparisons. Do it
      module-by-module with tests green. Medium. See F2 in 2026-07-12-review.md.
- [ ] **Audit 57 bare `except:` clauses for CancelledError swallowing** (added 2026-07-12 by Claude Code) —
      On 3.12 `CancelledError` is a `BaseException`; a bare `except:` catches it,
      contradicting the project's cancellation strategy. Narrow to `except Exception:`
      where intent is "swallow errors, not cancellation," esp. in async flows
      (e.g. `src/sites/github/flows/search_flow.py`). Needs tests. Medium.
      `grep -rn --include='*.py' -E 'except\s*:' src`. See F3 in review.
- [ ] **Audit fire-and-forget `asyncio.create_task(...)` calls** (added 2026-07-12 by Claude Code) —
      ~10+ tasks created without keeping a reference (e.g. `src/sites/base/site_scraper.py:84`,
      `src/sites/base/plugin_lifecycle.py:876,885`). Event loop holds only weak refs,
      so tasks can be GC'd mid-flight and exceptions lost. Store handles / await where
      completion matters. Low–Medium. See F4 in review.
