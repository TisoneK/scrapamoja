# Flaws Log (append-only — flows to the protocol package)

Friction caused by the `.context_ledger/` system or the protocol itself. See
`README.md` in this directory for the split between `flaws/` and
`inefficiencies/`.

Append-only, but compactable — the log never grows without bound:

- **Resolved entries move verbatim** to cold storage: once an entry is
  explicitly marked `RESOLVED` / `superseded` / fixed, cut it unchanged
  into `archive.md` in this directory so startup reads only the live
  entries. Age alone never makes an entry eligible — an unresolved flaw
  stays here as a live trap.
- **Repeats roll up:** when 3+ entries describe the same recurring
  protocol trap, append ONE consolidated `Recurring` entry — the pattern,
  how many times, the current workaround — and move the individual
  entries verbatim into `archive.md`. The live log keeps the pattern, not
  the repeats.

`ledger-mem prune` reports log sizes, archive-eligible entries (`--list`
names them), and roll-up candidates.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model> (Session N)

- **Flaw:** <what in the protocol or .context_ledger/ system didn't work>
- **Symptom:** <what happened to the agent — the observable friction>
- **Root cause:** <why the protocol/.context_ledger/ let this happen>
- **Suggested fix:** <concrete change to the package — a step, a pitfall,
  a template, a rule>
- **Status:** open | fixed in package <commit-sha or date>
-->

---
## 2026-10-03 — Noor / claude-sonnet-5-5 (Session 1)

- **Flaw:** a core migration done from memory of the protocol instead of the protocol: stale kickoff read, no edition read, check-in after reading, no claim/release, no gates, no upstream check, no flaw/preference/ai-models bookkeeping, and the migration reported "complete" three times while pieces were missing. The operator had to say so twice.
- **Symptom:** `ledger-sync status` named a local sibling clone as the update source ("source: 2.0.3"), and that read as "current"; public upstream was already 2.0.4 (a Windows-port fix the operator's Windows box needed). `migrate` also leaves the root `AGENTS.md`/`CLAUDE.md` on the old shape without saying so.
- **Root cause:** `status` reports the best *reachable* source without saying it may be stale, and `migrate` prints only a fill-facts list, not a checklist of what a finished migration includes (office close, entry-point regeneration, upstream check).
- **Suggested fix:** `ledger-sync status` should print "local sibling clone — not checked against the package remote" when the source is a sibling directory; `migrate` should end with an explicit done-list (core version vs upstream, entry points regenerated or left, office size vs `office_size`).
- **Status:** open


- **Symptom:** S003 pushed a commit while `ledger-gates run pre-commit` had FAILED (6 tests), because the gate output was piped through `tail` inside an `&&` chain, which masked the exit code.
- **Root cause:** gate result checked via pipeline, not `$?`/`pipefail`.
- **Suggested fix:** run the gate on its own line and test its exit status before committing; fixed forward within the session (next commit restored green).
- **Status:** fixed
