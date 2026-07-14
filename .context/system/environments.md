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

---
## Z.ai cloud sandbox (last verified 2026-07-14, session 5)
- **Identify by:** ephemeral container hostname (e.g. `c-6a55bf2b-…`), workspace `/home/z/my-project`, OS user `z`. Hostname changes per session — identify by the workspace path + Debian trixie + ephemeral hostname pattern, not a stable hostname.
- **OS:** Debian GNU/Linux 13 (trixie), x86_64, kernel 5.10.134
- **Runtimes:** system `python3` = 3.12.13; `git` 2.47.3; no `uv`/`node` verified this session (not needed for a sync)
- **Package manager:** system `apt` (not used this session); `pip` available via system python3
- **Verified commands (all run from repo root `/home/z/my-project/scrapamoja`):**
  - `git clone https://github.com/TisoneK/scrapamoja.git` — public project repo, no auth needed for clone
  - `git clone "https://x-access-token:${GIT_TOKEN}@github.com/TisoneK/.context.git" ../.context` — private package repo; PAT required (fine-grained, scoped to both TisoneK repos). Strip token from `.git/config` immediately after: `git -C ../.context remote set-url origin https://github.com/TisoneK/.context.git`
  - `git config user.name "Tisone Kironget" && git config user.email "tisonkironget@gmail.com"` — fresh sandbox has no git identity; set per `user/identity.md`
  - `git push origin main` — requires PAT even though the project repo is public (cloud/sandbox agent has no other creds). Dance: temporarily set remote URL with `x-access-token:${GIT_TOKEN}@`, push, then strip the token back to the plain URL.
  - `curl -s -H "Authorization: Bearer ${GIT_TOKEN}" https://api.github.com/user` — PAT validity check (returns login `TisoneK` for a working token)
- **Not yet run this session:** `uv`/venv setup, `pytest`/`ruff`/`mypy`, `playwright install` — sync session didn't need them. A future review/fix session on this sandbox should follow the Baos-Mac-mini block's `uv` recipe (with `--only-binary :all:`) to stand up the toolchain.
- **Quirks / gotchas:**
  - **No persistent state.** Every session starts from an empty workspace — both repos must be cloned fresh each time. The `.context/` memory lives in git, so nothing is lost, but anything not committed/pushed is gone when the session ends.
  - **PAT is the only credential.** No SSH keys, no `gh` CLI, no credential manager. A fine-grained PAT scoped to `TisoneK/scrapamoja` (Contents: RW) and `TisoneK/.context` (Contents: R) is required for any session that clones the package or pushes to the project. Never write the PAT to any file; pass it as an env var, strip it from `.git/config` after each push, and rotate after the session.
  - **The package repo `TisoneK/.context` is private.** The original external kickoff file contradicted itself on this (line 27 said private, line 81 said public) — ground truth is private. The in-repo `.context/kickoff.md` (generated session 5) records this correctly.
