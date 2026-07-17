# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

Project is idle — no active task. Next session should consult
`tasks/backlog.md` and pick up an open item, or accept a new target
from the user.
