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

---
## 2026-07-18 — GitHub Copilot / DeepSeek V4 Flash Free (Session 3)
- **Problem:** `_build_page_script()` in `dom.py` used naive `f'"{s}"'` quoting for CSS selectors, producing broken JS when a selector contained double quotes (e.g. `[class*="bet"]` → `"[class*="bet"]"`). This caused a JS `SyntaxError: Unexpected identifier` at runtime, blocking ALL DOM extraction.
- **Cost:** ~30 min of debugging (first blamed proxy, then browser config, then finally read the generated JS).
- **Cause:** Undocumented assumption that CSS selectors never contain double-quote characters. The BetB2B default selectors in the sports registry use `[class*="bet"]` etc.
- **Workaround / fix:** Added `_js_str()` helper that escapes `"` → `\"` and `\` → `\\` before embedding in JS template strings.
- **Prevent next time:** Any code that generates JavaScript strings from Python values must quote-escape. Add a lint rule or test that catches unescaped quotes in generated JS.
- **Prevent next time:** Run anything that might write files from a scratch dir first; check `git status` after every test run in this repo.

---
## 2026-07-17 — Super Z / GLM (Z.ai cloud sandbox)
- **Problem:** First Railway deploy of the FastAPI control plane failed. Every gunicorn worker crashed on startup with `PermissionError`, so the server never bound and the `/health` healthcheck timed out. Railway's deploy log identified the root cause: `src/core/snapshot/__init__.py` calls `os.makedirs("config")` + `os.makedirs("data/snapshots")` at IMPORT time, but the container runs as non-root `appuser` and the `/app` directory was root-owned (only `/app/data` had been chowned).
- **Cost:** One failed deploy + one extra iteration cycle (~15 min of build + debug time on Railway's side, since this sandbox has no Docker to pre-verify locally).
- **Cause:** Two compounding issues:
  1. **Product code smell (root cause):** `src/core/snapshot/__init__.py:_initialize_module()` runs at module-import time and calls `os.makedirs()` with RELATIVE paths (`"config"`, `"data/snapshots"`) — resolved against whatever the cwd is at import time. Import-time side effects that touch the filesystem are fragile: they crash any environment where the cwd isn't writable by the importing user (containers, read-only installs, CI sandboxes).
  2. **Dockerfile gap (trigger):** `WORKDIR /app` creates `/app` owned by root. The original `RUN mkdir -p /app/data && chown -R appuser:appuser /app/data` only chowned the `data/` subtree — not `/app` itself. So `appuser` could write to `/app/data/...` but NOT create a new top-level dir like `/app/config/`.
- **Workaround / fix:** Dockerfile-only fix (commit pending): pre-create `config/`, `data/snapshots/`, `output/`, `logs/`, `.checkpoints/` AND `chown -R appuser:appuser /app` (the directory itself, not just its contents). Pre-creation makes the import-time `os.makedirs(..., exist_ok=True)` a no-op; the `/app` chown covers any future runtime-created dirs. Source-level fix is backlogged (see `tasks/backlog.md`).
- **Prevent next time:** (a) When deploying Python apps as non-root in containers, ALWAYS chown the WORKDIR itself, not just the subdirs you pre-create — `WORKDIR` creates the dir as root and `COPY --chown=...` only chowns the files it brings in, not the parent. (b) When smoke-testing a Dockerfile locally without Docker (venv-only), grep the codebase for `os.makedirs` / `Path(...).mkdir` at MODULE LEVEL (not inside functions) — those are import-time side effects that will crash the same way under any restricted cwd. Found one such call here: `src/core/snapshot/__init__.py:260 _initialize_module()`.

---
## 2026-07-17 — Linebet WAF block: datacenter-IP fingerprinting, not geo-blocking

**Context:** Session 9 continuation — tried to validate the Linebet
scraper against the live site from the Z.ai cloud sandbox.

**What happened:**
- Every Playwright profile (default Chromium, Chrome 124 Linux/Win,
  Firefox) gets HTTP 203 → redirect to `/en/block` from linebet.com.
- Tried 3 free US proxies (from proxyscrape.com list) — same 203 block.
- Tried 5 alt entry points (/en/prematch, /en/live, /m/en, /en/sport/1,
  /en/sport/football) — all 203.
- The block response comes from nginx (header `x-id: hk2-hw-edge-gc21`)
  NOT from a JS challenge — it's a server-side decision based on the
  incoming request, before any SPA code runs.
- Even when blocked, the technical-pages app DOES fire real API calls
  to `/bff-api/config/group/get`, `/bff-api/config/v2/contacts.json`,
  `/analytics-module-api/v1/analytics`, `/fatman-api/<hash>/...`. Those
  were captured and committed as snapshots
  (`src/sites/linebet/snapshots/raw/waf_block_page_bodies.json`).

**Root cause:** Linebet's WAF recognises datacenter IP ranges (including
datacenter proxies) and hard-blocks them at the edge. The block is NOT
based on user-agent (we tried real Chrome 124 UAs), NOT based on
headers (we sent full sec-ch-ua / sec-fetch-* suites), NOT based on
geolocation (US proxies also blocked). It's IP-reputation-based.

**Workaround built this session:** HAR export + replay pipeline
(`src/sites/linebet/scripts/har_export.py` +
`har_replay.py`). Operator runs `har_export` from a residential IP,
ships the HAR file, developer runs `har_replay` to extract events
without a live browser. End-to-end tested with a synthetic HAR fixture
(`src/sites/linebet/snapshots/raw/synthetic_prematch.har`) — works.

**Prevent next time:**
1. When targeting a site with a known WAF (Linebet, Cloudflare-protected
   sites, etc.), build the HAR export + replay path FIRST, before
   attempting live validation. The sandbox is almost always blocked.
2. Don't waste time on free proxies — they're datacenter IPs too, the
   WAF blocks them just the same. Either use a paid residential-proxy
   service (Bright Data, Soax, IPRoyal) or accept the HAR workflow.
3. When the extractor returns 0 events but captures > 0 responses,
   suspect that the captured responses are from the technical-pages /
   block page (not the main app) and check the captured URLs against
   the known sports-data endpoint patterns.

---
## 2026-07-17 — Claude Opus 4.8 (Session 11, local agent)

- **Problem 1 — both local browser surfaces egress from a US datacenter IP.**
  Assumed a *local* agent on Baos-Mac-mini would present the user's residential
  IP (Sessions 9/10 blamed the WAF on the Z.ai datacenter IP). Wrong: BOTH
  `mcp__Claude_Browser__*` (in-app cloud browser) AND `mcp__claude-in-chrome__*`
  ("Claude in Chrome") egress from `135.180.70.225`, flagged US, and hit
  linebet's geo-block (203 → `/en/block`). Neither routes through the user's
  home network. Cost: ~2 browser round-trips confirming the block.
  - **Prevent next time:** a local Claude Code agent does NOT get the user's
    residential IP for free — the browser tools egress from Anthropic infra
    (US). Reaching a geo/WAF-blocked site requires an explicit proxy the USER
    supplies (VPN on their machine, or a proxy endpoint). Don't assume "local =
    residential." Also: linebet's block IS geo-based here (names the country),
    distinct from the Session 9 sandbox block which read as datacenter-IP
    fingerprinting — both can be true depending on the egress.

- **Problem 2 — pytest async config is inert (repo config bug).** New
  `async def` tests errored with "async def not natively supported" despite
  `asyncio_mode = "auto"` in `pyproject.toml`. Root cause: `pytest.ini` exists
  and shadows pyproject, but its section header is `[tool:pytest]` (setup.cfg
  style) so pytest reads NO config from it either — asyncio_mode never applies.
  (Already a known backlog item.) Cost: ~1 test-run cycle.
  - **Prevent next time:** in this repo, mark async tests explicitly with
    `@pytest.mark.asyncio` (the established convention — see
    `tests/unit/test_feature_flag_service.py`); do not rely on
    `asyncio_mode=auto` until the `pytest.ini` header bug is fixed. Custom
    markers (`integration`/`unit`) also warn as "unknown" for the same reason,
    but `-m "not integration"` selection still works.
