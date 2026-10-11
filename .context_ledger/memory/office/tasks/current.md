# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
its roster row (if left behind) says who was here; check the session
entry and backlog before starting.

- **Session:** 2026-10-11 — Dayo (S007) / claude-opus-4-8
- **Task:** Add a `flashscore live-poll` CLI command — poll live match score on an interval (reusing the FlashscoreScraper), score + stage only, no betting logic. Mirrors the betb2b poller pattern.
- **Status:** scrapamoja side DONE/pushed (`148fde6` live-poll, `1a202af` stage/clock, `cbd5359` live-serve /score). Now extended into ~/Code/task2sms: implemented Task<-DataSource context wiring (code + migration + tests, py_compile clean, UNCOMMITTED). BLOCKED: task2sms backend needs Docker (operator's choice; Docker Desktop not running) to validate; real SMS needs operator's provider keys + phone number + Over line.
