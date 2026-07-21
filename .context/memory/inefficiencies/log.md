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
## 2026-07-20 — GitHub Copilot / DeepSeek V4 Flash Free (Session 21)

- **Problem:** Knew the platform was Windows (recorded in user prefs since Session 3) but never audited `.context/core/` scripts against it. The protocol's `context-sync` is POSIX-only and the `sh` commands in `kickoff.md` Step 1 are broken on this system — yet every session that followed the literal instructions silently failed or skipped this step without logging why.
- **Cost:** Multiple sessions with a silently broken Step 1. The user had to point out the gap directly before it was investigated. ~15 min of discovery work that should have been done in Session 3.
- **Cause:** Instructions were treated as literal truth rather than as data to validate against the environment. "The protocol says run `sh ...`" was processed as a command, not as a proposition to check. Also, no cross-reference existed between "environment facts" and "protocol requirements" — the agent had the facts but never connected them.
- **Workaround / fix:** PowerShell alternative commands documented in `overrides/rules.md`. Flaw logged in `flaws/log.md`.
- **Prevent next time:** Before executing any environment-dependent command from the protocol, cross-reference against known platform facts. When the protocol says `sh` or `bash` or `/bin/`, verify it exists on PATH first. If the protocol ships platform-specific tooling, audit it proactively — don't assume it works on your platform just because it's documented.
---
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

---
## 2026-07-19 — GitHub Copilot / DeepSeek V4 Flash Free
- **Problem:** After reading `.context/kickoff.md` + Step 3 memory + the protocol edition, I asked the user "What's next?" instead of continuing autonomously on the existing task (cross-skin H2H failure investigation). Then I ran through Phase 1 protocol steps mechanically without connecting them to the conversation's active target — the protocol became the task instead of the method.
- **Cost:** ~2 wasted round-trips (my question + user correcting me + running redundant Phase 1 steps).
- **Cause:** Lost the conversation context after reading protocol. Treated the protocol as the session's purpose rather than its guide. Didn't log my own violation in real time.
- **Workaround / fix:** After the user pointed it out, logged this entry. The standing target was already established in conversation — should have proceeded with investigation immediately after loading context.
- **Prevent next time:** When entering a conversation with an active task, note the existing target BEFORE running Phase 1. The protocol's "check the user's first chat message for a target" rule applies even after protocol re-reads mid-conversation. And log inefficiencies as they happen, not when prompted.

---
## 2026-07-20 — GitHub Copilot / DeepSeek V4 Flash Free (Session 19)
- **Problem:** After implementing period_scores extraction (code changes + tests passing), I updated AGENTS.md to document the work — but ignored `.context/memory/` files entirely. The user corrected me twice: first about API-first vs DOM extraction emphasis, then about .context memory protocol vs AGENTS.md. The protocol's Phase 5 (Steps 15-17) explicitly says to update memory files — I knew this but still defaulted to AGENTS.md.
- **Cost:** ~3 user corrections + rework of which files to update.
- **Cause:** Protocol knowledge was present but not activated at the right time. AGENTS.md was attached in context and felt like "the right place" for project documentation. Memory of the .context protocol phases faded after reading 700+ lines of protocol text earlier.
- **Workaround / fix:** The user redirecting me forced me to re-read kickoff.md and follow Phase 1-6 properly. Memory files are now updated.
- **Prevent next time:** After making code changes, run through Phase 1-6 mentally BEFORE asking the user what to do next. Phase 5 (memory updates) is mandatory, not optional — treat it as part of "done."

---
## 2026-07-20 — GitHub Copilot / DeepSeek V4 Flash Free (Session 21 — H2H integration)
- **Problem:** Relied on the conversation-summary artifact instead of reading actual `.context/` files before working. Three concrete failures:
  1. Did not read `kickoff.md` at session start — the summary claimed I had, but that described the *previous* session.
  2. Did not read `workflows/active.md`, `inefficiencies/log.md`, or `flaws/log.md` before acting.
  3. Trusted the summary's claim that `config.py` already had `"h2h": True` — but when I actually grepped for it, it wasn't there. If I hadn't checked by accident, the feature flag would have been missing from the commit.
- **Cost:** ~10 min of rework (had to add the missing feature flag after-the-fact, plus this audit). Risk of shipping incomplete code.
- **Cause:** Conversation-summary over-reliance. The summary is a compressed orientation tool, not an authoritative source. I treated it as equivalent to having read the files themselves.
- **Prevent next time:** Treat conversation summaries as "directional hints" only. Before any code change, verify the actual file state by reading it. Always run Entry Steps (kickoff → memory → protocol) at session start regardless of what the summary says.

---
## 2026-07-20 — Claude Code / claude-opus-4-8 (Session 23 — betb2b e2e + compression)
- **Problem:** The task ("make sure it runs e2e and all endpoints collect data") cannot be fully satisfied on-demand: every betb2b feed is geo/WAF-gated and depends on the operator's Kenya proxy tunnel (bore.pub:1074), which was down (TCP conn refused). No sandbox/local egress can substitute.
- **Cost:** ~5 min confirming the blocker (TCP probe + reading the last validate summary) before pivoting to the offline-verifiable slice + the compression deliverable.
- **Cause:** Live validation is inherently operator-gated (residential/allowed-country egress). The proxy is an ephemeral tunnel, up only when the operator runs it on their Windows box.
- **Workaround / fix:** Verify everything offline (tests, CLI JSON shape, compression); ship the compression feature; report the live blocker with the exact resume command. Left `tasks/current.md` pointing at the blocker.
- **Prevent next time:** Before promising a live betb2b run, TCP-probe bore.pub:1074 first (`socket.connect`); if refused, the tunnel is down — do the offline slice and hand the live step back to the operator with env vars + command.

---
## 2026-07-21 — GitHub Copilot / DeepSeek V4 Flash Free (Session 24)
- **Problem 1 — Proxy assumption was wrong.** Sessions 9–23 all assumed linebet needed a proxy tunnel (bore.pub:1074) from Kenya. Session 23 was blocked entirely because "proxy tunnel down." Session 24 discovered that running *without* the proxy (`BETB2B_PROXY_URL` unset) works perfectly from Kenya — linebet's `allowed_countries: ["KE"]` allows direct Kenya egress. The proxy assumption persisted unexamined for 15 sessions.
- **Cost:** At minimum Session 23's entire live e2e goal was abandoned (~30 min). Prior sessions may have been slowed by proxy setup/teardown overhead. Unknown sessions where the operator was asked to start a tunnel unnecessarily.
- **Cause:** The proxy was declared in the original skin YAML config as the default, and "linebet needs proxy" became accepted truth. No one tried running without it — the env vars were always set, so the code never exercised the direct path. Also, no test/doc explicitly said "try without proxy if your egress is in an allowed country."
- **Workaround / fix:** This session ran without any proxy env vars. Scrape succeeded (28 prematch events, 63.6s). Added `BETB2B_PROXY_URL` docs in AGENTS.md saying it's optional.
- **Prevent next time:** Before declaring a site unreachable, try direct mode first — especially for `allowed_countries` skins. The proxy is a fallback, not a requirement. Document in `AGENTS.md` for each skin whether direct mode works from which egress.
- **Problem 2 — CLI argparse `%` formatting bug.** The `--compress` help string `"~85-90%"` causes `ValueError: badly formed help string` because Python argparse interprets `%` as format specifiers. This bug was shipping since the compress feature was added (Session 23), blocking ALL CLI commands. Not caught by tests (no CLI smoke tests).
- **Cost:** ~5 min to diagnose + fix once a CLI command was actually run. Could have been caught by a single integration test.
- **Cause:** No test exercises the CLI entry point. The `%` literal needs `%%` in argparse help strings — a known Python pitfall.
- **Workaround / fix:** Changed to `"~85-90%%"`. All CLI commands now work.
- **Prevent next time:** Add a CLI smoke test that calls `parser.parse_args(["--help"])` or similar for each subcommand. Better yet, add a single integration test that runs `python -m src.sites.betb2b.cli.main --help` and verifies exit code 0.

---
## 2026-07-21 — Claude Code / claude-opus-4-8 (Session 25 — betb2b live DOM + markets)
- **Problem 1 — wrong CLI entry point in the handoff (silent no-op).** Both `tasks/current.md` (Session 25 setup) and the Session 24 inefficiency "prevent next time" recommend `python -m src.sites.betb2b.cli.main`. But `cli/main.py` has NO `if __name__ == "__main__"` guard — running it as a module executes nothing and exits 0 with zero output. The real entry point is `python -m src.sites.betb2b.cli` (the package `__main__.py`). Ran the "correct-looking" command 3× getting empty output + exit 0 before checking for `__main__`.
- **Cost:** ~10 min chasing "why does the CLI print nothing?" across three invocations + reading argparse/dispatch/footer.
- **Cause:** A wrong invocation got written into project memory (current.md + an inefficiency's prevent-next-time) and propagated. `.cli.main` *looks* right (it's where `BetB2BCLI` lives) but isn't runnable as `-m`.
- **Workaround / fix:** Use `python -m src.sites.betb2b.cli`. Corrected the command in `tasks/current.md` + backlog. Left a NOTE in the new backlog items.
- **Prevent next time:** When a `-m` module invocation exits 0 with NO output, suspect a missing `__main__` guard — check `python -c "import runpy"`-style or just `grep __main__`. And: a console-script entry in `pyproject.toml` would remove the ambiguity entirely (backlog candidate).
- **Problem 2 — handoff over-scoped the GetGameZip work.** `current.md` Phase 2 said enrichment "is NOT running... add `_enrich_with_markets()` mirroring `_enrich_with_h2h()`." It already existed (`_enrich_dom_events_with_odds`, wired + default-on) — the real issue was a one-line skip-condition bug. Reading the code (Phase 1) surfaced this quickly, so low cost, but the plan would have had me build a duplicate method.
- **Cost:** ~0 (caught during mandatory code-read) — noted so future handoffs verify "missing feature" claims against the code before scoping a rebuild.
- **Prevent next time:** A handoff claiming a feature is missing should cite the grep that proves absence; "0 fetched" is a symptom, not proof the code path doesn't exist.
- **Problem 3 — bore proxy dropped mid-session.** `bore.pub:50670` was up for the captures + GetGameZip fetches, then dropped to HTTP 000 and did not recover, blocking the *integrated* end-to-end run. Consistent with the standing "tunnels rotate" warning.
- **Cost:** ~5 min of retries; the integrated confirmation is now backlogged.
- **Prevent next time:** Capture all live artifacts you'll need (HTML + a few real GetGameZip responses) in ONE proxy window early, so later code validation doesn't depend on the tunnel staying up. (Did this — every fix was validated from the early captures.)
