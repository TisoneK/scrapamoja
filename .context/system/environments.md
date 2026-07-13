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
## Baos-Mac-mini (last verified 2026-07-12, session 4)
- **Identify by:** hostname `Baos-Mac-mini.local`, `$USER` = `bao`, workspace `/Users/bao/Code/scrapamoja`
- **OS:** macOS 15.7.7 (build 24G720, Darwin 24.6.0), Intel **x86_64**
- **Runtimes:** system python3 = 3.9.6 (too old); **project runtime = uv-managed CPython 3.12.13 in `.venv/`**; node v24.17.0
- **Package manager:** **uv 0.11.28** at `~/.local/bin/uv` (installed 2026-07-12; not on default PATH — prefix commands with `export PATH="$HOME/.local/bin:$PATH"`). No Homebrew/pyenv/conda.
- **Verified commands (all run from repo root):**
  - `uv venv --python 3.12 .venv` — creates the venv (uv fetched CPython 3.12.13 standalone)
  - `uv pip install --python .venv/bin/python --only-binary :all: -e ".[dev]"` — **must pass `--only-binary :all:`**; without it uv tries to source-build `cryptography` and fails (no Rust/OpenSSL toolchain here)
  - `.venv/bin/python -c "import src.main"` — imports OK after the deps fix (`bb0e636`)
  - `.venv/bin/python -m playwright install` — chromium/firefox/webkit/ffmpeg downloaded to `~/Library/Caches/ms-playwright`; chromium headless launch smoke-tested OK
  - `git` push/pull work with existing creds
- **Not yet run this session:** `pytest` / `ruff` / `mypy` (installed and runnable — baseline just hasn't been executed).
  - `.venv/bin/python -m pytest tests/sites/template --no-cov -p no:cacheprovider --timeout=60 --timeout-method=signal -q` — verified (session 4); per-area runs finish in ~1.5s and dodge the suite-wide hangs. `pytest-timeout` is present in the venv (installed ad hoc session 3, still undeclared).
  - `.venv/bin/ruff check <path> --select F821` — verified (session 4); note the repo's `pyproject.toml` uses deprecated top-level `select`/`ignore` keys (ruff warns; still works).
- **Quirks / gotchas:**
  - `uv venv` does not install `pip` into the venv — use `uv pip ...` or `.venv/bin/python -m` for tools.
  - `--only-binary :all:` is required (see above). If a needed package has no wheel, that surfaces here as a hard error rather than a slow failing source build.
  - Network/filesystem-writing uv commands were run with the sandbox disabled (they need internet + writes to `~/.cache/uv`, `~/.local`).
