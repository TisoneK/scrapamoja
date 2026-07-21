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
- [ ] **Fix import-time crash: `analytics_engine` missing numpy/scipy** (added 2026-07-12 by Claude Code; **corrected 2026-07-20**: original diagnosis said it imports non-existent `report_generator`, but the actual error is `import numpy as np` / `from scipy import stats` failing because these deps weren't installed at bootstrap time) —
      `src/telemetry/reporting/analytics_engine.py` imports `numpy` and `scipy` at module level
      (line 18-19). Both are declared in `pyproject.toml` under `[project.dependencies]` but
      were not installed when the venv was created. Just run `pip install numpy scipy` to fix.
      High (breaks the telemetry reporting subsystem).
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
- [ ] **Fix DOM extraction to extract markets/odds/scores from BetB2B Vue grid** (added 2026-07-18 by GitHub Copilot) —
      Current DOM extraction finds events (championships + team names) but `markets=0` across
      all 8 skins. The Vue.js rendered grid likely uses non-standard element structures or
      the selectors in `dom_selectors` don't match the actual rendered cells. All 3/3 working
      skins hit this (linebet, helabet, megapari). Medium-High priority — without markets the
      scraper produces event stubs with no odds.
- [x] **Investigate paripesa 0 basketball events** (added 2026-07-18 by GitHub Copilot; **resolved 2026-07-19**) —
      Root cause found: skin domain was `paripesa.bet` which redirects to a bonus landing page
      (`bonus.rdrctpar24.lol`), not the actual BetB2B SPA. Fixed by changing domain to
      `paripesa.cool` in skin YAML. H2H endpoint now works (19 games, 12 teams, HTTP 200).
      The 0 DOM events from the prior session was likely the same domain issue. See
      commit `7d676e8`.
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
- [x] **`pytest.ini` config is silently ignored (wrong section header)** (added 2026-07-12 by Claude Code; fixed 2026-07-20, `d8f4a55`) —
      `pytest.ini` used `[tool:pytest]` (the setup.cfg-style header) instead of `[pytest]`,
      so pytest did not read it — markers, `addopts`, `testpaths`, `asyncio_mode`,
      `filterwarnings` all silently dropped. Fixed by renaming to `[pytest]`.
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
- [x] **Generalize the linebet scraper into a `betb2b` family base scraper** — DONE 2026-07-18 Session 12 (`src/sites/betb2b/` shipped: config + markets + sports + extraction + session + httpx client + scraper + CLI + scripts + 8 skin YAMLs + 24 unit tests + README; live validation pending — see `tasks/current.md`). Original entry: (added 2026-07-18 by Claude Opus 4.8, Session 11 cont.) —
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

---
- [ ] **Lift the odds-enrichment cap + confirm markets across all 8 skins** (added 2026-07-18 by Claude Opus 4.8, Session 18) —
      `GetGameZip` odds enrichment works (commit `3aad7c6`): linebet basketball
      prematch → Orlando Magic v Boston Celtics = 39 markets / 238 selections,
      verified live. It is capped by `skin.max_odds_fetch` (default 20) so a big
      list doesn't fan out to hundreds of per-match requests. Follow-ups:
      (1) decide the production cap / add pagination or concurrency (currently
      sequential + rate-limited) so a full card (100+ events) is fetchable without
      a huge wall-clock; consider `asyncio.gather` with a semaphore honouring the
      client rate limit. (2) Confirm markets>0 on the other 7 skins (helabet,
      megapari, melbet, betwinner, paripesa, 888starz, 22bet) — they share the
      same `GetGameZip` endpoint + schema so it should "just work," but the
      per-skin `partner`/`gr` placeholders may need the real values (see the
      existing per-skin partner/gr backlog item). Run `validate_live --skin <x>`
      through the proxy for each. Medium.
      **UPDATE 2026-07-21 (Session 25):** markets>0 confirmed live on 3 skins
      via `cli scrape ... --action list_live`: linebet (133 markets/10 events),
      **melbet** (89, real partner/gr 61/6), **helabet** (114 — and enrichment
      worked DESPITE its placeholder partner/gr=1, so GetGameZip does NOT
      strictly require exact per-skin partner/gr). All three returned the SAME
      event ids (shared BetB2B backend). Remaining to confirm: 22bet,
      betwinner, paripesa (reachable via proxy — see cross-skin item);
      megapari (proxy timeout) + 888starz (203 /en/block) still unreachable.
      The `max_odds_fetch` cap + concurrency follow-up (1) is still open.

---
- [ ] **Run + confirm betb2b live e2e — all endpoints collect data** (added 2026-07-20 by Claude Code, Session 23) —
      Operator-gated. Needs the Kenya proxy tunnel UP (bore.pub or gost/bore
      on the operator's Windows box) + env: `BETB2B_PROXY_URL`,
      `BETB2B_PROXY_USER`, `BETB2B_PROXY_PASS`, `BETB2B_PROXY_COUNTRY=KE`.
      Then per skin: `python -m src.sites.betb2b.scripts.validate_live --skin
      <skin> --sport basketball --count 50 --compress`. Confirm event_count>0
      for BOTH `list_live` and `list_prematch` (the 2026-07-18 run got 0 from
      both despite a verified-KE session + 1 capture each — feed empty at
      capture time vs an extraction gap is undiagnosed). Also exercise
      `sports_short` + `top_champs` actions. Ties into the existing "lift
      odds-fetch cap + confirm markets across 8 skins" item. JSON output now
      supports `--compress` (gzip) + `betb2b view <file>` to read back — see
      `src/sites/betb2b/storage.py` + README "Saving & viewing output". HIGH.
      **UPDATE 2026-07-21 (Session 25):** `list_live` confirmed collecting data
      end-to-end on linebet + melbet + helabet (10 events each, clean teams +
      scores + GetGameZip markets). The 2026-07-18 "0 events" was the
      fixed-settle render extracting before the grid rendered (fixed `d173c6a`
      grid-wait) — NOT a feed/extraction gap. Still open: `list_prematch`
      integrated confirmation + `sports_short`/`top_champs` actions (the API
      feeds those hit are still 406 per ADR-4; prematch DOM fallback validated
      against captured HTML but not yet via the integrated CLI this session).

---
- [x] **Rework live DOM selectors for in-play state (linebet)** (added 2026-07-21 by Super Z, Session 25 setup; **DONE 2026-07-21 Session 25**, commits `58f9a46`+`26b08d5`) —
      Root cause differed from the handoff: on a fresh live capture (via Kenya
      proxy) the current `dashboard-champ`/`dashboard-game-block__team`
      selectors already extract 10 clean events with numeric IDs — the Session
      24 garble was a loading-state snapshot, not a wrong subtree. The real
      gaps were (a) **scores** — live totals live in
      `.ui-game-scores__item--total .ui-game-scores__num` (two adjacent spans),
      which the old score selectors missed; fixed by adding that selector +
      teaching `_score_pair` to parse the "46 57" whitespace pair; and (b) the
      garbled-name guard, hardened (reject `0000` anywhere + duplication
      detector). Verified: 10 live events, 100% clean teams + IDs + scores.
      Original entry below.
- [ ] ~~**Rework live DOM selectors for in-play state (linebet)**~~ (superseded by the checked item above) —
      Session 24 confirmed prematch DOM extraction works (28 events, 100%
      teams/competition/market, 50% H2H), but live DOM extraction is broken:
      70 events returned with garbled team names (duplicate/truncated
      `"Ajax  Olympiacus Piraeus  0000-Ajax  Olympiacus Piraeus  0000"`),
      0 markets, 0 scores. The in-play page renders through a different Vue
      subtree than the prematch `dashboard-champ` grid; the selectors in
      `src/sites/betb2b/sports/base.py::DOMSelectors` don't match.
      Concrete plan:
        1. Capture `/en/live/basketball` HTML via `tools/analyze_match_html.py`
           or a fresh probe; enumerate actual live class names for game row,
           team names, scores, odds cells.
        2. Extend `DOMSelectors` with `live_*` family OR a separate
           `LiveDOMSelectors`; branch `_build_page_script()` in
           `extraction/dom.py` on `is_live`.
        3. Tighten `_is_plausible_team_name()` (dom.py:67) — the 80-char cap
           let the duplicated string through; add a duplication detector.
        4. Add a unit test under `src/sites/betb2b/tests/` with a captured
           live HTML fixture.
      HIGH — operator-blocker; without live coverage the scraper is
      prematch-only. See `tasks/current.md` Session 25 Phase 1.

---
- [x] **Wire `GetGameZip` market enrichment into DOM-extracted events** (added 2026-07-21 by Super Z, Session 25 setup; **DONE 2026-07-21 Session 25**, commit `99be8ac`) —
      Correction to the handoff: the enrichment was NOT missing — it already
      existed as `scraper._enrich_dom_events_with_odds` (wired into `scrape()`,
      default-on via `skin.enrich_dom_with_odds`). It fetched 0 in Session 24
      because of a skip-condition bug: the guard `if e.markets: skip` skipped
      every DOM event, since the DOM extractor always attaches a shallow
      1-market stub. Fixed to skip only already-deep events (`len(markets) >
      1`). Verified against real captures: 1 stub → 10 markets (prematch);
      live IDs → 40/9/7 markets via `LiveFeed/GetGameZip`. (Did not add a
      parallel `features["markets_enrich"]` flag — kept the existing
      `enrich_dom_with_odds` getattr-default pattern.) Original entry below.
- [ ] ~~**Wire `GetGameZip` market enrichment into DOM-extracted events**~~ (superseded by the checked item above) —
      Session 24 found DOM extraction yields only 1 market per event (the
      main "To Win Match" / "1x2" — that's all the grid renders).
      `GetGameZip` enrichment is NOT running for DOM events (0 fetched in
      Session 24). `Get1x2_VZip` still 406 per ADR-4. But `GetGameZip`
      reliably returns ~24 KB with the full `E[]/AE[]` market tree
      (handicaps, totals, BTTS, etc.) — confirmed Session 19/20. The
      numeric event id is already captured by `dom.py:189-195` from the
      match link `href`.
      Concrete plan:
        1. Mirror `_enrich_with_h2h()` (Session 21) — add
           `_enrich_with_markets()` in `scraper.py`: iterate DOM events,
           poll `/service-api/{Line,Live}Feed/GetGameZip?id=<eventId>` via
           direct `httpx` with harvested cookies, parse via
           `rules._extract_markets()`, replace shallow DOM market with full
           tree.
        2. Cap & rate-limit via `skin.max_odds_fetch` (default 20) +
           bounded `asyncio.gather` with semaphore.
        3. 406 / non-2xx → silent fallback to DOM market + warning log.
           Do NOT chase auth-header contract (ADR-4).
        4. Add `"markets_enrich": True` to default `features` dict in
           `config.py`.
        5. Unit test with captured `GetGameZip` fixture; assert ≥ 5 markets
           per basketball prematch event.
      HIGH — operator-blocker; without market depth the scraper cannot
      feed the downstream odds-comparison use case. See
      `tasks/current.md` Session 25 Phase 2.

---
- [x] **Confirm integrated live `scrape` end-to-end through the proxy** (added 2026-07-21 by Claude Code, Session 25; **DONE 2026-07-21** same session — operator restarted the tunnel on port 52147) —
      **Confirmed green:** `python -m src.sites.betb2b.cli scrape --skin linebet
      --sport basketball --action list_live` through the Kenya proxy →
      **10 live events, 10/10 clean team names (0 rejected), 10/10 with live
      scores, 8/10 with GetGameZip markets (133 total; Phoenix=40, Botafogo=39),
      76s.** Logs confirm all fixes composing: `proxy OK (attempt 1)`,
      `raw_rows=10` (grid-wait), `10 GetGameZip fetched` (enrichment). The
      tunnel flakiness that blocked the first two attempts was also hardened —
      proxy verification now retries transient errors (`7f59edc`). Two events
      returned 0 markets (women's Chinese basketball with no open live markets)
      — best-effort GetGameZip miss, not a defect. Original entry:
- [ ] ~~**Confirm integrated live `scrape` end-to-end through the proxy**~~ (superseded — done above) —
      Session 25 validated every stage of the live pipeline independently
      against real data (DOM extraction, score parse, GetGameZip enrichment)
      and fixed a fragile fixed-settle render (`d173c6a` — now waits for the
      game grid). But the *integrated* `scrape(list_live)` run through the
      Kenya bore proxy was NOT confirmed green — the tunnel (`bore.pub:50670`)
      dropped (HTTP 000) before the grid-wait fix could be re-run. When the
      proxy is up: `export BETB2B_PROXY_URL=http://bore.pub:<port>
      BETB2B_PROXY_USER=TisoneK BETB2B_PROXY_PASS=<pass> BETB2B_PROXY_COUNTRY=KE
      BETB2B_PROXY_ID=kenya` then `python -m src.sites.betb2b.cli scrape --skin
      linebet --sport basketball --action list_live --count 30 -o out.json`.
      Expect ≥1 live event with clean teams + score + ≥1 market. NOTE the
      entry point is `python -m src.sites.betb2b.cli` (NOT `.cli.main` — that
      has no `__main__` guard and silently no-ops). MED.
- [ ] **Map remaining GetGameZip market-group ids to names** (added 2026-07-21 by Claude Code, Session 25) —
      A few markets from `GetGameZip` extract with placeholder names like
      `G=14`, `G=91`, `G=92` (unmapped group id → display name) — odds/lines
      are still captured correctly, only the market label is generic. Extend
      the `G`(group)→name lookup (basketball) in
      `src/sites/betb2b/markets.py` / sport overrides. Cosmetic. LOW.

---
- [ ] **Fix 22bet skin: KE-redirect domain drops the `/en` prefix (0 live events)** (added 2026-07-21 by Claude Code, Session 25) —
      Cross-skin validation (Session 25) got 0 events from 22bet
      (`raw_rows=0`) while linebet/melbet/helabet/betwinner/paripesa all
      returned 10. Root cause: `22bet.com/en/live/basketball` redirects (via
      the Kenya proxy) to **`22bet.co.ke/live/basketball`** — the KE domain
      uses NO `/en` locale prefix, so the scraper's bootstrap path
      (`/en/live/basketball`) lands on a route that never renders the
      `.dashboard-champ__game` grid. Fix: in `src/sites/betb2b/skins/22bet.yaml`
      set `domain: 22bet.co.ke` and strip `/en` from `bootstrap_paths`
      (mirrors the Session 19 paripesa `paripesa.bet`→`paripesa.cool` domain
      fix, commit `7d676e8`). Then re-run `python -m src.sites.betb2b.cli
      scrape --skin 22bet --sport basketball --action list_live` through the
      proxy. Also re-check helabet/betwinner: they redirect too (helabetke.com,
      betwinner.ke) but preserved the path so they worked — leaving their
      `domain` as `.com` means feed/GetGameZip URLs still target `.com`
      (worked in this session, but the KE domain would be more correct). LOW-MED.

---
- [ ] **Unify + smoke-test the per-site CLI entry points** (added 2026-07-21 by Claude Code, Session 25) —
      Session 25 hit THREE entry-point defects of the same class: (1) betb2b
      `python -m src.sites.betb2b.cli.main` silently no-ops (no `__main__`
      guard — real path is `-m src.sites.betb2b.cli`); (2) the Session-25
      handoff recommended that wrong betb2b command; (3) flashscore
      `python -m src.sites.flashscore.cli` crashed passing raw argv to a
      Namespace-expecting `run()` (fixed `6b5ae82`). Root pattern: each site's
      `cli/__main__.py` is hand-written differently and `run()` signatures
      diverge, and only the `src.main <site>` dispatcher is reliably wired.
      Actions: (a) add a parametrized smoke test — `subprocess python -m
      src.main <site> --help` (and the package `-m <site>.cli --help`) asserting
      exit 0 — over all sites (flashscore/wikipedia/direct/linebet + betb2b);
      (b) **register betb2b in `src/main.py::SITE_CLIS`** — DONE 2026-07-21
      (Session 25, `011969d`): added a `BetB2BMainCLI` adapter (create_parser +
      run(args, interrupt_handler=, shutdown_coordinator=)) and split
      `BetB2BCLI.run` into parse + `run_args`. `python -m src.main betb2b scrape
      --skin linebet --sport basketball --action list_prematch` verified live
      (10 events, 86 markets, 67s, clean graceful-shutdown). Standalone `-m
      src.sites.betb2b.cli` still works. Remaining: (a) cross-site --help smoke
      test; (c) standardize every `cli/__main__.py`;
      (c) consider standardizing every `cli/__main__.py` on create_parser →
      parse_args → run(args). MED — devex + prevents silent breakage.

---
- [ ] **Grow the betb2b odds store: dedup, retention, flashscore, Postgres** (added 2026-07-21 by Claude Code, Session 25) —
      `src/sites/betb2b/store.py` (SQLite, opt-in `--db`) shipped Session 25
      (`961f569`, ADR-6). Follow-ups: (1) **odds dedup** — DONE 2026-07-21 (`9b72f0e`): change-only
      inserts for odds_snapshots/event_states/period_scores — an unchanged poll
      stores 0 rows, only movement is recorded (verified: identical poll +0,
      one price move +1). REMAINING follow-ups:
      (2) **retention/rollup** — a policy to prune or downsample old snapshots.
      (3) **flashscore + other sites** — map their models onto the same schema
      (or lift store.py into a shared `src/storage/odds/`) so one store holds
      all sites. (4) **Postgres backend** — the schema is already
      TEXT/INTEGER/REAL + ISO timestamps (portable); add a connection
      abstraction when file-SQLite stops scaling. (5) a small `betb2b odds`
      CLI subcommand wrapping `latest_odds`/`cross_skin_odds`/`line_movement`
      for operators. (6) a scheduled/loop poller — DONE 2026-07-21
      (`a1b9e08`): `betb2b poll <skin> <status> --interval N --db ...` loops
      scrape+persist; verified live — a 2-cycle poll captured 667 selections
      with >=2 price points (real line movement). MED — this is the
      "data processing" layer the odds-comparison product needs.
      NEW follow-up (7): **bootstrap-once fast-poll** — each poll cycle
      currently re-launches the browser (~70-90s), so the floor interval is the
      scrape duration. For sub-minute line-movement resolution, harvest cookies
      once then httpx-poll GetGameZip per event (ADR-3 hybrid) instead of
      re-rendering the DOM every cycle. MED.

---
- [ ] **DOM extractor under-captures: virtual scroll renders only ~1 screenful** (added 2026-07-21 by Claude Code, Session 25) —
      HIGH-ish coverage bug. The linebet live/prematch SPA VIRTUALIZES the game
      grid: the captured `/en/live/basketball` HTML had 16 championship headers
      (`dashboard-champ-name__label`) but only 10 rendered game rows
      (`dashboard-champ__game`), plus `virtual` scroll markers + 66 `skeleton`
      placeholders. So every scrape/poll captures only the first ~10 games of a
      card that is genuinely larger (>=16 here). `--count` is an API-feed param
      and doesn't help (feed is 406 → DOM fallback). The odds store + poller are
      therefore only tracking the top ~10 events per skin/sport.
      Fix: in `src/sites/betb2b/session.py::render_dom_events`, after the grid
      appears and before extraction, defeat virtualization — repeatedly
      `window.scrollTo(0, document.body.scrollHeight)` (or scroll the grid
      container) until `document.querySelectorAll('.dashboard-champ__game').length`
      stops growing (bounded by a max_scrolls cap + a short pause per scroll so
      lazy rows render). Then extract. Add `max_scrolls`/`scroll_pause` config.
      Validate live: a full live-basketball scrape should return >=16 events
      (all championships), not 10. MED–HIGH — without it the product misses most
      of every card.
