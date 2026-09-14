# Active Workflow (overwrite when the workflow changes)

The workflow currently in force for this repo — which protocol edition
agents follow and the standing session parameters. Update only when the
user changes the rules; note the change in your session entry.

- **Protocol:** by agent type — local agents → `.context_ledger/core/rules/ai-engineering-protocol-local.md`; cloud/sandbox agents → `.context_ledger/core/rules/ai-engineering-protocol.md`
- **Protocol location:** on disk — vendored in `.context_ledger/core/` (no network fetch needed; version in `.context_ledger/core/VERSION`, last verified in `../core.lock`)
- **Package upstream (for flaw back-ports + core updates):** https://github.com/TisoneK/context-ledger.git (renamed from `TisoneK/.context`, 2026-09; now public; a `ledger-sync status` "no reachable source" line means no *local* clone — check this remote before claiming up-to-date; sibling clone on Lameck-Windows at `C:\Users\Lameck\Tisone\.context`)
- **Since:** 2026-09-14 (core 1.1.1 — Context Ledger rename + office architecture, migrated from 0.17.0 by Session 48; prior history under the `.context/` flat layout; 0.2.0 two-zone since 2026-07-17)
- **Default role:** engineer — unless a session says otherwise; see `.context_ledger/core/roles/`
- **Scope:** discovery + review + fix all safe issues
- **Target:** general sweep
- **Focus areas:** all — security, performance, UX, architecture, testing, docs
- **Findings handling:** fix safe, flag architectural
- **Push policy:** push to main directly after each commit
- **Commit style:** Conventional Commits with scope; `chore(ledger):` for `.context_ledger/` (was `chore(context):` pre-1.1.1)
- **Commit granularity:** one logical change per commit
- **Deliverable:** report in `.context_ledger/memory/office/reviews/` + chat summary
- **Gates:** `.context_ledger/memory/workflows/gates.conf` — checkpoint before each next action; `pre-commit`, `integration`, and `exit` gates are mandatory (core 0.8.0 initialized the gates 2026-08-18; core 1.1.1 in force since 2026-09-14 — door check-in with roster Status cells; Windows agents use the `.cmd` launchers)
