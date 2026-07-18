# Backlog (append-only)

Open items for future sessions. Append at the bottom; never delete or
reorder. When an item is done, check it off and note the session/commit —
don't remove the line.

<!-- TEMPLATE — copy below the last entry:
---
- [ ] **<short title>** (added YYYY-MM-DD by <agent>) — <enough context that
      a fresh agent can act on this without any chat history. Severity if known.>
-->

---
- [x] **Install Python 3.12+ toolchain on Baos-Mac-mini** (added 2026-07-12 by Claude Code; done 2026-07-12, `bb0e636`) —
      Installed `uv` (user-space) → uv-managed CPython 3.12.13 → `.venv/` → `uv pip
      install --only-binary :all: -e ".[dev]"`. Verified commands in
      `.context/system/environments.md`. Still TODO: `playwright install` (browsers)
      and running the pytest/ruff/mypy baseline.
- [ ] **Migrate `datetime.utcnow()` (1081 uses) to tz-aware `datetime.now(timezone.utc)`** (added 2026-07-12 by Claude Code) —
      Deprecated in Python 3.12 (the project's floor). NOT a blind sed: `utcnow()`
      is naive, `now(timezone.utc)` is aware — changes `.isoformat()` output
      (`+00:00`) and can raise `TypeError` on naive/aware comparisons. Do it
      module-by-module with tests green. Medium. See F2 in 2026-07-12-review.md.
- [ ] **Audit 57 bare `except:` clauses for CancelledError swallowing** (added 2026-07-12 by Claude Code) —
      On 3.12 `CancelledError` is a `BaseException`; a bare `except:` catches it,
      contradicting the project's cancellation strategy. Narrow to `except Exception:`
      where intent is "swallow errors, not cancellation," esp. in async flows
      (e.g. `src/sites/github/flows/search_flow.py`). Needs tests. Medium.
      `grep -rn --include='*.py' -E 'except\s*:' src`. See F3 in review.
- [ ] **Audit fire-and-forget `asyncio.create_task(...)` calls** (added 2026-07-12 by Claude Code) —
      ~10+ tasks created without keeping a reference (e.g. `src/sites/base/site_scraper.py:84`,
      `src/sites/base/plugin_lifecycle.py:876,885`). Event loop holds only weak refs,
      so tasks can be GC'd mid-flight and exceptions lost. Store handles / await where
      completion matters. Low–Medium. See F4 in review.
- [ ] **Fix import-time crash: `analytics_engine` imports non-existent module** (added 2026-07-12 by Claude Code) —
      `src/telemetry/reporting/analytics_engine.py` does `import src.telemetry.report_generator`
      but no such module exists → `ModuleNotFoundError` on import. Find the real module
      (renamed/moved?) or restore it. High (breaks the telemetry reporting subsystem).
      Repro: `.venv/bin/python -c "import src.telemetry.reporting.analytics_engine"`.
- [ ] **Fix import-time crash: dataclass arg order in `route_visualization`** (added 2026-07-12 by Claude Code) —
      `src/navigation/route_visualization.py` raises `TypeError: non-default argument
      'route_id' follows default argument` at import — a field/param with no default is
      declared after one with a default. Reorder so non-default fields precede defaulted
      ones (or give `route_id` a default). High (breaks navigation viz import).
      Repro: `.venv/bin/python -c "import src.navigation.route_visualization"`.
- [ ] **Fix FastAPI route with invalid response model in `rate_limiting`** (added 2026-07-12 by Claude Code) —
      `src/selectors/adaptive/api/middleware/rate_limiting.py` fails to import under
      fastapi 0.139: a route's return annotation (`FailureService`) isn't a valid Pydantic
      response field. Add `response_model=None` to the decorator or fix the annotation.
      Medium; may be version-sensitive (surfaced with newly-installed fastapi).
      Repro: `.venv/bin/python -c "import src.selectors.adaptive.api.middleware.rate_limiting"`.
- [ ] **Test suite cannot run to completion on this machine — ~24% of tests hang** (added 2026-07-12 by Claude Code) —
      With a Python 3.12 venv + deps + playwright browsers installed, `pytest` collected
      **1864 tests but only reached ~67 before manual stop**: 16 hung for the full 60s
      timeout (blocked in lock/queue `wait()`/`acquire()` — deadlock-like async fixture
      teardown, not clean network waits), ~13 failed, ~54 passed. At ~60s/hang the full
      run would take hours. Root issues: (a) no per-test timeout configured in the project
      (had to `pip install pytest-timeout` ad hoc; not declared), (b) no network/browser
      skip markers, so live-I/O tests run by default and stall offline. Recommend: add
      `pytest-timeout` to dev deps + a default `--timeout`, mark live/browser tests with
      `@pytest.mark.integration`/`network` and deselect by default, and fix the fixture
      teardown deadlocks. High (blocks any real baseline). Repro:
      `.venv/bin/python -m pytest --no-cov --continue-on-collection-errors --timeout=60 --timeout-method=signal -q`.
- [ ] **`pytest.ini` config is silently ignored (wrong section header)** (added 2026-07-12 by Claude Code) —
      `pytest.ini` uses `[tool:pytest]` (the setup.cfg-style header) instead of `[pytest]`,
      so pytest does not read it — markers, `addopts` (incl. `--cov=src` and
      `--strict-markers`), `testpaths`, `asyncio_mode=auto`, and `filterwarnings` are all
      dropped. Evidence: declared marks (`unit`, `integration`) warn as "unknown," and
      coverage doesn't run despite the addopts. Fix: rename the section to `[pytest]` (or
      move config into pyproject's `[tool.pytest.ini_options]`, which also exists — pick one
      source). NOTE: fixing this activates `--strict-markers`, which will then ERROR on the
      undeclared `quality_control` marker (10 tests) until it's registered. Medium.
- [ ] **15 test files fail at collection** (added 2026-07-12 by Claude Code) —
      `pytest --collect-only` reports 15 collection errors. Known causes: FastAPI
      response-model (test_audit_api, test_audit_export_formats, test_audit_query_api,
      test_feature_flag_api, test_site_api_endpoints — same root as rate_limiting item);
      navigation dataclass TypeError (test_navigation_service/_performance/_resilience —
      same root as route_visualization item); `NameError: name 'time'...` in
      test_component_integration (missing `import time`); `TypeError: StealthSettings...`
      in test_resource_monitoring; plus browser_lifecycle_test, test_template_framework,
      test_plugin_integration, test_tab_switching_integration, test_wikipedia_yaml_selectors
      (errors not captured — rerun collect to see). Fix underlying imports/signatures. High.
      *(Progress 2026-07-12 session 4: test_template_framework collection fixed — `b237089`.
      14 files remain.)*
- [ ] **Align template test suites with the implemented interface API** (added 2026-07-12 by Claude Code, session 4) —
      ~25 unit failures in `tests/sites/template/` + most of
      `tests/end_to_end/test_template_framework.py` expect APIs that
      `src/sites/base/template/interfaces.py` never declared: `health_check`,
      `get_performance_metrics`, positional `scrape(action)`, `registry.initialize()`,
      `loader.load_selectors()`/`get_selector()`, attribute-style validation results,
      and module-level `psutil` patching (psutil is imported locally). The
      implementations match the interface docstrings and the real GitHub consumer, so
      rewrite the tests against `interfaces.py` as the contract (or extend the interface
      deliberately — owner call). Medium. See finding 10 in 2026-07-12-review-2.md.
- [ ] **Author the 6 missing .j2 scaffolding templates** (added 2026-07-12 by Claude Code, session 4) —
      `development.py` `default_structure` promises 12 generated files but only 6 `.j2`
      templates exist in `src/sites/base/template/templates/`; missing:
      integration_bridge, selector_loader, flow_file, extraction_rules,
      extraction_models, test templates — those files are scaffolded empty with a
      warning. Medium. See finding 11 in 2026-07-12-review-2.md.
- [ ] **ADR: pick one site-scraper hierarchy** (added 2026-07-12 by Claude Code, session 4) —
      Two parallel "add a new site" systems exist: copy `src/sites/_template/`
      (extends ModularSiteScraper; wikipedia/flashscore hierarchy) vs `template create`
      CLI (generates BaseSiteTemplate subclasses; only github, which multiple-inherits
      from BOTH). Contradicts the one-framework philosophy; new contributors can't tell
      which path is canonical. Needs an owner decision + convergence of scaffold,
      generator, and docs. Architectural — do not "fix" without approval. See finding 9
      in 2026-07-12-review-2.md.
- [ ] **Triage 46 GitHub Dependabot alerts** (added 2026-07-12 by Claude Code, session 4) —
      Every push prints: 1 critical, 17 high, 23 moderate, 5 low at
      https://github.com/TisoneK/scrapamoja/security/dependabot. Review and bump/pin
      affected dependencies. High (security).
- [ ] **Template CLI writes template_cli.log to the process cwd** (added 2026-07-12 by Claude Code, session 4) —
      `TemplateFrameworkCLI.setup_logging()` attaches a
      `FileHandler('template_cli.log')` unconditionally, so any CLI invocation litters
      the caller's cwd (untracked file in the repo root when run from there). Route it
      to the project's log/data dir or make it opt-in. Low.

- [ ] **Fix import-time `os.makedirs` in `src/core/snapshot/__init__.py`** (added 2026-07-17 by Super Z, session 8) —
      `_initialize_module()` (lines 246–260) runs at MODULE IMPORT time and calls
      `os.makedirs("data/snapshots")` + `os.makedirs("config")` with RELATIVE paths.
      This crashed the first Railway deploy: the container runs as non-root `appuser`
      and `/app` was root-owned, so every gunicorn worker died with `PermissionError`
      on startup and the `/health` healthcheck timed out. Dockerfile-only fix is in
      place (pre-create the dirs + `chown -R appuser:appuser /app`), but the root
      cause is the import-time side effect. Fix options (pick one):
        (a) Make `_initialize_module()` lazy — call it from `SnapshotManager.__init__`
            or a `get_snapshot_manager()` first-call hook, not at import time.
        (b) Use absolute paths under a single writable root (e.g. `data/snapshots/`
            resolved via `Path(__file__).parents[N] / "data" / "snapshots"`).
        (c) Wrap the makedirs in try/except PermissionError + log a warning, so a
            read-only cwd doesn't crash the import (weakest option — hides the
            real misconfiguration).
      Recommend (a) — import-time filesystem writes are a code smell regardless of
      deployment target. Also sweep `src/` for other module-level `os.makedirs` /
      `Path(...).mkdir` calls (grep found 13 total, but only this one runs at import
      time — the rest are inside functions). Medium. See `inefficiencies/log.md`
      2026-07-17 entry + ADR-1 in `plans/decisions.md`.

---
- [ ] **Linebet: capture a real HAR from a residential IP and discover the actual sports/odds endpoints** (added 2026-07-17 by Super Z, Session 9 continuation) —
      The Linebet scraper is built and tested, but the actual sportsbook-data
      endpoints (`/bff-api/sports/...` or whatever they are) have NOT been
      verified against real traffic because the sandbox IP is WAF-blocked
      (HTTP 203 → /en/block) before the SPA can fire them. Probed 3 browser
      profiles + 3 free US proxies + 5 alt entry points — all blocked at the
      nginx edge, so this is datacenter-IP fingerprinting, NOT geo-blocking.
      Action needed: run `python -m src.sites.linebet.scripts.har_export
      --output my_session.har --live` from a RESIDENTIAL IP (or a paid
      residential-proxy service like Bright Data / Soax), then commit the HAR
      to `src/sites/linebet/snapshots/raw/` and replay it with `python -m
      src.sites.linebet.scripts.har_replay <har> <out.json> --normalize
      <snapshot.json>`. Once we see the real sports-data endpoint URLs +
      JSON shape, update `src/sites/linebet/extraction/rules.py::_classify_endpoint`
      + the `_extract_prematch` / `_extract_live` / `_extract_market_detail`
      methods to match the real schema. The extractor is already defensive
      (multi-key `_get_first` lookups + shape heuristics), so it will likely
      "just work" once the right endpoints are captured — but the
      `_SPORT_ALIASES` map and `_MARKET_NAME_PATTERNS` regex may need
      tightening against real data. HIGH — blocks real-world use.
- [ ] **Linebet: implement the httpx-based replay mode** (added 2026-07-17 by Super Z, Session 9 continuation) —
      `ENABLE_REPLAY_MODE` is plumbed in `config.py` but the actual httpx
      re-issue path (take a captured request, forward cookies + the 14
      `REPLAY_FORWARD_HEADERS` we observed in real traffic, re-issue via
      httpx, return the response) is not implemented. Would let us poll
      Linebet sub-second without relaunching the browser each time. Build
      it once the residential-IP HAR above gives us a known-good request
      to replay. MEDIUM.
- [ ] **Linebet: register `LinebetScraper` with the global `ScraperRegistry` at app startup** (added 2026-07-17 by Super Z, Session 9 continuation) —
      `src/sites/linebet/__init__.py::register(registry)` exists and works,
      but nothing calls it. The CLI (`python -m src.main linebet ...`) is
      registered in `src/main.py::SITE_CLIS`, but the central
      `ScraperRegistry` instance (used by the FastAPI control plane + the
      validation suite) does NOT have Linebet registered. Wire it up
      wherever the other sites (wikipedia, github, flashscore) get
      registered. LOW — the CLI works without it, but registry-driven
      discovery won't find Linebet until this is done.

---
- [ ] **Build site scraping-mode classifier** (added 2026-07-17 by Super Z, Session 10) —
      THE actual deliverable. Linebet is just the validation case, not the goal.
      Build `src/extraction/classifier/` — a system that watches a site behave
      (either live via Playwright or via a HAR replay) and classifies which
      `ExtractionMode` (`raw` / `intercepted` / `hybrid` / `playwright`) fits,
      then emits a recommended `SiteConfig` (with `API_URL_PATTERNS`,
      `REPLAY_FORWARD_HEADERS`, etc.). Heuristics to start with: (a) fraction
      of page data fetched via XHR vs rendered in initial HTML; (b) presence
      of WAF signals (HTTP 203 / Cloudflare challenge pages / cf-ray headers);
      (c) auth-cookie behaviour (does the site set long-lived cookies that
      gate API access? → suggests `intercepted`+session-bootstrap); (d) API
      URL patterns (under `/api/`, `/bff-api/`, `/graphql` → suggests
      `intercepted` or `hybrid`); (e) DOM data density (sparse HTML +
      JS-rendered → not `playwright`/`raw`). Validate by feeding it a real
      Linebet HAR (once captured from a residential IP — see the existing
      "residential-IP HAR" backlog item) and asserting the classifier outputs
      `ExtractionMode.HYBRID` with the right patterns. HIGH — this is what
      the whole linebet exercise was building toward.

---
- [ ] **Migrate stealth + navigation onto the canonical `src/network/proxy` ProxyManager** (added 2026-07-17 by Claude Opus 4.8, Session 11) —
      Session 11 built the canonical proxy layer in `src/network/proxy/`
      (ProxyEndpoint + ProxyManager + providers + verify + config) and wired the
      browser-launch / HAR / httpx chokepoints to it, but INTENTIONALLY left the
      two pre-existing proxy systems in place to avoid a risky rewrite:
      `src/stealth/proxy_manager.py` (residential rotation, wired into
      `src/stealth/coordinator.py`) and `src/navigation/proxy_manager.py`.
      There are also two duplicate `ProxySettings` classes
      (`src/browser/models/proxy.py` and `src/browser/models/configuration.py`)
      plus the flat `config.proxy_server/username/password` fields the browser
      session manager falls back to. Follow-up: point `stealth/coordinator` and
      `navigation` at the canonical ProxyManager (adapters already exist:
      `ProxyEndpoint.from_stealth_session` / `.from_navigation_config` /
      `.from_browser_proxysettings`), then deprecate the duplicate ProxySettings
      classes and the flat fields. Re-validate the stealth pipeline's tests
      (`tests/stealth/test_proxy_manager.py`). MEDIUM — architectural; do
      deliberately, one caller at a time, with tests green.
- [x] **Capture linebet HAR through the Kenyan ngrok proxy (Stage 4)** (added 2026-07-17 by Claude Opus 4.8, Session 11; DONE 2026-07-17 Session 11 cont., commit `9878dcf` — captured via `bore` tunnel not ngrok; found the odds feed is SW-mediated/invisible, see RECON.md + the two new follow-ups below) —
      The proxy abstraction is done; the remaining step is the actual capture,
      blocked on the user standing up a `gost` HTTP proxy on their Kenyan Windows
      box exposed via `ngrok tcp`. When they send host:port + basic-auth
      user/pass: `build_proxy_manager({...kenya endpoint + *linebet.com routing})`,
      `verify_proxy` (assert countryCode KE), then `HarExporter(url=linebet,
      proxy=kenya)` → 200 not 203 → HAR → `HarReplayer` + normalize → commit the
      normalized snapshot under `src/sites/linebet/snapshots/`. This finally
      yields the real sports/odds endpoints + headers and feeds the classifier.
      See `tasks/current.md` for the exact resume steps. HIGH.

---
- [ ] **Find linebet's live-odds endpoint (SW-mediated transport)** (added 2026-07-17 by Claude Opus 4.8, Session 11 cont.) —
      Stage-4 capture proved the live odds render in the DOM but the feed is
      INVISIBLE to Playwright page/context interception, the HAR, and page
      WebSocket/SSE events — it rides linebet's service-worker transport
      (`ivpn-sw.js` header injection from IndexedDB `vpn/headers`; `domain-sw.js`
      mirror-domain failover). To find the actual odds endpoint: (a) attach a CDP
      session with `Target.setAutoAttach {autoAttach:true, flatten:true}` to the
      service-worker target and enable the `Network` domain there (page-level
      Playwright can't see SW traffic), OR (b) after the SPA initializes, read the
      IndexedDB `vpn/headers` store + locate the sportsbook fetch the app issues
      (the SPA `entry-*.js` only revealed casino `service-api` endpoints; the
      sportsbook chunk loads separately). Requires the Kenya proxy live again
      (bore/gost). HIGH — this is the endpoint a direct-API linebet scraper needs.
- [ ] **Build a linebet live-odds DOM extractor** (added 2026-07-17 by Claude Opus 4.8, Session 11 cont.) —
      Since the odds feed is SW-hidden, the reliable extraction path today is the
      rendered DOM (odds render fully — verified). Build a Playwright DOM extractor
      over the live betting grid (champ rows / `c-events` items: teams, scores,
      market odds). This is the pragmatic linebet scraper until/unless the direct
      odds endpoint (item above) is reverse-engineered. Feeds the scraping-mode
      classifier as evidence linebet = hybrid/playwright, not clean intercept.
      MEDIUM.

---
- [ ] **Reverse-engineer linebet `/LineFeed/` odds via IndexedDB header replay** (added 2026-07-17 by Claude Opus 4.8, Session 11 cont. — AUGMENTS the two "live-odds endpoint" + "DOM extractor" items above with concrete operator intel) —
      Combines this session's SW-transport finding with the operator's prior
      (abandoned) linebet attempt. Known facts:
        * The odds data endpoint is **`/LineFeed/...`** (1xbet/melbet-family).
          Response is **heavily compressed**; decompressed it's JSON with **terse
          single-letter keys** (`T`,`E`,`C`,`G`,`O1`,`O2`,…) — re-derive the exact
          key map from a live capture (the linebet `extraction/models.py`
          Event/Market/Selection dataclasses are the target shape).
        * The request needs headers a plain scraper never has: an **auth token
          WITH an expiry**, `x-project-id`/`x-dt` (650), and a **referer-like
          header carrying the URL of the previous page** (pre-click navigation
          context). These are injected by the `ivpn-sw.js` service worker from
          IndexedDB **`vpn`→`headers`** — that's why they're invisible to
          interception and to the page JS. See `src/sites/linebet/RECON.md`
          "Prior operator investigation" + ADR-2.
      Concrete plan (needs the Kenya proxy live again — gost + `bore` tunnel):
        1. Load linebet live, let the SPA init, then dump IndexedDB `vpn/headers`
           (via `page.evaluate` opening the DB, or CDP `IndexedDB.requestData`) →
           get the token + expiry + referer header + x-dt/x-project-id.
        2. Capture a real `LineFeed` request: CDP `Target.setAutoAttach
           {autoAttach:true,flatten:true}` on the **service-worker** target +
           enable its `Network` domain (page-level Playwright can't see SW
           traffic), OR find the `LineFeed` URL+params in the sportsbook JS chunk
           (separate from the casino `entry-*.js`).
        3. Replay `LineFeed` with the IndexedDB headers → decompress
           (gzip/deflate/brotli; possibly a custom wrapper) → parse terse JSON →
           map keys to Event/Market/Selection.
        4. Handle **token expiry**: re-harvest from IndexedDB (or re-bootstrap the
           browser) on a timer — this is the `sw_replay`/`hybrid` concern per ADR-2.
      DOM extraction over the live grid (`c-events`/champ rows) remains the
      works-today fallback. HIGH — this is the linebet scraper's core unblock.

---
- [x] **Reverse-engineer linebet `/LineFeed/` odds via IndexedDB header replay** — **SUPERSEDED / SOLVED 2026-07-18** (Session 11 cont.): the odds feed does NOT need IndexedDB/x-hd headers. It's `GET /service-api/LiveFeed/Get1x2_VZip` (+ siblings), a plain XHR that replays from httpx with base betting headers + cookies + an allowed-country proxy (proven: 200/Success=true, and identical without x-hd). Full details in `src/sites/linebet/RECON.md` "SOLVED" + ADR-3. Replaces the IndexedDB-replay plan below.
- [ ] **Build the linebet `hybrid` scraper (cookie-harvest → httpx LiveFeed polling)** (added 2026-07-18 by Claude Opus 4.8, Session 11 cont.) —
      Everything needed is now known (RECON.md "SOLVED" + ADR-3). Implement:
        1. Browser bootstrap through an allowed-country proxy (`ProxyManager` +
           `SessionHarvester`/`HybridConfig` — already in the framework) to harvest
           the ~21 session cookies.
        2. `httpx` poll loop (through the same proxy) over the feeds:
           `/service-api/LiveFeed/Get1x2_VZip` (live) and `/service-api/main-line-feed/v1/*`
           (prematch), with base betting headers
           (`is-srv:false`, `x-app-n:__BETTING_APP__`, `x-svc-source:__BETTING_APP__`,
           `x-requested-with:XMLHttpRequest`) + cookies. Query params: `gr=650`,
           `country=87`, `partner=189`, `lng=en`, `count=N`.
        3. Map the terse `Value[]` JSON to the existing `extraction/models.py`
           Event/Market/Selection (I/ZP=id, O1/O2=teams, SN=sport, L=league, S=start,
           SC.FS=score; E[]/AE[].ME[] markets: T=type, G=group, C=odds, P=line, B=blocked).
        4. Build the `T`(market-type)/`G`(group) id → market-name lookup (1=1x2, 2=handicap,
           17=totals, …; 1xbet-family tables) and confirm cookie TTL / re-bootstrap cadence.
      Needs the Kenya proxy live (gost + bore). HIGH — this ships the scraper the
      whole exercise was for. Extraction mode = `hybrid` per ADR-3.

---
- [ ] **Generalize the linebet scraper into a `betb2b` family base scraper** (added 2026-07-18 by Claude Opus 4.8, Session 11 cont.) —
      VERIFIED 2026-07-18: linebet is one skin of the BetB2B/1xbet platform, and the
      recon generalizes across the family. Probing `/service-api/LineFeed/Get1x2_VZip`
      through the Kenya proxy returned the IDENTICAL `feed/NotAcceptableException` 406
      envelope (same feed microservice) on: melbet, betwinner, 22bet, megapari,
      888starz, helabet, paripesa, linebet. So the endpoints/headers/schema/hybrid
      approach are shared. Build a `src/sites/betb2b/` base scraper + thin per-skin
      `SiteConfig`s. Per-skin params that differ: `domain`, `partner`/`ref`
      (linebet=189), `gr` project id (linebet=650), geo `country`, per-skin cookie
      harvest. Shared: LiveFeed(in-play)/LineFeed(prematch) roots, endpoint names,
      base betting headers, terse-key Value[] schema, hybrid cookie-harvest→httpx poll.
      EXCEPTIONS: 1xbet.com is Cloudflare-fronted (403 challenge) — needs anti-CF
      handling; 1win.pro is a DIFFERENT platform (200 HTML, no service-api) — exclude.
      See `src/sites/linebet/RECON.md` "Generalizes to the 1xbet/BetB2B family". This
      supersedes the linebet-only build item into a family-wide one. HIGH.
