# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
its roster row (if left behind) says who was here; check the session
entry and backlog before starting.

- **Session:** Zuri (S011)
- **Task:** DB handoff (local-Postgres cutover) + on-demand full scrape to populate today/tomorrow. DONE.
- **Status:** done — scrape run 991 persisted 200 events / 232,988 odds to local PG; today (2026-10-24)=71 games, tomorrow (2026-10-25)=19. Awaiting operator's next task.
