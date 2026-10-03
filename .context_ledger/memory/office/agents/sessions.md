# Agent Sessions (append-only within the current office)

One entry per agent session in the **current office**, newest at the bottom.
Never edit or delete past entries — append corrections instead. This is not
append-only *forever*: when the office reaches `office_size` sessions (or a
milestone), `ledger-history close` freezes this whole office verbatim into
`.context_ledger/history/office-<NNN>/` (roster, registry, notes, logs —
nothing trimmed), writes the permanent accomplishments record
`.context_ledger/history/office-<NNN>.md`, and opens a fresh empty office
here. Closed offices in `history/` and `archive/` are never read at session
start. Before closing, note which open threads still matter — they are
re-seeded into the new office explicitly, and nothing else carries over.

<!-- TEMPLATE — copy below the last entry and FILL IN every placeholder:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from .context_ledger/core/roles/> | **Core:** <version from .context_ledger/core/VERSION>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md (actionable) or tasks/parking-lot.md (findings/questions), or "none">
- **Notes:** .context_ledger/memory/office/sessions/<date>-<N>/notes.md  (or "none")
- **Report:** .context_ledger/memory/office/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-10-03 — Session 1 (Noor/S001)
- **Agent:** Noor (S001) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** operator | **Core:** 2.0.3
- **Task:** finish the core 2.0.3 migration: close the previous office, fill its permanent record, re-seed the new office.
- **Commits:** ledger only (check-ins, close + re-seed, entry points, core 2.0.4 update, bookkeeping); no product code.
- **Outcome:** done (after two operator corrections — first pass skipped the protocol; see flaws log) — previous office frozen verbatim and recorded in `history/office-001.md`; backlog re-seeded with 20 actionable rows (cap 20), one carry-over ADR written, new roster and `STATE.md` generated. The close was operator-requested; the registry held 13 sessions, under the 20-session door threshold.
- **Open items:** the 20 backlog rows (top: linebet live re-verification, Neon sub-game volume check).
- **Follow-up (entry points):** `AGENTS.md` and `CLAUDE.md` regenerated from the 2.0.3 templates (the weak-agent floor); the project text they carried (architecture, BetB2B rules 11-17, setup, key files) moved verbatim to `memory/overrides/project-guide.md`, wired in via an override bullet so it survives core updates.
- **Notes:** none
- **Report:** .context_ledger/memory/office/reviews/2026-10-03-review.md

