# Environments (update in place)

Machines and sandboxes agents have run on, and what it takes to work on
this project from each. One block per environment; update the matching
block (and its "last verified" date) every time you run on it again.

## Rules

1. **Match before you add.** At session start, check whether the machine
   you're on already has a block (use its "Identify by" line). Update the
   match; add a new block only for a genuinely new environment.
2. **Record what you verified, not what you assume.** A command belongs
   under "Verified commands" only after it ran successfully on this
   environment, this project.
3. **Agents never delete blocks.** An environment the project no longer
   uses may be pruned by the user; if you can't verify a block, leave it
   alone — its last-verified date already says how stale it is.
4. **Machine facts only.** Secret values go in `secrets/`; user
   preferences in `user/`; project-wide decisions in `plans/`.

---
## Baos-Mac-mini (last verified 2026-07-12)
- **Identify by:** hostname `Baos-Mac-mini.local`, `$USER` = `bao`, workspace `/Users/bao/Code/scrapamoja`
- **OS:** macOS 15.7.7 (build 24G720, Darwin 24.6.0)
- **Runtimes:** python3 = **3.9.6 (system)** — ⚠️ project requires >=3.12; python3.11/3.12/3.13 NOT installed; no Homebrew python; node v24.17.0
- **Package manager:** pip (requirements.txt); no `uv`, no `poetry`, no venv present
- **Verified commands:** `git` (identity + push work with existing creds); package repo cloned at `../.context`
- **Quirks / blockers:**
  - **No Python 3.12+ interpreter available** — cannot create a compatible venv, install deps (`pip install -e ".[dev]"`), or run `pytest` / `ruff` / `mypy` against the project's required runtime. Baseline test/lint/typecheck could NOT be run this session. Static (read-only) code review only until a 3.12+ interpreter is installed.
  - No project virtualenv (`.venv/` / `venv/`) present.
  - Installing to system Python 3.9 is disallowed by protocol and would fail the `>=3.12` requirement anyway.
