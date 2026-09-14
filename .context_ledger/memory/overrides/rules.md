# Protocol Overrides (update in place — project-owned)

Project-local adjustments to the protocol. Sessions read this file
right after loading their edition; where an override and the edition
conflict, **the override wins** — except the two rules nothing can
override: secret handling and append-only guarantees.

Overrides are standing, project-shaped deltas — not session
instructions (those die with the session) and not user preferences
(those live in `../user/preferences.md`). Core updates never touch
this file: customizations here survive every core version bump.

<!-- TEMPLATE — one bullet per override, with provenance:
- **<what the protocol says>** → **<what THIS project does instead>** —
  <why> (set by <user/agent>, YYYY-MM-DD)

Example:
- **Push to main after each commit** → **push to the `develop` branch;
  main is release-only** — repo uses git-flow (set by user, 2026-07-14)
-->

*(none yet)*

- **`kickoff.md` Step 1 — Windows core-check commands** → **No change needed since core 1.1.1** — the protocol ships `.cmd` launchers for every tool (`ledger-sync.cmd`, `ledger-gates.cmd`, `ledger-mem.cmd`, `ledger-collab.cmd`, `ledger-history.cmd`) that run the `.ps1` ports with `-ExecutionPolicy Bypass`; the 0.17-era override (PowerShell port + manual SHA fallback) is fully retired, including its pre-0.4.0 manual verification snippet. (set by agent, 2026-07-20; superseded by the 0.4.0 ps1 port 2026-08-01; retired by core 1.1.1 `.cmd` launchers, 2026-09-14)

- **`kickoff.md` Step 1 — `git pull --ff-only`** → **No change needed** — git works fine from PowerShell on Windows. (set by agent, 2026-07-20)
