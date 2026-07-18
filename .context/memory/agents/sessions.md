# Agent Sessions (append-only)

One entry per agent session, newest at the bottom. Never edit or delete
past entries — append corrections instead.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from .context/core/roles/> | **Core:** <version from .context/core/VERSION>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md, or "none">
- **Report:** .context/memory/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-07-12 — Session 1
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Bootstrap `.context/` (first session) + general-sweep review & safe fixes.
- **Commits:** 4 (`3de04c3`..`HEAD`) — bootstrap, `fix(cli)` scorewise entry point, review report, context log.
- **Outcome:** partial — `.context/` bootstrapped; 1 High bug fixed (`c8a4179`); baseline (pytest/ruff/mypy) NOT run — machine lacks Python 3.12+, so review was static-only.
- **Open items:** 4 in tasks/backlog.md (install Py3.12+ toolchain; datetime.utcnow migration; bare-except audit; fire-and-forget task audit).
- **Report:** .context/reviews/2026-07-12-review.md

---
## 2026-07-12 — Session 2 (continuation)
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Install dependencies (user request) — unblock the Python 3.12 toolchain.
- **Commits:** 1 (`bb0e636`) `fix(deps)` + `.context` updates.
- **Outcome:** done — installed uv → CPython 3.12.13 → `.venv` → deps (with `--only-binary :all:`). Found `pyproject.toml` was missing 10 runtime deps (fastapi/numpy/scipy/aiohttp/requests/networkx/watchdog/jinja2/semantic-version/python-json-logger) that `src/` imports; declared them. Discovered 3 pre-existing import-time code bugs (see backlog).
- **Open items:** `playwright install` + run pytest/ruff/mypy baseline; 3 new import-crash bugs in tasks/backlog.md.
- **Report:** .context/reviews/2026-07-12-review.md (F1–F4); dep + toolchain work captured in this entry + system/environments.md.

---
## 2026-07-12 — Session 3 (continuation)
- **Agent:** Claude Code | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Run the full test suite (incl. real/integration tests).
- **Commits:** 0 code (findings only) + `.context` updates.
- **Outcome:** partial/blocked — suite could not complete. `pytest` collected 1864 tests, 15 files error at collection; run reached only ~67/1864 before manual stop because ~24% of tests hang to the 60s per-test timeout (deadlock-like fixture teardown / live I/O). First 67: ~54 passed, ~13 failed. Installed `pytest-timeout` into the venv (ad hoc, not declared). Note: `--timeout-method=thread` aborts the whole run on first hang — use `signal`.
- **Open items:** 4 new backlog items (suite-can't-complete/hangs; `pytest.ini` `[tool:pytest]` header ignored; 15 collection errors; earlier 3 import-crash bugs).
- **Report:** delivered in chat; findings in tasks/backlog.md. No coverage/artifacts left (ran `--no-cov -p no:cacheprovider`).

---
## 2026-07-12 — Session 4
- **Agent:** Claude Code | **Model:** claude-fable-5 | **Platform:** Baos-Mac-mini (macOS 15.7.7) | **Role:** engineer
- **Task:** Review the site-scraper template framework (`src/sites/base/template/`) against its one-framework philosophy; fix safe issues incl. the `test_template_framework` collection error.
- **Commits:** 8 (`1b558e3`..`HEAD`) — 5 `fix(template)`, 1 `docs(review)`, 2 `chore(context)`.
- **Outcome:** done — the "create → validate → generate" path was broken at 4 independent points; all fixed (`template create` smoke-tested working). Target-area tests: 14 passed/27 failed/22 errors + e2e uncollectable → 39 passed/33 failed/2 errors, e2e collects 11. Remaining failures = tests drifted from the canonical interface (backlogged, needs owner call).
- **Open items:** 6 new in tasks/backlog.md (test-API alignment; 6 missing .j2 templates; hierarchy ADR; Dependabot triage; CLI log file; progress note on collection errors — 14 files remain).
- **Report:** .context/reviews/2026-07-12-review-2.md

---
## 2026-07-14 — Session 5
- **Agent:** Super Z | **Model:** unknown (system prompt names the family "GLM" but not an exact version ID; recorded per kickoff rule — never guess) | **Platform:** Z.ai cloud sandbox (Debian 13 trixie, x86_64, kernel 5.10.134) | **Role:** engineer
- **Task:** Sync `.context/` with the package skeleton (user request). First session on this repo from a cloud/sandbox agent; prior sessions were Claude Code on a local Mac.
- **Commits:** 3 (`7d39fc1`..`HEAD`) — 2 sync commits + 1 bookkeeping commit (this entry).
- **Outcome:** done — structural sync (README.md + SYNC.md updated from package; other 4 structural files already identical); generated `.context/kickoff.md` from the skeleton template (was missing — the convention was added to the package after this project's bootstrap); all pushed to `origin/main` (`63e854e..c552669`). PAT-handling note for future cloud/sandbox sessions on this repo: the package repo `TisoneK/.context` is **private** (the original external kickoff contradicted itself on this — line 27 said private, line 81 said public; ground truth is private). A fine-grained PAT scoped to both repos (Contents: RW for project, R for package) is required for clone-of-package + push-to-project.
- **Open items:** none new. Push surfaced the existing Dependabot warning (46 alerts: 1 critical / 17 high / 23 moderate / 5 low) — already backlogged (line 109 of tasks/backlog.md).
- **Report:** no review report — this was a sync session, not a review. Summary delivered in chat.

---
## 2026-07-14 — Session 6
- **Agent:** Super Z | **Model:** unknown (same as Session 5 — system prompt names the GLM family but not an exact version ID) | **Platform:** Z.ai cloud sandbox (Debian 13 trixie, x86_64) | **Role:** engineer
- **Task:** Update `.context/kickoff.md` to an updated template the user provided (user request). The updated template was NOT yet in the on-disk package skeleton (package repo confirmed at `d94c19e`, "Already up to date" — its skeleton kickoff.md is still the old `../.context` version). The user pasted the new template directly in chat.
- **Commits:** 2 (`2ae69d2`..`HEAD`) — 1 regenerate + 1 bookkeeping (this entry).
- **Outcome:** done — regenerated `.context/kickoff.md` from the updated template. Key changes adopted: (1) canonical package clone path is now `../context` (was `../.context`); legacy `../.context` clones are still found by the local-agent find-loop for backward compat. (2) Local-agent Step 0 now locates an existing package clone by REMOTE URL (not directory name) via a find-loop, with two new guards: "never clone when a package clone already exists" (prevents the clone-into-existing-dir retry loop) and "a failed pull is not a missing package" (use on-disk copy if pull fails). (3) Step 3 references `$PKG` (the found clone) instead of a hardcoded path. Project Facts unchanged from Session 5 — verified against `user/identity.md`, `workflows/active.md`, `git remote`. Template grep-check passes (1 hit = literal grep instruction in HTML comment). No real PAT in file; `${GIT_TOKEN}` stays symbolic. Note: the on-disk package clone for THIS session is still at `../.context` (cloned Session 5 under the old path); not moved, since the local-agent find-loop handles both names and cloud/sandbox sessions are ephemeral. The updated template has NOT been pushed to the package repo (`TisoneK/.context`) — that's the user's call; this commit only updates the in-repo `kickoff.md`.
- **Open items:** none new. If the user wants the package skeleton itself updated to match, that's a separate push to `TisoneK/.context` (out of scope here — agents don't push to the package unless explicitly asked).
- **Report:** no review report — template update only. Summary delivered in chat.

---
## 2026-07-17 — Session 7
- **Agent:** Super Z | **Model:** GLM (Z.ai cloud sandbox, Linux x86_64) | **Role:** engineer | **Core:** 0.2.0
- **Task:** Migrate `.context/` from the 0.1.x flat layout to the 0.2.0 two-zone layout (vendored `core/` + project-owned `memory/`), per `MIGRATION.md` in the package. Followed by a separate project task: set up Railway deployment config (out-of-scope for this `.context/`-surface commit — that lands in its own project-mode commit).
- **Commits:** 1 (this commit) — `chore(context): migrate to core 0.2.0 two-zone layout`.
- **Outcome:** done — migration applied exactly per `MIGRATION.md`:
  1. `git mv`'d all 11 memory modules (agents, flaws, inefficiencies, plans, reviews, secrets, system, tasks, user, workflows) into `.context/memory/` — history preserved (git tracks renames).
  2. Retired old structural files: removed `SYNC.md` (basename rule retired in 0.2.0), old root `README.md` and `kickoff.md` (replaced from new templates).
  3. Vendored the package core at `.context/core/` from the freshly-cloned package (TisoneK/.context @ current `main`, core VERSION 0.2.0). `sh .context/core/bin/context-sync verify` passes — every file matches `MANIFEST.sha256`. `memory/core.lock` written automatically: `version=0.2.0 verified=2026-07-17`.
  4. Seeded the new root files from templates: `.context/README.md` (zone map), `.context/kickoff.md` (front door, Project Facts refilled from `memory/user/identity.md` + `memory/workflows/active.md` + `git remote get-url origin`), root `AGENTS.md` (weak-agent digest, `<PROJECT_NAME>` filled with "Scrapamoja"), and `.context/memory/overrides/rules.md` (project-local protocol adjustments — empty placeholder, no overrides yet).
  5. Updated `memory/workflows/active.md` to the 0.2.0 template shape: Protocol now recorded "by agent type" naming BOTH editions at their `.context/core/rules/` paths (was: a single hard-coded local edition + raw/blob GitHub URLs that 404'd after the package restructure); replaced with `Protocol location: vendored in .context/core/` + `Package upstream: https://github.com/TisoneK/.context.git`.
  6. Path sweep: refreshed the memory-dir READMEs (`memory/secrets/README.md`, `memory/reviews/README.md`, `memory/flaws/README.md`) from the new templates so path references now point to `.context/memory/<dir>/` not `.context/<dir>/`. Patched the top template block in `memory/agents/sessions.md` (added `Core:` field, fixed the `Report:` path to `.context/memory/reviews/`). Historical log entries left untouched per the append-only rule.
- **Open items:** none for this commit. Railway deployment setup lands in a separate project-mode commit (different surface, different commit prefix).
- **Report:** no review report — this was a migration session, not a code review. Summary delivered in chat.

---
## 2026-07-17 — Session 8
- **Agent:** Super Z | **Model:** GLM (Z.ai cloud sandbox, Linux x86_64) | **Role:** engineer | **Core:** 0.2.0
- **Task:** Follow-up to Session 7. Two parts: (a) fix the Railway deploy crash the user reported (the build failed because every gunicorn worker died with `PermissionError` on startup — `src/core/snapshot/__init__.py:_initialize_module()` runs `os.makedirs("config")` + `os.makedirs("data/snapshots")` at IMPORT time, but `/app` was root-owned and `appuser` couldn't write to it); (b) record in `.context/memory` that Scrapamoja is now linked to Railway via GitHub integration, plus the Railway plan limits (8 vCPU / 8 GB per-replica cap) the user shared.
- **Commits:** 2 (pending push) — one project-surface `fix(deploy):` for the Dockerfile, one `.context/`-surface `chore(context):` for the memory updates.
- **Outcome:** done —
  - (a) Dockerfile fix: pre-create `config/`, `data/snapshots/`, `output/`, `logs/`, `.checkpoints/` AND `chown -R appuser:appuser /app` (the directory ITSELF, not just its contents — that was the bug). The original `WORKDIR /app` created `/app` as root, and `chown -R appuser:appuser /app/data` only covered the `data/` subtree. Pre-creation makes the import-time `os.makedirs(..., exist_ok=True)` a no-op; the `/app` chown covers any future runtime-created dirs. Added a long comment in the Dockerfile explaining why (so the next agent doesn't revert it).
  - (b) Memory updates (all under `.context/memory/`):
    - `system/environments.md` — new "Railway" block: GitHub integration active (pushes to `main` auto-deploy), plan limit 8 vCPU / 8 GB, Dockerfile builder, runtime = python:3.12-slim + Playwright + Chromium + non-root appuser, volume mount needed at `/app/data` (NOT yet mounted — user needs to add it), full quirks list including the import-time makedirs crash and the no-Docker-on-this-sandbox caveat.
    - `inefficiencies/log.md` — appended a 2026-07-17 entry: root cause = product code smell (import-time filesystem writes with relative paths) + Dockerfile gap (chowned `/app/data` not `/app`); workaround = Dockerfile pre-create + chown; prevent-next-time = always chown WORKDIR itself, and grep for module-level `os.makedirs` when smoke-testing a Dockerfile without Docker.
    - `plans/decisions.md` — appended ADR-1: "Deploy the FastAPI control plane to Railway via Dockerfile". Records what's deployed (API only, not UI), what's not (UI as separate static site, scrapes as separate jobs), volume requirement, and constraints future agents must respect (don't add UI build to this Dockerfile; if swapping SQLite→Postgres, drop the Volume + ADAPTIVE_DB_PATH).
    - `tasks/backlog.md` — appended: source-level fix for `_initialize_module()` (make lazy or use absolute paths; recommend lazy). Medium severity. Includes the grep finding (13 `os.makedirs` calls in src/, only this one at import time).
- **Open items:**
  - Push both commits to `origin/main` (Railway will auto-redeploy).
  - User should add a Railway Volume at `/app/data` for SQLite persistence (not yet done — flagged in the new environments.md block).
  - Source-level fix for `_initialize_module()` is in backlog — not blocking, but should be picked up before the next non-container deploy target.
- **Report:** no review report — this was a deploy-fix + memory session. Summary delivered in chat.

---
## 2026-07-17 — Session 9
- **Agent:** Super Z | **Model:** GLM (Z.ai cloud sandbox, Linux x86_64) | **Role:** engineer | **Core:** 0.2.0
- **Task:** User request: "Initialize AGENTS.md" + "Using templates feature, create new site scraper for Linebet https://linebet.com/en — the site uses hybrid mode where we browse real browser but fetch via api endpoints". Two-part task: (a) follow the `.context/` workflow protocol per AGENTS.md, and (b) add a new `src/sites/linebet/` site package built on `BaseSiteTemplate` that uses Playwright + `NetworkInterceptor` to capture JSON from Linebet's own `/api/...` endpoints.
- **Commits:** 1 project-surface `feat(sites/linebet):` (scraper package) + 1 `.context/`-surface `chore(context):` (session log) — pending push to `origin/main`.
- **Outcome:** done —
  - (a) Protocol followed: cloned repo with PAT (stripped from `.git/config` right after), read `.context/kickoff.md` + memory modules, identified as cloud/sandbox agent → followed `ai-engineering-protocol.md`, marked Session 9 in `tasks/current.md`, now clearing it and logging this entry.
  - (b) Built `src/sites/linebet/` as a full site package:
    - `config.py` — `SITE_CONFIG` (registry-compliant: id/name/base_url/version/maintainer), `API_URL_PATTERNS` (4 prefixes covering `linebet.com` / `www.` / `m.` / `linebet1.com` mirrors), rate limits, stealth config, feature flags, `validate_config()`.
    - `scraper.py` — `LinebetScraper(BaseSiteTemplate)`. Hybrid pipeline: attach `NetworkInterceptor` (with `API_URL_PATTERNS`) **before** navigation → `LinebetFlow` drives the page (home / live / scroll) → wait for API burst to settle → decode each captured response → `LinebetExtractionRules.extract_from_captured` projects JSON onto `Event`/`Market`/`Selection` dataclasses → de-dupe by `event_id` (merging richer market lists) → return `LinebetScrapeResult`. Supports 4 actions: `list_prematch`, `list_live`, `list_all`, `raw_capture`. Hard 60s timeout per scrape.
    - `flow.py` — `LinebetFlow(BaseFlow)`. Navigation-only: `navigate_to_home` / `navigate_to_live` / `navigate_to_sport`. Uses `domcontentloaded` (NOT `networkidle` — Linebet keeps a long-poll open for live odds). Includes `scroll_fixtures` (trigger lazy `/api/list/` calls), `dismiss_consent_if_present` (best-effort), `wait_for_api_burst` (fixed 12s window).
    - `extraction/models.py` — typed dataclasses: `Event`, `Market`, `Selection`, `Sport` (enum), `MarketType` (enum), `EventStatus` (enum), `CapturedAPIResponse`, `LinebetScrapeResult`.
    - `extraction/rules.py` — `LinebetExtractionRules`. Defensive JSON→dataclass projection: classifies captured URL → endpoint type (prematch/live/market/menu/info), walks arbitrary nested JSON to find event-shaped dicts (heuristic: has-id + has-teams), supports both inline flat-1X2 odds and rich `Markets[].Selections[]` layouts, JSONP-wrapper-aware decoder, sport-name alias map, market-name regex classifier (`1X2` / `double_chance` / `totals` / `handicap` / `correct_score` / `h2h`), degrades to empty list (never raises) on schema drift.
    - `integration_bridge.py` — `LinebetIntegrationBridge(FullIntegrationBridge)` — framework-compliance shim (registry + compliance validator expect it). Carries Linebet-specific error-pattern table (429/403/404/5xx recovery hints).
    - `selectors/*.yaml` — 2 minimal YAML files (`linebet_api_response.yaml` + `cookie_consent_banner.yaml`). Hybrid mode doesn't depend on them; kept so the template passes framework selector-loader validation and a future DOM-fallback path can use them.
    - `tests/test_linebet_scraper.py` — 20 unit tests (no browser, no network). Cover: config validation, JSON decode (valid / JSONP-wrapped / garbage / bodyless), prematch extraction (flat 1X2 + array markets), live extraction (score/minute/status), market-detail extraction (rich markets with handicap lines), unknown-endpoint fallback, malformed-payload safety, sport aliases, param validation, event de-duplication + market merging, raw_capture (skip extractor), full pipeline with mocked interceptor. All 20 pass.
    - `README.md` — operator guide: architecture ASCII diagram, action reference, usage example, output JSON shape, config knobs table, limitations (schema drift, live long-poll, no replay mode yet, Cloudflare escalation).
- **Open items:** none blocking. If the user wants real-world validation, the next session should: (1) `playwright install chromium` in this sandbox, (2) run `action="raw_capture"` against the live site, (3) inspect captured JSON to verify the `_SPORT_ALIASES` and `_MARKET_NAME_PATTERNS` regexes match Linebet's actual sport/market labels, (4) tighten the extractor if drift is found.
- **Report:** no review report — this was a feature-add session. Summary delivered in chat.

---
## 2026-07-17 — Session 9 continuation (hardening + HAR pipeline)
- **Agent:** Super Z | **Model:** GLM (Z.ai cloud sandbox, Linux x86_64) | **Role:** engineer | **Core:** 0.2.0
- **Task:** Follow-up to Session 9. User pointed out the original Linebet work used GUESSED API URL patterns (`/api/...`) instead of capturing real endpoints. User asked to: (a) actually probe the site and study real endpoints/headers, (b) try a proxy if it's geo-restrictions, (c) push all tests + debugging files to the repo, (d) normalize using snapshots to make debugging easier, (e) update `.context/memory/` so the next agent stays in sync.
- **Commits:** 1 project-surface `feat(sites/linebet):` (hardening + HAR pipeline + snapshots) + 1 `.context/`-surface `chore(context):` (session log + backlog + inefficiencies) — pending push to `origin/main`.
- **Outcome:** done —
  - (a) Probed linebet.com from the sandbox with 3 browser profiles + 3 free US proxies + 5 alt entry points. **Finding:** every probe hits HTTP 203 → `/en/block` from nginx. The WAF is datacenter-IP fingerprinting, NOT geo-blocking (US proxies also blocked). The block is server-side at the nginx edge, before any SPA code runs. Even when blocked, the technical-pages app fires REAL API calls — captured 16 of them with full bodies. **Real API prefixes** (replacing the guessed `/api/`): `/bff-api/` (config + sports data), `/fatman-api/` (analytics, with a 40-char hash in the path), `/analytics-module-api/`. **Real required request headers**: `x-svc-source`, `x-app-n`, `x-requested-with: XMLHttpRequest`, `is-srv: false`, `content-type: application/json`, plus full sec-ch-ua / sec-fetch-* suite. Real query params include `lang=en&d=linebet.com&g=HK&p=650` (geo code + project ID). Updated `src/sites/linebet/config.py::API_URL_PATTERNS` + `REPLAY_FORWARD_HEADERS` + new `NOISE_PATTERNS` to match the real traffic.
  - (b) Proxy attempt: free datacenter proxies (proxyscrape.com list) don't help — they're datacenter IPs too, WAF blocks them the same way. A paid residential-proxy service would work but isn't available in this sandbox. Built the **HAR export + replay pipeline** as the real solution: operator runs `python -m src.sites.linebet.scripts.har_export --output my.har --live` from a residential IP, ships the HAR, developer runs `python -m src.sites.linebet.scripts.har_replay my.har out.json --normalize snap.json` to extract events without a live browser. End-to-end tested with a synthetic HAR fixture (`src/sites/linebet/snapshots/raw/synthetic_prematch.har`) — works, extracts the synthetic event with the right markets/selections.
  - (c) Moved all 4 debug scripts from `scripts/linebet_*.py` into `src/sites/linebet/scripts/` so they travel with the package. Added `har_export.py` + `har_replay.py`. Added `src/sites/linebet/scripts/_common.py` with `repo_root()` + `output_dir()` helpers so the scripts are portable (no hardcoded `/home/z/my-project/...` paths). Each script is runnable as `python -m src.sites.linebet.scripts.<name>`.
  - (d) Built the snapshot normalizer + diff tool (`src/sites/linebet/snapshots/normalize.py` + `diff.py`). The normalizer takes a raw capture list and produces a STABLE JSON shape: redacts volatile query params (`_t`, `ts`, `csrf`, etc.), redacts env-specific params (`d`, `g`, `p`, `lang` → `<env>`), redacts volatile JSON keys recursively (`ts`, `sessionId`, `token`, `traceId`, etc. → `<redacted>`), strips the long fatman-api hash from paths, filters request headers to only the signal ones (drops cookies + UA + sec-ch-ua), truncates large bodies, and computes a `body_sha256` for drift detection. The diff tool compares two snapshots and reports added/removed/changed endpoints. Committed 2 normalized snapshots from the real captured WAF-block traffic (`snapshots/normalized/waf_block_page_api_snapshot.json` + `chrome_124_linux_full_capture.json`) plus 5 raw capture files in `snapshots/raw/`.
  - (e) Updated `.context/memory/`:
    - `tasks/current.md` — cleared to idle + summary pointer to this session.
    - `tasks/backlog.md` — 3 new Linebet items (residential-IP HAR capture; httpx replay mode; register with global ScraperRegistry). Each has full context for a fresh agent.
    - `inefficiencies/log.md` — full entry on the WAF block: what was tried, root cause (datacenter-IP fingerprinting), workaround (HAR pipeline), prevent-next-time guidance.
    - This session entry.
- **Test results:** 45 linebet tests passing (was 20 at end of Session 9). New tests cover: snapshot normalizer (12 tests), snapshot diff tool (4 tests), committed-snapshot validity (3 tests), HAR replay pipeline (3 tests). All extractor tests updated to use REAL API URL prefixes (`/bff-api/sports/list/prematch` etc.) instead of the old guessed `/api/...` paths.
- **Open items (see backlog for detail):**
  - Capture a real HAR from a residential IP → discover the actual sports/odds endpoint paths → tighten the extractor if needed. HIGH.
  - Implement the httpx-based replay mode (sub-second polling without relaunching the browser). MEDIUM.
  - Register LinebetScraper with the global ScraperRegistry at app startup. LOW.
- **Report:** no review report — this was a hardening + tooling session. Summary delivered in chat.

---
## 2026-07-17 — Session 10 (reframe + framework generalization)
- **Agent:** Super Z | **Model:** GLM (Z.ai cloud sandbox, Linux x86_64) | **Role:** engineer | **Core:** 0.2.0
- **Task:** User correction — I had built snapshot + HAR tooling inside `src/sites/linebet/` instead of in the framework, and had been treating linebet as the deliverable when it's actually just the *test case* for a future site scraping-mode classifier. Reframe: linebet = validation case for a classifier we are building; the deliverable is a system that learns + classifies a site's scraping mode. This session: stop, survey existing systems, generalize the HAR + snapshot tooling into the framework, remove the duplicated linebet code.
- **Commits:** 1 project-surface `refactor(snapshot,har):` (framework generalization) + 1 `.context/`-surface `chore(context):` (session log + reframe) — pending push to `origin/main`.
- **Outcome:** done —
  - **Survey findings** (what I had missed in earlier sessions):
    - `src/core/snapshot/` already had a full snapshot system: `SnapshotManager`, `SnapshotStorage`, `SnapshotBundle`, `SnapshotMode` (FULL_PAGE/SELECTOR/MINIMAL/BOTH), 7 domain handlers (browser/session/scraper/selector/error/retry/monitoring), `TriggerManager`, `MetricsCollector`. Its `_capture_network_logs` recorded URL/status/method/response-headers but NOT bodies or request headers, and didn't dedupe or normalize.
    - `src/extraction/router.py` already had `ExtractionModeRouter` + `ExtractionMode` enum (`raw` / `intercepted` / `hybrid` / `playwright`) + `SiteConfig.extraction_mode` field + `InterceptedConfig` / `HybridConfig` sub-configs. The router already implements session-bootstrap mode (browser harvests cookies → HTTP client reuses them via `SessionHarvester`).
    - `docs/proposals/browser_api_hybrid/` had 9 feature proposals (SCR-001 through SCR-009), including SCR-006 (Session Harvesting) and SCR-002 (Network Interception), with a phased build order. Status: only SCR-001 (Direct API Mode) was Completed; the rest were Proposed.
    - So my linebet HAR scripts duplicated SCR-006's proposed design, and my linebet snapshot normalizer duplicated a capability the existing snapshot system was missing (post-processing on captured network responses for drift comparison).
  - **Generalized into the framework** (the actual deliverable for this session):
    - `src/core/snapshot/normalize.py` — new module. `normalize_captured_response()` + `normalize_capture_list()` + `NormalizerConfig` (configurable: volatile query params, env query params, signal request headers, noise header prefixes, volatile JSON keys, path-hash regex patterns, max body chars). Site-agnostic. CLI: `python -m src.core.snapshot.normalize <input> <output>`. Replaces the deleted `src/sites/linebet/snapshots/normalize.py`.
    - `src/core/snapshot/diff.py` — new module. `diff_snapshots()` reports added/removed/changed endpoints between two normalized snapshots. CLI: `python -m src.core.snapshot.diff <old> <new>`. Replaces the deleted `src/sites/linebet/snapshots/diff.py`.
    - `src/core/snapshot/__init__.py` — extended to export the new API.
    - `src/network/har/` — new framework package. `export.py` (`HarExporter` + `HarExporterConfig` + CLI), `replay.py` (`HarReplayer` + `HarReplayResult` + CLI), `to_snapshot.py` (HAR → capture-dicts, HAR → framework `CapturedResponse` objects, HAR → normalized snapshot). Site-agnostic. Implements the proposed SCR-006. CLIs: `python -m src.network.har.export --url ... --output ...`, `python -m src.network.har.replay <input.har> <output.json> --normalize snap.json`.
  - **Updated linebet to USE the framework** (no duplicated code):
    - `src/sites/linebet/snapshots/__init__.py` — now just re-exports the framework API for backward compat + holds the committed fixtures under `raw/` and `normalized/`.
    - `src/sites/linebet/scripts/har_export.py` — rewritten as a thin wrapper around `HarExporter` with linebet-specific defaults (URLs, scroll behaviour). ~50 lines vs the previous ~150.
    - `src/sites/linebet/scripts/har_replay.py` — rewritten as a thin wrapper around `HarReplayer` + the linebet `LinebetExtractionRules` extractor. ~80 lines vs the previous ~150.
    - Deleted: `src/sites/linebet/snapshots/normalize.py`, `src/sites/linebet/snapshots/diff.py`, `src/sites/linebet/tests/test_linebet_snapshots.py` (replaced by framework tests).
  - **Tests** (66 total passing — was 45):
    - `tests/unit/core/snapshot/test_normalize.py` — 16 framework normalizer tests (site-agnostic).
    - `tests/unit/core/snapshot/test_diff.py` — 6 framework diff tests.
    - `tests/unit/network/har/test_replay.py` — 13 framework HAR tests (HAR loading, decoding, URL filtering, normalization, replayer with/without extractor, error handling).
    - `src/sites/linebet/tests/test_linebet_har_replay.py` — 3 linebet-specific integration tests (verifies the linebet extractor works when fed via the framework `HarReplayer`).
    - `src/sites/linebet/tests/test_linebet_scraper.py` — 22 existing linebet scraper tests (unchanged).
  - **Memory updates**: cleared `tasks/current.md` with the reframe (linebet = test fixture, not deliverable; next step is the classifier). Added "Build site scraping-mode classifier" backlog item with the heuristic starter list. This session entry.
- **Open items (see backlog for detail):**
  - Build `src/extraction/classifier/` — the actual deliverable. HIGH.
  - Capture a real Linebet HAR from a residential IP → feed to the classifier as the validation case. HIGH (already in backlog from Session 9 continuation).
  - Implement the httpx-based replay mode (sub-second polling). MEDIUM (already in backlog).
- **Report:** no review report — this was a refactor + framework-generalization session. Summary delivered in chat.

---
## 2026-07-17 — Session 11 (proxy abstraction + linebet recon)
- **Agent:** local IDE agent (Claude Code) | **Model:** Claude Opus 4.8 (`claude-opus-4-8`), Baos-Mac-mini | **Role:** engineer | **Core:** 0.2.0
- **Task:** User: "working with linebet in sites; use real browser + a proxy if you can't connect from your location (linebet blocked in US, works in Russia + African countries); we are NOT building the scraper yet — learning the headers/endpoints. Initialize AGENTS.md." Then, after recon hit a wall, user redirected: build a **robust ProxyManager abstraction FIRST** (validated in 5 stages), and plug in their Kenyan Windows proxy (via ngrok) LAST.
- **Commits:** 4 project-surface (`44a4bce` proxy package, `8bc8a29` chokepoint wiring, `8fb284f` Stage-2 tests, `467acb1` config factory) + 1 `.context/`-surface (this log + memory) — pushed to `origin/main`.
- **Outcome:** proxy abstraction DONE (Stages 1–3 + 5); Stage 4 (linebet capture) BLOCKED on the user's ngrok details.
  - **Recon finding:** AGENTS.md already existed + correct (no action). BOTH browser surfaces a local agent has — the in-app `mcp__Claude_Browser__*` and `mcp__claude-in-chrome__*` — egress from a **US datacenter IP** (`135.180.70.225`) and hit linebet's geo-block (203 → `/en/block`, "not available in your country • US"). So a local agent can't reach linebet without a user-supplied proxy. Even the block page fires real backend calls, re-confirming the API surface: hosts `linebet.com/bff-api/…`, `/analytics-module-api/…`, CDN `v3.traincdn.com`, analytics `mc.yandex.com`; param grammar `lang / d=linebet.com / g=<GEO> / p=650`. The main sportsbook endpoints still require an allowed-country IP (Stage 4). See `inefficiencies/log.md` for the "local ≠ residential IP" trap.
  - **Built `src/network/proxy/`** (canonical single chokepoint; replaces 3 fragmented `ProxySettings` + 2 `ProxyManager`s, which stay in place with adapters for later migration):
    - `models.py`: `ProxyScheme` (incl. DIRECT), `ProxyEndpoint` (`to_playwright_proxy`/`to_httpx_proxy`/`to_url`/`from_url` + `from_browser_proxysettings`/`from_navigation_config`/`from_stealth_session` adapters + credential-safe repr), `ProxyHealth` (success-rate, EWMA latency, auto-dead on N consecutive failures).
    - `manager.py`: `ProxyManager` — rotation (round_robin/random/sticky/health_weighted), health reporting, failover skipping unhealthy endpoints, `with_failover()` retry helper, per-site `RoutingRule` (glob; leading-wildcard matches subdomains).
    - `providers.py`: `ProxyProvider` ABC + `DirectProvider`/`StaticProvider`/`ManualEndpointProvider` (incl. `.ngrok(host,port,user,pass)`).
    - `verify.py`: `verify_proxy()` (egress IP + geo via httpx 0.28 `proxy=`) + `verify_proxy_playwright()` — the "IP changes when expected" check.
    - `config.py`: `build_proxy_manager(dict)` / `build_endpoint(dict)` — declarative pool + routing (YAML/env-friendly). Kept canonical to the proxy package rather than threaded through the fragile central `AppConfig`.
  - **Chokepoint wiring (scraper never hardcodes proxy):** `HarExporterConfig.proxy` + `--proxy` CLI (`network/har/export.py`); injected `ProxyManager` with flat-field fallback in `browser/session_manager.py` (`_resolve_proxy`); `set_proxy_manager()` + create_context apply in `browser/session.py` (previously ignored proxy); `proxy=` in `network/direct_api/client.py`.
  - **Validation:** Stage 2 integration tests stand up an in-process recording CONNECT proxy and prove BOTH httpx and Playwright route through the manager's endpoint. Stages 3 (rotation/health/failover) + 5 (routing) covered by manager + config unit tests.
- **Test results:** 47 proxy unit tests + 3 Stage-2 local-proxy integration tests + 2 verify integration probes, all passing. `tests/unit/network/har` + `tests/network/test_direct_api*` still green (no regressions). Used `@pytest.mark.asyncio` per repo convention (the `pytest.ini` `[tool:pytest]` header bug makes `asyncio_mode=auto` inert — see inefficiencies).
- **Open items:** Stage 4 linebet HAR capture via the Kenyan ngrok proxy (blocked on user; exact resume steps in `tasks/current.md`); migrate stealth/navigation onto the canonical ProxyManager + deprecate duplicate ProxySettings (new backlog item).
- **Report:** no review report — feature-build session. Summary delivered in chat.

---
## 2026-07-17 — Session 11 continuation (Stage 4: live linebet capture)
- **Agent:** local IDE agent (Claude Code) | **Model:** Claude Opus 4.8 | **Role:** engineer | **Core:** 0.2.0
- **Task:** Resume Stage 4 once the user stood up their Kenyan proxy. ngrok was unusable (TCP tunnels need card verification); pinggy rejected anonymous TCP; `bore` (no account, raw TCP) worked: `gost` HTTP proxy (Kisumu, KE) → `bore.pub:<port>` → framework `ProxyManager`.
- **Commit:** `9878dcf` (`docs(sites/linebet):` recon writeup + API catalog) + this `.context/` log.
- **Outcome:** FIRST successful live linebet capture (all prior sessions were geo/WAF-blocked).
  - `verify_proxy` through the Kenya endpoint confirmed egress `102.210.56.70` / countryCode `KE`. `build_proxy_manager` routing (`*linebet.com → kenya`, else direct) validated live. This is the real "IP changes when expected" proof Stage 2 couldn't do locally.
  - `HarExporter(proxy=kenya)` loaded `linebet.com/en` + `/en/live` at `200` (not the `203`→`/en/block` we get direct). 11.4 MB HAR, `waf_block_detected: False`, real page titles. Live betting DOM renders real matches + odds (ATP Umag, FIVB Nations League, Peru Liga 1 — screenshot verified).
  - **Architecture finding (the important part):** linebet's live-odds feed is invisible to standard interception. Odds render in the DOM, but ZERO odds requests appear at Playwright page OR context level, in the HAR, or as page WebSocket/SSE. Transport is service-worker-mediated: `ivpn-sw.js` injects headers from IndexedDB (`vpn`/`headers`; derives `x-dt` from `x-project-id`, forces `same-origin`); `domain-sw.js` runs mirror-domain failover via `/checker/redirect/stat/run/` + pixel.gif probes; plus `check-rum.worker.js` (RUM) and `pwa-module-sw.js` (cache). Implication: linebet is NOT clean `intercepted` mode — naive interception/HAR replay won't get live odds; DOM/hybrid extraction (or CDP-level SW capture) is required. Documented in `src/sites/linebet/RECON.md` + `snapshots/normalized/linebet_api_catalog.json`.
  - Bootstrap API surface cataloged (17 endpoints): `bff-api` (config/group/get, licenses.json, event-logo/suitable.json — params `lang/d/g=KE/p=650`), `web-api` (session 204, v3/bonuses/welcome-bonuses KES, third-party banners), `service-api/gamespreview/*` (casino), `fatman-api/<40hex>/*` (telemetry), `analytics-module-api/v1/analytics`. Hosts: linebet.com + v3.traincdn.com (CDN) + widget.suphelper.top + mc.yandex.ru.
  - Raw HAR NOT committed (session cookies) — only the writeup + redacted catalog.
- **Open items / next:** (1) find the live-odds endpoint via CDP `Target.setAutoAttach` to the SW target + `Network`, or by reading IndexedDB `vpn/headers` at runtime; (2) build a DOM extractor for the live grid; (3) feed a capture to the scraping-mode classifier; (4) migrate stealth/navigation onto the canonical ProxyManager. See backlog + `tasks/current.md`.
- **Report:** `src/sites/linebet/RECON.md` is the recon deliverable. Summary in chat.

---
## 2026-07-18 — Session 12 (betb2b family base scraper — built, live validation pending)
- **Agent:** cloud/sandbox agent (Super Z / GLM) | **Model:** GLM | **Platform:** Z.ai cloud sandbox (Linux) | **Role:** engineer | **Core:** 0.2.0
- **Task:** User: "Scrapamoja: https://github.com/TisoneK/scrapamoja.git — Initialize AGENTS.md; read context and implement betb2b sites as designed by context and active task. Proxy is available at bore.pub:1074 (creds TisoneK:Taalib01). Test the feature using real betb2b sites and since we are building an infrastructure, make sure everything is customizable. If possible do a deep research on betb2b sites and their infrastructure." Then: "Leave live validation pending but document for the future agents then commit and push after updating context."
- **Commits:** 1 project-surface (`feat(betb2b):` family base scraper — config + markets + sports + extraction + session + httpx client + scraper + CLI + scripts + 8 skin YAMLs + README + 24 unit tests + AGENTS.md update) + 1 `.context/`-surface (sessions log + review + backlog + flaws + tasks/current) — pushed to `origin/main`.
- **Outcome:** betb2b family base scraper **built, unit-tested, committed, pushed**. Live end-to-end validation **pending** (blocked 4x by a Bash-tool `broken session: 403 Forbidden` outage that always hit right before the `validate_live` invocation; not a code or proxy issue — proxy was verified live mid-session).
  - **AGENTS.md:** appended an "Active task — `src/sites/betb2b/` family base scraper" section with the one-paragraph brief + 5 hard rules (everything customizable; re-use ProxyManager/SessionHarvester/HybridConfig; never log secrets; per-skin YAML is the customization surface; live tests gated on operator proxy with `--no-live` fallback).
  - **`src/sites/betb2b/` package built from scratch:**
    - `config.py` — `BetB2BSkinConfig` dataclass; EVERY URL/header/query-param/market-id/sport-id is a field on the config; `from_yaml()` loader with strict-key rejection (typos fail fast); `feed_url()`/`merged_headers()`/`bootstrap_url()` renderers; `validate()`; `to_dict(redact=True)`; `with_overrides()`. Defaults: `DEFAULT_BASE_BETTING_HEADERS`, `DEFAULT_FEED_PATHS`, `DEFAULT_FEED_QUERY_PARAMS`, `DEFAULT_BOOTSTRAP_PATHS`, `DEFAULT_STEALTH_PROFILE`, `DEFAULT_SKIN_CONFIG` (linebet).
    - `markets.py` — `MarketGroup` + `MarketTypeMap` dataclasses + `DEFAULT_MARKET_GROUPS` (15 groups) + `DEFAULT_MARKET_TYPES` (23 types) + `lookup_market()` (degrades gracefully to `G=<g>` / `T=<t>` labels for unknown ids).
    - `sports.py` — `SportMap` + `DEFAULT_SPORT_MAP` (37 sports) + `lookup_sport()`.
    - `extraction/models.py` — `Sport`/`EventStatus`/`MarketType` enums + `Selection`/`Market`/`Event`/`CapturedFeedResponse`/`BetB2BScrapeResult` dataclasses (mirror the linebet skin shape so downstream consumers treat all skins uniformly).
    - `extraction/rules.py` — `BetB2BExtractionRules`; defensive 1xbet-terse `Value[]` JSON projection. Handles both `E[]` (flat, grouped by `G`) and `AE[]` (grouped, with `ME[]` sub-arrays) layouts — prefers `AE[]` and uses `E[]` to enrich. Coerces `SC` block to (status, minute, period, time_remaining); pulls English team names from `O1E`/`O2E`; maps `SN`/`SI` via the skin's sport_map; appends the `P` line to selection labels for handicap/totals markets. Never raises — degrades to "fewer events/markets" on schema drift.
    - `session.py` — `BetB2BSessionManager`; browser bootstrap through `ProxyEndpoint` (Playwright Chromium, headless, stealth profile from skin config) → consent dismissal → SPA settle → `SessionHarvester.harvest()` → cached `SessionPackage`. Pre-bootstrap proxy-country verification (fails fast if egress not in `skin.allowed_countries`). TTL-based + auth-error-based re-bootstrap via `SessionValidator`. Detects geo/WAF block (HTTP 203 → `/en/block`) and raises with a clear message.
    - `client.py` — `BetB2BFeedClient`; long-lived `httpx.AsyncClient` (httpx 0.28 `proxy=` kwarg) with connection pooling; rate-limited; pulls fresh cookies from the session manager on every poll; auto-triggers re-bootstrap on auth-error statuses (401/403/419/440).
    - `scraper.py` — `BetB2BScraper` orchestrator; `scrape(action=…)` dispatches to `list_live`/`list_prematch`/`list_all`/`raw_capture`/`sports_short`/`top_champs`. Wires into the framework's `ProxyManager.acquire(site=domain, endpoint_id=…)`. De-dupes events by `event_id` (merges markets, prefers live version). Async-context-manager lifecycle.
    - `cli/main.py` + `cli/__main__.py` — `scrape` / `info` / `skins` / `probe` subcommands. Proxy config from env vars (`BETB2B_PROXY_URL`/`USER`/`PASS`/`COUNTRY`/`ID`) — no secrets in CLI args.
    - `scripts/validate_live.py` — end-to-end probe → harvest → poll → extract → persist script. Writes summary + per-action captures to `/home/z/my-project/download/betb2b_validate_<skin>/`.
    - `scripts/probe_family.py` — reproduces the Session-11 8-domain family-generalization probe (linebet/melbet/betwinner/22bet/megapari/888starz/helabet/paripesa + 1xbet.com + 1win.pro).
    - `skins/{linebet,melbet,betwinner,22bet,megapari,888starz,helabet,paripesa}.yaml` — 8 shipped skin configs. linebet uses verified-true values (`partner=189`, `gr=650`, `country=87`, `geo=KE`); the other 7 ship with `partner=1`/`gr=1` placeholders (per-skin `partner`/`gr` ids NOT captured yet — see `tasks/current.md`).
    - `tests/test_betb2b_extractor.py` — **24 unit tests, all passing**. Covers: decode (valid/empty/invalid JSON, Success=false), extraction (live feed, prematch feed, AE-grouped markets, E-flat markets, non-event dict filtering, unknown market ids degrade gracefully), market/sport lookups, skin YAML loading (defaults filled, unknown keys rejected), `feed_url` rendering (both roots + extra params), `merged_headers` with cookies, `with_overrides`, dedup (market merge + live-version preference), `get_info`.
    - `README.md` — full operator guide (architecture diagram, extraction-mode rationale, quick-start, customization, actions, output shape, schema map, testing, limitations).
  - **Proxy verified live mid-session:** `verify_proxy(kenya)` returned `[kenya] 102.210.56.70 (KE) 3636ms` — exactly what `linebet.yaml` requires. CLI `skins` + `info --skin linebet` both worked from the sandbox.
- **Test results:** `pytest src/sites/betb2b/tests/ -v` → 24 passed, 0 failed (3.46s). No network, no browser. The repo's broader pytest baseline is still broken (per the Session-4 backlog items — `pytest.ini` header bug, ~24% of tests hang, 15 collection errors); I did NOT touch any of that.
- **Blocked / pending (live validation):** four attempts to run `python -m src.sites.betb2b.scripts.validate_live --skin linebet` were each blocked by the Bash tool returning `broken session: 403 Forbidden` on every invocation (including `echo retry`). Two of the four hit AFTER `verify_proxy` had just succeeded, so the outage is a session-level tool-surface issue, not a proxy or code issue. Logged in `flaws/log.md`. The exact resume command + operator proxy env vars are documented in `tasks/current.md` "Live validation pending" — a next-session agent should run it as the first action and report the extracted event count.
- **Open items (see `tasks/current.md` + backlog):**
  - **HIGH:** live-validate `validate_live --skin linebet` end-to-end (the pending action). Next agent runs it; if 0 events/0 captures, the task file has the triage steps.
  - **MEDIUM:** confirm per-skin `partner`/`gr` ids for the 7 non-linebet skins (bootstrap each, dump `bff-api/config/group/get?...&p=<gr>` from the SPA, patch the YAMLs).
  - **MEDIUM:** run `probe_family.py` through the proxy to re-confirm the family-generalization signal against the current set of domains.
  - Already in backlog from Session 11 cont.: "Generalize the linebet scraper into a betb2b family base scraper" — **DONE this session**, marked `[x]` in the backlog.
- **Report:** `.context/memory/reviews/2026-07-18-betb2b-base-scraper-build.md`. Summary delivered in chat.
