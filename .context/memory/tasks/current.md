# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

- **Session:** 2026-07-17 — Session 8
- **Task:** (a) Fix the Railway deploy crash (every gunicorn worker died with `PermissionError` because `src/core/snapshot/__init__.py` calls `os.makedirs("config")` at import time and `/app` was root-owned). (b) Record in `.context/memory` that Scrapamoja is linked to Railway via GitHub + the Railway plan limits (8 vCPU / 8 GB).
- **Status:** done — both parts complete. Two commits ready to push: `fix(deploy): pre-create runtime dirs + chown /app` (project) and `chore(context): record Railway linkage, plan, and the deploy crash` (memory). See Session 8 entry in `memory/agents/sessions.md`.
- **Open items:** push to `origin/main` (triggers Railway auto-redeploy). User still needs to add a Railway Volume at `/app/data` for SQLite persistence — flagged in `memory/system/environments.md`.

Project is idle — no active task. Next session should consult `tasks/backlog.md` and pick up an open item, or accept a new target from the user.
