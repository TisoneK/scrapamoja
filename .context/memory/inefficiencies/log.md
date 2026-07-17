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

---
## 2026-07-12 — Claude Code / claude-fable-5 (Session 4)
- **Problem:** Template-framework test runs littered the repo root with `*_error_*.png/html` error captures, and any `template` CLI invocation drops `template_cli.log` into the cwd — both dirty `git status` mid-session and risk being committed accidentally.
- **Cost:** ~10 min of repeated artifact cleanup + a stray `src/sites/templates/` dir created as a side effect of the (buggy) scaffolder path.
- **Cause:** Product code wrote captures/logs to bare filenames in the process cwd.
- **Workaround / fix:** Captures fixed in-product (`681f3da` — now `data/snapshots/`, gitignored). CLI log file backlogged. Ran CLI smoke tests from the scratchpad dir to keep the repo clean.
- **Prevent next time:** Run anything that might write files from a scratch dir first; check `git status` after every test run in this repo.
