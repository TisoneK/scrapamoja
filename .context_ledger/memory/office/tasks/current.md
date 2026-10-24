# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
its roster row (if left behind) says who was here; check the session
entry and backlog before starting.

- **Session:** Zuri (S011)
- **Task:** on-demand full discovery scrape (betwinner basketball, `--direct`) to pull today's/tomorrow's upcoming games into local Postgres now, rather than waiting for the next scheduled 6 h run. Follows the local-Postgres cutover this session shipped.
- **Status:** working — running the scrape, then verifying event counts for 2026-10-24 / 2026-10-25
