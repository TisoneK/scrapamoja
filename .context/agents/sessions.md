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
