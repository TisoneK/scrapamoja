# Inefficiency Log (append-only, mandatory)

Every session appends one block — honestly. Friction you absorb silently
is friction the next agent hits blind. "None this session" is valid only
if literally nothing slowed you down.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model>
- **Problem:** <what went wrong or was slower than it should be>
- **Cost:** <rough time/effort wasted>
- **Cause:** <root cause if known>
- **Workaround / fix:** <what worked, or "unresolved">
- **Prevent next time:** <protocol/context change that would have avoided it>
-->

---
## 2026-07-12 — Claude Code / claude-opus-4-8
- **Problem:** Could not run the Phase-1 baseline (pytest/ruff/mypy) — the machine has only system Python 3.9.6 but the project requires >=3.12. No venv, no `uv`, no newer interpreter.
- **Cost:** ~Whole session's dynamic verification lost; review reduced to static-only.
- **Cause:** Toolchain gap on Baos-Mac-mini (see `system/environments.md`); protocol forbids installing to system Python / installing global packages without asking.
- **Workaround / fix:** Verified the one code change with `python3 -m py_compile` only. Left a backlog item + report note with exact setup commands.
- **Prevent next time:** Install `python@3.12` + `.venv` on this machine before the next review; record verified commands in `system/environments.md` so the next agent skips this discovery.

---
## 2026-07-12 — Claude Code / claude-fable-5 (Session 4)
- **Problem:** Template-framework test runs littered the repo root with `*_error_*.png/html` error captures, and any `template` CLI invocation drops `template_cli.log` into the cwd — both dirty `git status` mid-session and risk being committed accidentally.
- **Cost:** ~10 min of repeated artifact cleanup + a stray `src/sites/templates/` dir created as a side effect of the (buggy) scaffolder path.
- **Cause:** Product code wrote captures/logs to bare filenames in the process cwd.
- **Workaround / fix:** Captures fixed in-product (`681f3da` — now `data/snapshots/`, gitignored). CLI log file backlogged. Ran CLI smoke tests from the scratchpad dir to keep the repo clean.
- **Prevent next time:** Run anything that might write files from a scratch dir first; check `git status` after every test run in this repo.

---
## 2026-07-17 — Super Z / GLM (Z.ai cloud sandbox)
- **Problem:** First Railway deploy of the FastAPI control plane failed. Every gunicorn worker crashed on startup with `PermissionError`, so the server never bound and the `/health` healthcheck timed out. Railway's deploy log identified the root cause: `src/core/snapshot/__init__.py` calls `os.makedirs("config")` + `os.makedirs("data/snapshots")` at IMPORT time, but the container runs as non-root `appuser` and the `/app` directory was root-owned (only `/app/data` had been chowned).
- **Cost:** One failed deploy + one extra iteration cycle (~15 min of build + debug time on Railway's side, since this sandbox has no Docker to pre-verify locally).
- **Cause:** Two compounding issues:
  1. **Product code smell (root cause):** `src/core/snapshot/__init__.py:_initialize_module()` runs at module-import time and calls `os.makedirs()` with RELATIVE paths (`"config"`, `"data/snapshots"`) — resolved against whatever the cwd is at import time. Import-time side effects that touch the filesystem are fragile: they crash any environment where the cwd isn't writable by the importing user (containers, read-only installs, CI sandboxes).
  2. **Dockerfile gap (trigger):** `WORKDIR /app` creates `/app` owned by root. The original `RUN mkdir -p /app/data && chown -R appuser:appuser /app/data` only chowned the `data/` subtree — not `/app` itself. So `appuser` could write to `/app/data/...` but NOT create a new top-level dir like `/app/config/`.
- **Workaround / fix:** Dockerfile-only fix (commit pending): pre-create `config/`, `data/snapshots/`, `output/`, `logs/`, `.checkpoints/` AND `chown -R appuser:appuser /app` (the directory itself, not just its contents). Pre-creation makes the import-time `os.makedirs(..., exist_ok=True)` a no-op; the `/app` chown covers any future runtime-created dirs. Source-level fix is backlogged (see `tasks/backlog.md`).
- **Prevent next time:** (a) When deploying Python apps as non-root in containers, ALWAYS chown the WORKDIR itself, not just the subdirs you pre-create — `WORKDIR` creates the dir as root and `COPY --chown=...` only chowns the files it brings in, not the parent. (b) When smoke-testing a Dockerfile locally without Docker (venv-only), grep the codebase for `os.makedirs` / `Path(...).mkdir` at MODULE LEVEL (not inside functions) — those are import-time side effects that will crash the same way under any restricted cwd. Found one such call here: `src/core/snapshot/__init__.py:260 _initialize_module()`.
