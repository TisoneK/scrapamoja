# Inefficiency Log (append-only, mandatory)

Every session appends one block — honestly. Friction you absorb silently
is friction the next agent hits blind. "None this session" is valid only
if literally nothing slowed you down.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model>
- **Problem:** <what went wrong or was slower than it should be>
- **Cost:** <rough time/effort wasted>
- **Cause:** <root cause if known>
- **Workaround / fix:** <what worked, or "unresolved">
- **Prevent next time:** <protocol/context change that would have avoided it>
-->

---
## 2026-07-12 — Claude Code / claude-opus-4-8
- **Problem:** Could not run the Phase-1 baseline (pytest/ruff/mypy) — the machine has only system Python 3.9.6 but the project requires >=3.12. No venv, no `uv`, no newer interpreter.
- **Cost:** ~Whole session's dynamic verification lost; review reduced to static-only.
- **Cause:** Toolchain gap on Baos-Mac-mini (see `system/environments.md`); protocol forbids installing to system Python / installing global packages without asking.
- **Workaround / fix:** Verified the one code change with `python3 -m py_compile` only. Left a backlog item + report note with exact setup commands.
- **Prevent next time:** Install `python@3.12` + `.venv` on this machine before the next review; record verified commands in `system/environments.md` so the next agent skips this discovery.
