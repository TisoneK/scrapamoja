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

---
## 2026-10-04 — Imani (S005) / claude-sonnet-5-5 (Session 5)

- **Flaw:** (1) The protocol had no rule against loading a geo-blocked site's pages from a restricted machine; an unattributed browser-path run on the operator's Mac recorded country blocks and rested the skin's feed runs. (2) The office was closed and reset *while this session was working*: its roster row vanished, a different agent took the same name (Mei, S004), and a later session note was appended to the end of `sessions.md` — which was now that agent's entry.
- **Symptom:** (1) `geo_block` for betwinner and linebet at 05:29-05:39 on a US machine; direct runs refused with "in cooldown". (2) a "Follow-up 8" bullet sitting inside S004's entry.
- **Root cause:** (1) policy lived in people's heads, and the guard's cooldown is per site, not per access path. (2) appending to the file tail without re-reading roster/sessions after a long gap; `ledger-history close` happened under a live session with no signal to it.
- **Suggested fix:** (1) done — ADR-2, `egress.py`, rule 18, override. (2) before every append to an append-only log re-read its tail and the roster; `ledger-history close` should refuse (or warn loudly) while a non-clocked-out row exists on the roster.
- **Status:** (1) fixed; (2) corrected in-session by checking in as Imani (S005) and a correction line in this session's entry; protocol-level fix open (core).

---
## 2026-11-01 — Tariq (S014) / claude-opus-4-8 (Session 14)

- **Flaw:** Phase 1 (Sync) was skipped entirely — I went Phase 0 → straight to Phase 2 check-in, with no `git pull --ff-only` and no `ledger-sync verify`/`status`. The supervisor had to catch it ("Why didn't you run sync protocol?"). Had I run it on time, I'd have seen core 2.3.3 was available before, not after, committing two check-in commits on the stale 2.2.0 core.
- **Symptom:** check-in + STATE regen committed and pushed while still on core 2.2.0; the update to 2.3.3 only surfaced when sync was finally run after the first supervisor nudge. No data harm (the pull was a no-op fast-forward), but the ordering guarantee was broken and the supervisor, not the ledger, was the thing that noticed.
- **Root cause:** a genuine tension in the guidance, resolved the wrong way under emphasis. `CLAUDE.md`'s opening ("**Before reading anything else here — including the rest of this file — check in**"), the roster header ("Sign **before the deep read**"), and the per-turn `ledger-guard` floor's first bullet ("Check in on the roster BEFORE the deep read") are loud, absolute, and repeated every turn. kickoff.md's own phase order puts **Sync (Phase 1) before Check-in (Phase 2)**, but that ordering is stated once, quietly, and is outweighed by the drumbeat of "check in first." "Check in before the deep read" is meant to stop you doing the *deep read* before signing — but it reads as "do nothing before check-in," which silently swallows the short, mandatory Phase 1 sync that must precede the sign-in. kickoff.md Phase 2 even says "needs only two files" and "before analysis, before product work" — it never says "and you must already have synced."
- **Suggested fix:** carve Phase 1 Sync out of the "check in first" rule explicitly, in the loud places, so the two stop competing:
  1. `CLAUDE.md` opening + roster header + the `ledger-guard` floor's first bullet: change "check in before the deep read" to name the one thing that precedes check-in — e.g. "Run Phase 1 Sync (`git pull --ff-only`, `ledger-sync verify`/`status`) first; **then** check in, before the deep read." Distinguish "sync" from "the deep read" — they are not the same thing and only the deep read comes after check-in.
  2. kickoff.md Phase 2 opening: add a one-line guard — "If you reached here without running Phase 1, stop and run it now; eagerness to sign is exactly how Phase 1 gets skipped."
  3. Optional mechanical backstop (fits 2.3.3's loop-closing theme): the check-in commit's `prepare-commit-msg`/`pre-commit` path could note when `core.lock`'s last `ledger-sync status` is older than this session / absent, i.e. a check-in landing with no sync recorded this session — a warning, like `push-check`'s Working-row warning, so the ledger catches the skip, not the supervisor (Rule 15).
- **Status:** open — remediated in-session (Phase 1 run late: pull was a no-op fast-forward, core updated 2.2.0 → 2.3.3, `verify` green); protocol-level fix open (core package).

---
## 2026-11-26 — Baraka (S015) / claude-opus-4-8 (Session 15)

- **Flaw:** `ledger-mem prune` over-flags a dated block holding mixed open+fixed sub-entries as fully closed. Since the exit gate auto-runs `prune --apply` (2.4.0), a routine close-out would silently archive OPEN flaws out of the startup read.
- **Symptom:** `prune --list` flagged `2026-10-03 Noor (S1)` and `2026-10-04 Imani (S5)` archive-eligible, but each holds a live open sub-flaw (Noor: migration-from-memory / `ledger-sync status` sibling-clone staleness, `Status: open`; Imani: item (2) close-under-live-row, "protocol-level fix open").
- **Root cause:** `prune_apply_one` (ledger-mem ~L332) sets `closed=1` on ANY `**Status:**` line matching `fixed|resolved|…`; the open-guard only excludes `still open|partly|partial|unverified`, so bare `open` / `fix open` on an earlier sub-entry is missed and one `fixed` line closes the whole multi-flaw block.
- **Suggested fix:** (a) add bare `\bopen\b` to the open-guard; (b) require ALL Status lines in a block closed, not ANY; (c) make the exit gate's `prune --apply` warn-only (no auto-move) unless every Status line is resolved.
- **Status:** open — worked around: declined to archive, left `flaws/log.md` intact, ran manual Exit checklist instead of `ledger-gates run exit` to avoid the auto-archive.

