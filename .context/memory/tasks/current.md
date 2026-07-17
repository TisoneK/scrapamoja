# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

Project is idle — no active task. Next session should consult
`tasks/backlog.md` and pick up an open item, or accept a new target
from the user.

**Most recent session (Session 9 continuation, 2026-07-17):** added
hardening + tooling around the Linebet scraper — snapshot normalizer
+ diff tool, HAR export + replay pipeline (the real solution to the
WAF block), moved debug scripts into the package, added 45 passing
tests. See the Session 9 continuation entry in `agents/sessions.md`
for the full picture, and the 3 new backlog items (top of the
Linebet-related work) for what's next on Linebet specifically.
