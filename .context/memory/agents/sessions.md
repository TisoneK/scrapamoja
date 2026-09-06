# Agent Sessions (append-only within the current group)

One entry per agent session in the CURRENT group, newest at the bottom.
Closed groups live in .context/history/ and .context/archive/ (not read
at session start). Rotate with context-history.

<!-- TEMPLATE - copy below the last entry and FILL IN every placeholder:
---
## YYYY-MM-DD - Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay> | **Core:** <version>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked>
- **Open items:** <pointers into tasks/backlog.md, or "none">
- **Notes:** .context/memory/sessions/<date>-<N>/notes.md  (or "none")
-->
