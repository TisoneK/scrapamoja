# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
its roster row (if left behind) says who was here; check the session
entry and backlog before starting.

- **Session:** Kofi (S018), 2026-11-28
- **Task:** B-2026-10-03-5 — fallback outbox drain never fires across process boundaries. Add an explicit out-of-persist drain command (operator/boot step) that drains the on-disk SQLite outbox to primary when primary is writable, independent of the in-memory `_outbox_remaining` gate. Scope: new facet only (cross-process drain); the inline-replay-deadline + exit-1 facets stay on the backlog unless trivially co-fixed.
- **Status:** Working — implementing + testing against the real on-disk outbox (858 stranded rows in `data/betb2b/odds.db`). Quality bar: replay carries original `captured_at` (late history, not fabrication); do not fabricate/backfill.
