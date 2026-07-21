# Session 25 — betb2b: Live DOM selectors + Market depth (HIGH-priority gaps)

**Status:** ready — next agent pick up here.  
**Target:** betb2b (linebet skin, Kenya direct egress).  
**Setup agent:** Super Z | GLM | Z.ai cloud sandbox | 2026-07-21 | Core 0.2.0  
**Built on:** Session 24 (`reviews/2026-07-21-review.md`).

> Read `.context/kickoff.md` first, then this file. The `.context/` protocol
> is the front door; this file is the per-session lock and concrete handoff.

---

## Why this session exists

Session 24 unblocked the CLI (argparse `%` fix shipped at `5e1dfc3`), proved
linebet works **direct from Kenya without a proxy** (allowed_countries:
`["KE"]`), and validated prematch DOM extraction: 28 events, 100% teams /
competition / market coverage, 50% H2H coverage, 63.6 s scrape. Two HIGH
gaps remain and block the betb2b scraper from being production-quality:

1. **Live DOM extraction is broken** — 70 events returned with garbled
   team names (duplicate / truncated), 0 markets, 0 scores. The in-play
   page renders through a different Vue subtree than the prematch grid;
   the `dashboard-champ` selectors in `sports/base.py::DOMSelectors`
   don't match.
2. **Market depth is one-deep** — only the main "To Win Match" / "1x2"
   market is captured per event (DOM only renders the main market).
   `GetGameZip` enrichment is NOT running for DOM-extracted events
   (0 fetched in Session 24), so the full market tree (handicaps,
   totals, BTTS, etc.) is missing. `Get1x2_VZip` still returns 406 per
   ADR-4.

Both are operator-blockers: without live coverage the scraper is
prematch-only, and without market depth it cannot feed the downstream
odds-comparison use case.

---

## Concrete entry points (read these before coding)

| File | Lines | Why |
|------|-------|-----|
| `src/sites/betb2b/extraction/dom.py` | 1–349 | The DOM extractor. `_build_page_script()` (83–212) is the in-page walker; `extract_events_from_page()` (229–349) maps raw rows → `Event`. Garbage-team guard at 67–77. |
| `src/sites/betb2b/sports/base.py` | 42–100 | `DOMSelectors` dataclass — the selector bundle the extractor consumes. Defaults target the prematch `dashboard-champ` grid. **Live page needs overrides.** |
| `src/sites/betb2b/scraper.py` | 1–694 | `BetB2BScraper._run_action()` triggers DOM fallback; `_enrich_with_h2h()` (Session 21) is the per-event enrichment pattern to mirror for `GetGameZip`. |
| `src/sites/betb2b/session.py` | render_dom_events | Navigates the skin's live/line page and calls `extract_events_from_page()`. The `_on_page_ready` callback is where a snapshot of the live DOM can be captured for selector discovery. |
| `src/sites/betb2b/extraction/rules.py` | 1–689 | Terse-key JSON → Event/Market/Selection. `_extract_markets()` is what `GetGameZip` enrichment would call. |
| `src/sites/betb2b/cli/main.py` | 1–444 | CLI entry. `compare-match` subcommand (added Session 19) is the UI-vs-API gap tool — use it to inspect live page DOM. |
| `src/sites/betb2b/scripts/compare_match.py` | — | Polls 7 API endpoints for one match + extracts UI data. Reuse its browser session for live DOM probing. |
| `tools/analyze_match_html.py` | — | DOM analysis tool — discovers live CSS class names from captured HTML. |

---

## Phase 1 — Live DOM selector discovery (HIGH, do this first)

**Goal:** Extract clean team names, scores, and at least the main market
from the linebet `/en/live/basketball` (or `/en/live`) page.

**Symptoms observed in Session 24:**
- Team name string: `"Ajax  Olympiacos Piraeus  0000-Ajax  Olympiacus Piraeus  0000"` — duplicated and concatenated.
- 0 markets extracted (the `c-bets__bet` / `coupon-loading-component__coef` selectors don't match live cells).
- 0 scores (the `.ui-team-scores__scores` / `.dashboard-game-block__score` selectors don't match live scoreboard).

**Plan:**
1. **Capture live HTML** — bootstrap linebet direct (no proxy), navigate to `/en/live/basketball`, wait for in-play state to settle, dump `page.content()` to `data/telemetry/betb2b/live_dom_capture_<ts>.html`. Use `tools/analyze_match_html.py` or a fresh probe script to enumerate actual class names for: (a) game row container, (b) team name elements, (c) score elements, (d) odds cells.
2. **Compare prematch vs live DOM** — diff against a prematch capture. The prematch grid uses `dashboard-champ` / `dashboard-champ__game` / `dashboard-game-block__team`; the live page likely uses a different Vue subtree (in-play component). Identify the live equivalents.
3. **Extend `DOMSelectors`** — add a `live_*` family of selectors OR a separate `LiveDOMSelectors` bundle. Preferred: add `live_championship`, `live_game`, `live_team_names`, `live_team_scores`, `live_odds` to `DOMSelectors` with sensible fallbacks, and have `_build_page_script()` branch on `is_live`.
4. **Re-test** — `python -m src.sites.betb2b.cli.main scrape --skin linebet --action list_live -v`. Verify: 0 garbage team names (the `_is_plausible_team_name` guard should already reject them; the symptom above implies the guard was bypassed by a long concatenated string that happened to be ≤ 80 chars — tighten the length cap or add a duplication detector).
5. **Update `sports/base.py`** with the new selectors; add a unit test under `src/sites/betb2b/tests/` that feeds a captured live HTML fixture through the extractor and asserts ≥ 1 valid event with non-empty home/away, ≥ 1 market, and a numeric score.

**Definition of done for Phase 1:** `list_live` against linebet basketball returns ≥ 20 events with 0 garbage names, ≥ 50% with scores, and ≥ 1 market per event.

---

## Phase 2 — Market depth via `GetGameZip` enrichment (HIGH)

**Goal:** Per DOM-extracted event, fetch the full market tree from
`/service-api/LineFeed/GetGameZip?id=<eventId>` (prematch) or
`/service-api/LiveFeed/GetGameZip?id=<eventId>` (live) and merge into
`Event.markets` via the existing `_extract_markets()` in `rules.py`.

**Why `GetGameZip` not `Get1x2_VZip`:** ADR-4 says `Get1x2_VZip` returns
406 (auth-header rotation). But Session 19/20 confirmed `GetGameZip`
**reliably returns ~24 KB** of data with scores, periods, AND the full
`E[]/AE[]` market tree. The event id is already captured by the DOM
extractor (`eventId` from the match link `href` — see `dom.py:189–195`).

**Plan:**
1. **Mirror `_enrich_with_h2h()`** (Session 21) — add `_enrich_with_markets()` in `scraper.py` that iterates DOM-extracted events, polls `GetGameZip` via direct `httpx` with harvested session cookies, parses via `rules._extract_markets()`, and replaces the shallow DOM market with the full tree.
2. **Cap & rate-limit** — respect `skin.max_odds_fetch` (default 20). Use sequential polling or a bounded `asyncio.gather` with a semaphore honouring the client rate limit. A full card (100+ events) should not fan out to hundreds of concurrent requests.
3. **406 / non-2xx handling** — silent fallback to the DOM-extracted market (don't lose what we already have). Log a warning. Do NOT chase the auth-header contract (ADR-4 — DOM is the stable path; `GetGameZip` is the best-effort enrichment).
4. **Feature flag** — add `"markets_enrich": True` to the default `features` dict in `config.py`, mirroring the `"h2h"` flag from Session 21.
5. **Test** — unit test with a captured `GetGameZip` response fixture (use `betb2b_validate_linebet/captured/` if a real capture exists, else synthesize from `rules.py` docstring). Assert ≥ 5 markets per event for a basketball prematch event.

**Definition of done for Phase 2:** A prematch scrape of linebet basketball returns ≥ 5 markets per event for the first 10 events (was 1). Live events return ≥ 1 market (the main one from DOM) + best-effort `GetGameZip` enrichment.

---

## Phase 3 — Statistics / timeline enrichment (MED, optional this session)

Only if Phases 1 + 2 land early. The `statisticfeed/api/v1/Game/statistics`
and `/timeline` endpoints returned 404 for women's Chinese basketball in
Session 20. Needs an **NBA major league** match to test. If the live card
has one, probe both endpoints and wire the response into `Event.statistics`
/ `Event.timeline` (new dataclass fields, mirroring `H2HData` from Session 21).

If no NBA match is live, defer to a future session — log the gap in
`backlog.md` and move on.

---

## Phase 4 — Cross-skin validation (LOW, time-box 30 min)

**Working configuration for this session:**
- **Primary (linebet):** direct mode, no proxy. Kenya egress is in `allowed_countries: ["KE"]`.
- **Proxy fallback** for cross-skin testing: `http://TisoneK:Taalib01@bore.pub:50670` (set as `BETB2B_PROXY_URL` / `_USER` / `_PASS` / `_COUNTRY=KE` / `_ID=kenya`). Bore tunnels rotate — verify reachability before relying on it.
- **Blocked from Kenya direct (Session 24):** helabet, 22bet, betwinner — timed out or 0 events. Test each through the proxy; if still blocked, log in `flaws/log.md` and skip.

Run `validate_live --skin <skin> --sport basketball --count 50 --compress` for each. Confirm event_count > 0 for both `list_live` and `list_prematch`. This re-tests the existing backlog item "Run + confirm betb2b live e2e — all endpoints collect data".

---

## Proxy & credentials (this session only)

- **Proxy:** `http://TisoneK:Taalib01@bore.pub:50670` — Kenya egress. Use for cross-skin testing only; linebet works direct.
- **GitHub PAT:** `github_pat_11ASCEY4...` — for pushes from cloud/sandbox. **Strip from `.git/config` immediately after clone/push** per `.context/kickoff.md` Step 0.
- **Git identity for commits:** `Tisone Kironget <tisonkironget@gmail.com>` (per `memory/user/identity.md`).

**Never commit secrets to tracked files.** The proxy URL above contains
credentials — it lives in this `current.md` only as a session pointer;
the next agent must set it as env vars at runtime, not write it into
product code or YAML.

---

## Exit checklist (before closing Session 25)

- [ ] Phase 1 done: live DOM selector rework shipped + unit test green.
- [ ] Phase 2 done: `GetGameZip` market enrichment shipped + unit test green.
- [ ] Phase 3 attempted or deferred with a logged reason.
- [ ] Phase 4 cross-skin results recorded (even if blocked).
- [ ] All product-code commits under conventional prefixes (`feat(betb2b):`, `fix(betb2b):`); all `.context/` updates under `chore(context):`. **Never mix surfaces in one commit** (Session 14/15 lesson).
- [ ] Pushed to `main`.
- [ ] Review report written to `.context/memory/reviews/2026-07-2X-review.md`.
- [ ] Session entry appended to `.context/memory/agents/sessions.md`.
- [ ] This file cleared to "Idle — no session in progress" with a one-paragraph summary.

---

## Open items deferred to backlog (not this session)

- Source-level fix for `_initialize_module()` import-time crash (carried from Session 24).
- `ruff` typing debt in `cli/main.py` + `validate_live.py` (carried from Session 23).
- `numpy/scipy` install in venv to unblock `analytics_engine` (carried from Session 22).
- `datetime.utcnow()` migration (1081 uses, carried from Session 1).
