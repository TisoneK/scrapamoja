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
