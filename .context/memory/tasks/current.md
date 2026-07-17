# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

- **Session:** 2026-07-17 — Session 7
- **Task:** Two-part: (a) migrate `.context/` from 0.1.x flat layout to 0.2.0 two-zone layout; (b) set up Scrapamoja for Railway deployment.
- **Status:** (a) done — committed as `chore(context): migrate to core 0.2.0 two-zone layout` (see Session 7 entry in `memory/agents/sessions.md`). (b) in progress — Railway config files (Dockerfile, railway.json, .dockerignore, Procfile) being authored next, will land as a separate project-mode commit.

Project is mid-session on part (b) — Railway deployment setup. Next agent should pick up part (b) if this session is interrupted.
