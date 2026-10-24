# Agent Sessions (append-only within the current office)

One entry per agent session in the **current office**, newest at the bottom.
Never edit or delete past entries — append corrections instead. This is not
append-only *forever*: when the office reaches `office_size` sessions (or a
milestone), `ledger-history close` freezes this whole office verbatim into
`.context_ledger/history/office-<NNN>/` (roster, registry, notes, logs —
nothing trimmed), writes the permanent accomplishments record
`.context_ledger/history/office-<NNN>.md`, and opens a fresh empty office
here. Closed offices in `history/` and `archive/` are never read at session
start. Before closing, note which open threads still matter — they are
re-seeded into the new office explicitly, and nothing else carries over.

<!-- TEMPLATE — copy below the last entry and FILL IN every placeholder:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from .context_ledger/core/roles/> | **Core:** <version from .context_ledger/core/VERSION>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md (actionable) or tasks/parking-lot.md (findings/questions), or "none">
- **Notes:** .context_ledger/memory/office/sessions/<date>-<N>/notes.md  (or "none")
- **Report:** .context_ledger/memory/office/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-10-03 — Session 1 (Noor/S001)
- **Agent:** Noor (S001) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** operator | **Core:** 2.0.3
- **Task:** finish the core 2.0.3 migration: close the previous office, fill its permanent record, re-seed the new office.
- **Commits:** ledger only (check-ins, close + re-seed, entry points, core 2.0.4 update, bookkeeping); no product code.
- **Outcome:** done (after two operator corrections — first pass skipped the protocol; see flaws log) — previous office frozen verbatim and recorded in `history/office-001.md`; backlog re-seeded with 20 actionable rows (cap 20), one carry-over ADR written, new roster and `STATE.md` generated. The close was operator-requested; the registry held 13 sessions, under the 20-session door threshold.
- **Open items:** the 20 backlog rows (top: linebet live re-verification, Neon sub-game volume check).
- **Follow-up (entry points):** `AGENTS.md` and `CLAUDE.md` regenerated from the 2.0.3 templates (the weak-agent floor); the project text they carried (architecture, BetB2B rules 11-17, setup, key files) moved verbatim to `memory/overrides/project-guide.md`, wired in via an override bullet so it survives core updates.
- **Notes:** none
- **Report:** .context_ledger/memory/office/reviews/2026-10-03-review.md


---
## 2026-10-03 — Session 2 (Achieng/S002)
- **Agent:** Achieng (S002) | **Model:** deepseek/deepseek-flash | **Platform:** Lameck-Windows (Windows 11, DESKTOP-3LRR8MD) | **Role:** engineer | **Core:** 2.0.4
- **Task:** operator: (1) "I hope now windowsgates passes" — verify the gate on Windows after the core migration; (2) check product code for `.context_ledger` vocabulary contamination.
- **Commits:** 2 (`80220d6` product: `tools/gates/pytest.sh` + `.gitattributes` LF pin; `698d297` ledger: `gates.conf` portable launcher) + ledger bookkeeping.
- **Outcome:** done — the gate did NOT pass as pulled (core 2.0.4 does not translate the POSIX path); fixed in the project registry: one launcher, invoked as `git -c 'alias.ledger-gate=!sh tools/gates/pytest.sh' ledger-gate`, picks `.venv/bin/python` or `.venv/Scripts/python.exe`. Verified through **both** runners (`sh …/ledger-gates` and the PowerShell path `ledger-gates.cmd` uses) — both PASSED; failure propagation checked (exit 5). Rejected alternatives with evidence: bare `sh` (not on the clean Windows PATH), inline `;` conditional (git treats `;` as a comment), dropping to discovery (bare `python`). Lint sweep: 23 hits, **all** in `AGENTS.md`/`CLAUDE.md` (managed entry points), zero in `src/`/`tools/`/`tests/`/`docs/`; one real leak in my own new script's comment found and stripped.
- **Open items:** none new; the upstream `lint --tree` entry-point limitation remains the only tree-sweep exit-1 cause.
- **Notes:** none
- **Report:** .context_ledger/memory/office/reviews/2026-10-03-review-2.md

---
## 2026-10-04 — Session 3 (Wanjiru/S003)
- **Agent:** Wanjiru (S003) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.0.4
- **Task:** operator: find and fix the minutes-long silences in a betb2b scrape (remote Neon persist and backfill passes).
- **Commits:** product: `perf(betb2b)` batch event/sub-game/state writes + phase timings; one-transaction backfill passes (`store.batched`) + `_team` rename-clash fix; 5s connect timeout + warning log for direct-call failures. Ledger: check-in, codename S003 (S002 was Achieng's).
- **Outcome:** partial — unverified against Neon (no DATABASE_URL in the session); gate + SQLite smoke tests pass. Operator should rerun and read the `persist run … [prefetch …]` timing line.
- **Open items:** confirm timings on a real run; mid-fetch 10-16s stalls may be server throttling, not fixable client-side.
- **Notes:** none
- **Report:** none

---
## 2026-10-04 — Session 4 (Mei/S004)
- **Agent:** Mei (S004) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.0.4
- **Task:** operator: read the engine's `SCRAPER_DATA_ISSUES.md` (scorewise-engine) and fix all eight scraper-side data issues.
- **Commits:** product: `fix(betb2b)` H2H kind / dedupe / placeholder scores / team backend ids; `fix(betb2b)` void placeholder results, near-start odds refresh, withdrawn-line marker, `repair-data`. Ledger: check-in, project-guide section.
- **Outcome:** done in code, unverified on live data — new `data_quality.py` + 37 tests (both backends), suite green. Issues 1, 3, 5, 6, 7 fixed at write time; 2 via `team_aliases` learned from matching games; 4 no new facts for superseded events (replacement is always a stored event by construction); 8 hourly refresh for matches starting within 12h + suspended row for a withdrawn line. Existing rows need `cli repair-data` (not run: it writes the hosted store).
- **Open items:** run `repair-data` against Neon with the owner's say-so, then re-run `python -m engine.dataquality`; schema `ALTER`s for `h2h_games.kind/result_flag` + new `team_aliases` apply on connect (verify); the extra refresh raises request volume (see B-2026-10-03-2).
- **Notes:** none
- **Report:** none
- **Follow-up 8 (geo-restricted machines, operator rule):** an unexplained `geo_block` on betwinner/linebet on this US machine was a browser PAGE load (`/en/block`, HTTP 203) from the blocked address; the per-site cooldown then also stopped the direct feed runs although feeds are not country-gated. Operator: strict rule for agents on geo-blocked machines — no page loads without the proxy, data fetching only. Shipped: `src/security/egress.py` (`SCRAPAMOJA_GEO_RESTRICTED=1` or a learned page-level block -> `PageLoadsRefused` for the browser bootstrap, DOM render, hybrid scrape, profile warm-up, betb2b + linebet probe scripts; `--direct` untouched), a page-level country block without a proxy now switches pages off without starting a feed cooldown, `security status/clear` show/lift it, 9 tests, `.env.example`, rule 18 in `project-guide.md`, an override in `rules.md`; this Mac's `.env` set restricted. Note: the 05:29-05:39 blocks came from something other than my runs (they started 06:22) — unattributed.

---
## 2026-10-04 — Session 5 (Imani/S005)
- **Agent:** Imani (S005) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.0.4
- **Task:** operator: cover the full-capture scraper work and the new strict geo-restricted-machine rule in the ledger memories. This session continues the work logged in the closed office (`history/office-001/agents/sessions.md`, "Session 52 (Mei/S450)" with its follow-ups 1-7); the office was closed under it, so it checked back in under a fresh name (a different agent holds "Mei" as S004 here).
- **Commits:** product (this session's tail): `feat(security)` geo-restricted machines never load a site's pages without a proxy; earlier in the same working session (listed in the frozen entry): sub-games by default + subject/period labels + coverage table, H2H backfill + dedupe, results/period/statistics passes, probe memory, skip-by-default, summary output, linebet via the allowed-country tunnel, the Kenya-machine brief. Ledger: check-in, rule 18 + override, this update (ADR-2..4, preferences, flaw, backlog, environments, report).
- **Outcome:** done — the ledger now states the rule (`overrides/project-guide.md` rule 18, `overrides/rules.md`, ADR-2), the data model and gap semantics (ADR-3), and the skip/probe/timeout behaviour (ADR-4); preferences, a flaw (no rule + the office reset under a live session), environments (the Mac is geo-restricted), backlog (B-2026-10-04-1..4; 4 low rows moved to the parking lot at the cap).
- **Open items:** B-2026-10-03-1 (linebet end to end on the Kenyan machine), B-2026-10-04-1 (per-skin skip filter), -2 (Neon volume), -3 (declare restricted machines), -4 (legacy statistics table).
- **Notes:** none
- **Report:** .context_ledger/memory/office/reviews/2026-10-04-review.md
- **Correction (appended, never edited above):** the bullet "Follow-up 8 (geo-restricted machines, operator rule)" at the end of Session 4's entry was written by S005 (Imani), not by S004; it landed there because the office had been reset and the file tail then belonged to S004. Its content is covered by ADR-2 and this entry.
- **Closing addendum:** after the wrap the operator's three-skin refetch finished on the Mac (Neon: 681 events, 230 finished, statistics for 183 matches, 81k player rows; betwinner 477 / melbet 361 / 22bet 332 events, linebet 2) and one more bug surfaced and was fixed: a match whose source gave only player statistics (no team periods) was re-asked every run (`fix(betb2b)`, test added). The betwinner follow-up was refused once by the old `geo_block` cooldown (started 3 minutes early) and re-ran clean. All work committed and pushed; no background jobs left running.


---
## 2026-10-10 — Session 6 (Kofi/S006)
- **Agent:** Kofi (S006) | **Model:** claude-sonnet-5-5 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.0.4
- **Task:** operator pasted an engine-side report that the scraper has filled no results since 6 Oct 05:52 UTC; find out why.
- **Commits:** ledger only (check-in, this entry). No product change, no scrape run (this Mac is geo-restricted).
- **Outcome:** diagnosed, no code fault found. Read-only checks of Neon: last write of every scraper table is 6 Oct 05:51-05:54 UTC (`scrape_runs` 63-66, betwinner: results, backfills, prematch); store 296 MB of 1000 MB, reachable, not read-only; no scrape process, launchd job or crontab for the scraper here (the only launchd jobs are the engine's `com.scorewise.new/full/grade`). The scraper has only ever run when started by hand (runs 4, 5 and 6 Oct); `BetB2BScheduler` exists but nothing starts it. So results stopped because nobody ran the scrape, not because a run failed. Remedy: run `scrape betwinner` (results pass settles finished matches, incl. 7-9 Oct) or schedule it; the matches' results are still on the source for a week after kickoff, so a run now backfills 7-9 Oct games.
- **Open items:** decide how the scraper is kept running (launchd job on a non-restricted machine, or the scheduler as a service).
- **Notes:** none
- **Report:** none

### Follow-up (Kofi/S006, same day) — scraper service added
- Operator asked for the missing scraper service; no ingest wanted for now. Shipped `scripts/schedule.sh` (`a08a938`): launchd job `com.scrapamoja.betb2b`, `scrape betwinner scheduled --sport basketball --direct` every 6 h, log `~/Library/Logs/scrapamoja-scrape.log`; installed on this Mac.
- First hand run (run 71): 200 events, 25,742 markets, 589 s, rc 0. Results pass: 200 pending -> only 21 finished recorded (88 period scores). Scored games per day afterwards: 6 Oct 20/291, 7 Oct 0/48, 8 Oct 0/86, 9 Oct 0/17 -> the 7-9 Oct results are NOT backfilled yet. The pass looks capped at 200 pending per run (not verified); later runs should work through the rest. Open: verify after the next scheduled runs (~14:42 and ~20:42 UTC), and check whether the 200 cap or the source not yet resolving those games is the limit.

### Follow-up 2 (Kofi/S006) — on-demand results
- Operator found the periodic full scrape inconvenient and asked for an on-demand results mode. Cause of the missing 7-9 Oct scores found: `events_needing_results` is capped at 200, oldest first, so old unresolved games starved newer ones (an uncapped run saw 514 pending). Shipped `results <skin> --auto | --event ID` (+ `store.events_by_ids`, 1 test) and switched the launchd job to `results --auto` every 30 min (odds: manual `scripts/schedule.sh scrape`). Result: 7-10 Oct scored games 0 -> 49; the rest still unresolved by the source (ReadTimeouts and 'no data' on many; they retry each run until the 7-day give-up). Open: odds for new games now need a manual scrape or a second job; decide.

### Follow-up 3 (Kofi/S006) — two jobs
- Operator: the full scrape stays scheduled every 6 h as usual. `scripts/schedule.sh install` now installs two launchd jobs: `com.scrapamoja.scrape` (6 h, full scrape, direct, no ingest) and `com.scrapamoja.results` (30 min, `results --auto`); the first version's `com.scrapamoja.betb2b` label is replaced. Both installed on this Mac; first scrape fires ~6 h after install, no RunAtLoad.

### Follow-up 4 (Kofi/S006) — "Alternative Matches" skipped
- Why finished games had no scores: 352 of 360 unscored matches since 6 Oct are in "<League>. Alternative Matches" (EuroCup 206, Euroleague 90, FIBA CL 56) — the bookmaker's simulated markets with real team names; the source answers "no data" for them. Real leagues are scored (Euroleague 29/29 ...). Fix: `events_needing_results` (both backends) leaves them out; 1 test; pending 514 -> 97. Engine check (read-only, Neon): 0 predictions, 0 paper bets, 0 real bets, 0 grade rows and 0 H2H on the 442 alternative events (90 upcoming) — the engine skips them (no H2H), so no engine change needed. Note: the engine's audit rule E3 (`engine/dataquality.py`) keywords don't include "alternative", so it won't flag them; optional hardening on the engine side.

### Follow-up 5 (Kofi/S006) — is_alternative flag
- The engine agent (operator's other session) asked for a row-level marker instead of league-name matching. Shipped `events.is_alternative` (BOOLEAN NOT NULL DEFAULT FALSE; ORM model, SQLite schema, idempotent Postgres ALTER), `store.mark_alternative` (called after every persist and from `repair-data`), tests. Applied to Neon: column added and 442 events flagged (90 upcoming) — an additive change to the shared store, no other data touched (did NOT run the full `repair-data`). The engine can now filter `WHERE NOT is_alternative`; the engine's own name-based exclusion keeps working.

### Follow-up 6 (Kofi/S006) — the 7 unscored real-league games
- Asked the source for the 7 games still without a result: all "no data", no errors, no stat ids. The engine agent then verified from news sites that 6 are real, played games in leagues the source does not cover (Philippines NCAA, Liga Femenina Challenge, Azerbaijan Superleague — "Landau Lions" is an Azeri club); my "mislabelled/simulated" guess for Landau–NTD was wrong and is retracted. Only "1st teams (Points) – 2nd teams (Points)" (FIBA CL) is a novelty market. Shipped: `mark_alternative` also flags team names ending " teams (Points)" (1 event, flagged on Neon); the results pass now excludes by the `is_alternative` flag instead of the league name. The 6 real ones stay unflagged; they are marked unresolved after 7 days and settled by hand.

### Follow-up 7 (Kofi/S006) — manual fill for uncovered matches
- Operator: agents would keep flagging the unscored real games. Shipped `results --set ID=HOME-AWAY` and `--give-up ID` (+ `store.give_up_event`, 1 test). Applied on Neon with the scores the engine agent verified from news (single-outlet for some): Arellano 62-64 Jose Rizal, Aguinaldo 84-89 Mapua (after OT), Sumgayit 76-87 Nakhchivan, Landau 102-68 NTD, Neftchi 83-79 Ordu — all `result_status 3` with a `result_manual` coverage row. Closed out as no-result: Joventut–Valencia II (score not found) and the "(Points)" novelty listing. Note for graders: the Aguinaldo score includes overtime. Nothing was predicted on any of these.

### Follow-up 8 (Kofi/S006) — canonical event id
- Engine agent asked why re-listed games are linked, not merged. Facts (Neon): 234/1,602 events superseded, 104k odds + 8.8k H2H rows on them, 8 chains (A->B->C), 6 same-game pairs unlinked because the plain "newer id needs a venue" guard rejected venue-less re-listings. Shipped (operator: "build steps 1-3"): `events.canonical_event_id` (final id after following superseded_by; own id if never replaced), `store.resolve_canonical` (flattens chains; run by `mark_superseded`), relaxed link rule (venue-less newer id ok if not a known sub-game and has H2H or >= 8 markets), 4 tests. Applied on Neon: 5 pairs newly linked (239 superseded), 0 chains, 0 null canonical ids. The 6th pair (San Sebastian–De La Salle, 758590480/81) is NOT a duplicate: 758590481 is the "1st quarter" sub-game stored as an event (in `sub_games`), so the guard rightly left it. Rows were not re-pointed (rejected: ~113k rows on a changing key). Engine side: it can group on `canonical_event_id` and drop its own link-following; the 110 predictions on superseded ids are the engine's to move.

## 2026-10-11 — Session 7 (Dayo/S007)
- Operator (from the scorewise-engine session, slip for Hapoel Beer Sheva vs Hapoel Tel Aviv 1Q Over) asked for a live-score monitoring tool polling the existing flashscore scraper. Chose: reusable poller in this repo (not a one-off agent), score + stage only, no betting logic — operator's two explicit choices, plus "not quarters only" = report the overall running score, not just the quarter.
- Validated first: `flashscore scrape basketball live` works end-to-end (returns teams/score/status; `time`/stage comes back empty at listing level for basketball).
- Shipped `feat(flashscore): live-poll` (`148fde6`): `flashscore live-poll <sport> [--match SUBSTR | --match-id ID] [--interval 30] [--cycles 0] [--for 0] [--limit] [--jsonl PATH] [--no-headless]`. Launches the browser ONCE and re-scrapes the live board each interval, printing the running score for the targeted match(es). `src/sites/flashscore/poll.py` holds the pure `poll_loop` (mirrors `src/sites/betb2b/poll.py`) + pure `select_live_matches`/`format_match_line`; the command wires the real scraper. 13 unit tests (no browser). Registered `src/sites/flashscore/tests/` in `tools/gates/pytest.sh` (it previously ran only betb2b/security/browser). Gate green with the new tests.
- Verified live: 2-cycle run printed 6 live games and captured movement between cycles (Olimpia 38-28 -> 49-30), wrote 2 JSONL snapshots, clean exit.
- Known gaps / follow-ons: (1) quarter + clock need the match detail page (summary tab / full-workflow) — listing-level `time` is blank for basketball; only overall score is reliable now. (2) `poll_loop` is duplicated from betb2b's rather than shared in a common util (kept flashscore self-contained; consolidation is a later refactor). No betting/slip-evaluation logic was added, by the operator's standing rule.

### Follow-up (Dayo/S007) — live stage/clock without the detail page
- Operator said the slip game tips off in ~49 min; used the window to close gap (1) the cheap way. Root cause of the blank stage: `BaseExtractor._extract_time_info` only handled `scheduled`/`finished` (reads `.event__time`) and returned `None` for `live`. Fixed to read `.event__stage--block/.event__stage` for live — same page, no per-match detail navigation. Shipped `feat(flashscore): capture live stage/clock` (`1a202af`) + 4 browser-free unit tests (fake nodes). Verified live: poller now prints `Paris 17-18 Strasbourg | 1st Quarter 8` (quarter + clock). So for a 1Q-total watch the poller now shows the running score AND that it's still Q1 with the clock — gap (1) effectively closed for the live board; the detail-page per-quarter breakdown (final splits after each quarter) remains only if the operator wants post-quarter confirmation. 17 flashscore tests total, gate green.

### Follow-up 2 (Dayo/S007) — live-serve JSON endpoint for task2sms
- Operator cloned `TisoneK/task2sms` into `~/Code/` and wants it as the monitor+SMS layer (chosen wiring: task2sms HTTP **Data Source** + conditional rules; triggers: tip-off / Q1 total reaches a number they give / end-of-Q1 final total). task2sms contract (read from its repo): DataSource(HTTP) fetches `url`+`json_path`; a Task condition tests one `condition_field` with gt/lt/eq/gte/lte and fills `{vars}` in the template; it has a MockProvider SMS fallback for testing.
- Shipped `feat(flashscore): live-serve` (`cbd5359`): `flashscore live-serve <sport> [--match|--match-id] [--port 8787]` runs the poll loop and serves the current match's derived state at `GET /score` (+`/health`). poll.py gained pure helpers `parse_stage`/`parse_score`/`derive_score_state` (flat JSON: found/status/home/away/total/q1_total/q1_final/q1_ended; freezes q1_final when play leaves Q1, sticky, never fabricates an unobserved Q1 total). 10 new unit tests; validated live (/score returned real state; a Half-Time match correctly showed q1_total/q1_final null). 27 flashscore tests total.
- Next: stand up task2sms backend (mock SMS) and wire a Data Source -> this endpoint + the 3 conditional tasks; validate a mock send. Blockers for REAL sms (operator-supplied, not me): SMS provider keys (Africa's Talking/Twilio) in task2sms `.env`, a destination phone number, and the Over line number for the threshold task.

### Follow-up 3 (Dayo/S007) — task2sms Task<-DataSource wiring (cross-repo; in ~/Code/task2sms)
- Discovery while scoping task2sms: the Task+DataSource+condition path is NOT wired end-to-end there — scheduler (`workers/scheduler.py`) and manual run (`api/routes/tasks.py`) both call `execute_task(db, task)` with no context, so conditions/templates never see data-source values. The working conditional-alert engine is the Web Monitor (`scraper_service.py`, event/outcome-aware). Surfaced both to operator; operator chose to FIX the Task+DataSource wiring (not pivot to Web Monitor) and to run via Docker Compose.
- Implemented in task2sms (NOT scrapamoja; task2sms uses a lighter `.context`, no hooks): `tasks.data_source_id` FK (model + schemas TaskCreate/Update/Out), `build_task_context(db, task)` in `services/core/task_service.py` (fetches the linked data source into the context dict; None when unlinked, {} on missing/failed/non-object fetch so a run never crashes), and `execute_task` now auto-builds context when none passed (so both call sites benefit, no call-site edits). Alembic `0012_task_data_source` (batch add_column + FK, idempotent). Tests `tests/test_task_data_source.py` (build_task_context + condition eval). All files `py_compile` clean.
- BLOCKED on validation: task2sms backend won't `pip install` here (cryptography has no wheel for this x86_64/Rosetta Python 3.12, tries a Rust/OpenSSL build and fails). Operator chose Docker Compose to sidestep it, but Docker Desktop is not running. task2sms changes are in the working tree, UNCOMMITTED/unpushed (will validate in Docker, then commit; push to task2sms needs operator ok). Reusable scrapamoja side is all shipped/pushed and usable standalone.

### Follow-up 4 (Dayo/S007) — resolution + clock-out
- Docker was NOT installed at all (not just off) → ran task2sms natively instead: `cryptography==45.0.7` wheel installed before requirements fixed the source-build failure; backend validated (alembic 0012, full suite 54 passed). task2sms changes committed + pushed to its origin/main (operator pushed the bootstrap range with the guard's sanctioned skip; `.claude/settings.json` committed by operator as `a7a4bdc`).
- LIVE VALIDATION (the point of all this): the operator's real slip — Hapoel Beer Sheva vs Hapoel Tel Aviv, 1st-quarter Total Over 41.5 — was tracked live with `flashscore live-poll --match-id C0j8ufzg`. Q1 closed 23–24 → Q1 total **47**, cleared the line → bet won. The poller's `q1_final` signal matched exactly. Monitoring stopped at operator's request (was at 35–44, halftime).
- scrapamoja is fully shipped/pushed (`148fde6` live-poll, `1a202af` stage/clock, `cbd5359` live-serve). Clocking out.

---
## 2026-10-16 — Session 9 (Kwame/S009)
- **Agent:** Kwame (S009) | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.2.0
- **Task:** operator: read the engine's handoff then pull and focus on it. Handoff = `scorewise-engine/HANDOFF-scrapamoja-two-tier-storage.md` (Marco/S003): the shared cloud Postgres hit 100% and silently broke grading; it asked scrapamoja to go local-first and push a lean, H2H-qualified, latest-odds-only, size-capped set to the cloud.
- **Core update:** 2.0.4 → 2.2.0 (operator: "upgrade"); `ledger-guard` installed (pre-commit/prepare-commit-msg/pre-push hooks + `.claude/settings.json`). `.claude/settings.json` is UNCOMMITTED — the app's self-modification guard blocks committing Claude Code hook config; left for the operator to commit if wanted (hooks are active locally regardless).
- **Re-scope (operator overrode the handoff's division of labour):** "the scraper fetches and stores; the engine omits/filters." Chosen: **engine owns cloud too** — scraper is local-first + full mirror, NO scraper-side qualification/filtering/collapse, and the scraper no longer prunes/caps/truncates the cloud. (So the big filtering build I had designed — `cloud_sync` with H2H qualification + latest-odds collapse + delete-oldest cap — was NOT written; it would have put filtering in the scraper.)
- **Commits:** product `42e43e3` `feat(betb2b): two-tier storage — scraper observe-only on cloud quota`; ledger (this entry, ADR-6, project-guide rule 19, core-migration `2271d22`).
- **Outcome:** done in code, unverified on live cloud (this Mac has no DATABASE_URL/.env). Scheduler quota pass is now **observe-only + fail-loud** by default (`quota.retention_enabled`/`retention_action`, default off); old self-pruning/truncate behind `BETB2B_CLOUD_RETENTION=1`. `scripts/schedule.sh` passes `BETB2B_STORE_MODE`/`DATABASE_URL`/`BETB2B_DB_PATH` through for local-first + mirror (`BETB2B_STORE_MODE=mirror`). 3 new/2 updated scheduler tests; full gate green. `HANDOFF-RESPONSE-two-tier-storage.md` written back to the engine. ADR-6 recorded.
- **Open items:** (1) THE ENGINE must now extend `sw retain` to the scraped tables (`odds_snapshots`, `player_stats`, …) or the cloud refills to 100% — operator accepted the risk; relayed in the response note. (2) Operator to validate local-first + mirror against Neon with `DATABASE_URL` set and pick the Neon history-retention window (the reclaim caveat). (3) `.claude/settings.json` commit decision (self-mod guard).
- **Notes:** none
- **Report:** none

---
## 2026-10-17 — Session 10 (Juma/S010)
- **Agent:** Juma (S010) | **Model:** undisclosed | **Platform:** DESKTOP-2VPR9IB (Windows, Qoder CLI) | **Role:** skill-evolution session | **Core:** 2.2.0
- **Task:** operator: verify source session 31d52d87 (Amara/S008's "pull changes" session) and draft a reusable Skill from its Windows test-infra fixes; plan-only first round, then operator confirmed.
- **Commits:** ledger only — check-in `4e653fc`, this clock-out. No product code touched (Amara/S008 holds an in-flight working tree on this box — 4 integration test files).
- **Outcome:** skill `windows-sqlite-test-teardown` created in the user Skill dir via `skill_manage create` (no name collision; frontmatter validated by the skill registry). Content verified against committed state, not the recommendation JSON: dispose-before-unlink (`ab24e35` — `tests/unit/test_feature_flag_service_site_enhancements.py:33,281`; 10 setup errors → 44 passing, 2 stale xfails dropped), SIGALRM hasattr guard (`596860a` — `tests/unit/test_src_modules_importable.py:49`), and `store_orm._engines.clear()` around DATABASE_URL-backed tests (`store_orm.py:47` + betb2b tests). JSON correction recorded in the skill: the `_engines.clear` pattern predates that session — an established repo pattern, not "the third fix of the session". Skill also records known gaps: integration fixtures still unlink without dispose (`tests/integration/test_site_flags_migration.py:36`, `test_selector_engine_site_integration.py:34`, `test_site_api_endpoints.py:41`).
- **Open items:** the three integration fixtures above remain unfixed — deliberately left alone; Amara/S008's live session owns adjacent integration test files.
- **Notes:** source session 31d52d87 was LIVE while verifying; all skill citations were taken from committed state only. Office headcount 9 at check-in (limit 20) — no close needed.
- **Report:** none

---
## 2026-10-24 — Session 11 (Zuri/S011)
- **Agent:** Zuri (S011) | **Model:** claude-opus-4-8 | **Platform:** Baos-Mac-mini (macOS, Claude Code desktop) | **Role:** engineer | **Core:** 2.2.0
- **Task:** operator: "confirm handoff and start working" → the DB handoff. Execute the engine's local-Postgres cutover (`scorewise-engine/HANDOFF-scrapamoja-local-postgres-cutover.md`, Samir/S006, 2026-10-24): repoint the scraper off the frozen Neon cloud (1024 MB `DiskFull`) onto the shared local Postgres `postgresql://bao@localhost:5432/scorewise`, including the scheduled `com.scrapamoja.*` jobs; confirm writes land locally.
- **Commits:** product `67e0155` `docs(db)` HANDOFF-RESPONSE; ledger (check-in, stale-row cleanup, this entry, ADR-7, backlog edit, STATE). Config change (not a commit): `src/sites/betb2b/.env` repointed (gitignored). No scraper/store code changed — the cutover was a one-line `.env` change as the handoff predicted.
- **Outcome:** done + verified live on local Postgres. Found the DB-URL resolution the engine couldn't: the scheduled CLI loads the **gitignored `src/sites/betb2b/.env`** (`cli/main.py:32`) before the (absent) repo-root `.env`; it held the Neon URL, so the plists/`launchctl`/repo-root all looked empty while jobs still reached Neon. Repointed that line to local PG (old Neon parked as a comment for rollback); `_normalize` auto-pins psycopg v3. Verified: resolution → local (not Neon); transactional write probe on local PG ok; cutover schema present; a bounded `--direct` betwinner scrape wrote 3 `scrape_runs` + 191 fresh event results (dated 2026-10-24) to local PG. Stopped the run after proof (it had moved into the unbounded stats backfill) to stay gentle on the endpoints. Response written back: `HANDOFF-RESPONSE-local-postgres-cutover.md`. ADR-7 recorded. Also cleaned the stale Amara/S008 roster row (operator confirmed no other working agent).
- **Open items:** engine side still owes the local→remote push + `sw retain` against Neon before pruning (ADR-6, their ADR-18). B-2026-10-04-2 (quota-monitor blind spot) re-scoped to low-urgency — scraper no longer writes cloud on this machine. The scheduled jobs will now feed local PG on their 6 h / 30 min cadence; operator to confirm the next scheduled run lands locally.
- **Notes:** this Mac is geo-restricted — direct feed fetch works, pages do not; cutover doesn't depend on the proxy. Office headcount 10 at check-in (limit 20) — no close needed.
- **Report:** none

### Follow-up (Zuri/S011) — on-demand full scrape populates today/tomorrow
- Operator asked whether today's/tomorrow's games were in the DB (they weren't: 0/0; the last scheduled full scrape ran ~1 h before the cutover and its discovery went to the dead Neon). Confirmed the scraper IS running — both launchd jobs loaded; the 30-min `results --auto` runs were already landing in local PG post-cutover (cutover verified on the scheduled path), but `results` only settles finished games and doesn't discover upcoming ones.
- Ran an on-demand full `scrape betwinner scheduled --sport basketball --direct` (`--direct`, geo-safe). Persisted run 991: 200 events / 232,988 odds / 27,582 markets / 74 with H2H → local Postgres (`remote, mode=auto`). events 2840 → 3040; **today 2026-10-24 = 71 games, tomorrow 2026-10-25 = 19**. The next scheduled 6 h scrape (~11:52 UTC) will refresh again.

---
## 2026-10-24 — Session 12 (Nia/S012)
- **Agent:** Nia (S012) | **Model:** unknown | **Platform:** DESKTOP-2VPR9IB (Windows 11, Qoder Desktop) | **Role:** engineer | **Core:** 2.2.0
- **Task:** operator: "Pull changes" — sync the checkout with `origin/main` and run the ledger lifecycle.
- **Commits:** ledger only — check-in `c13f7aa`, STATE regen `c5fa312`, this clock-out. No product code touched.
- **Outcome:** fast-forward pulled `a1cdf52`→`da2d2e7` (9 commits, 6 files: office STATE/roster/sessions/decisions/backlog + `HANDOFF-RESPONSE-local-postgres-cutover.md`); `ledger-sync verify` OK and `status` reports core 2.2.0 up to date against `TisoneK/context-ledger`; pre-commit gate PASSED on both staged ledger trees.
- **Open items:** none from this session. The pulled `HANDOFF-RESPONSE-local-postgres-cutover.md` is Zuri/S011's cutover response — already reflected in ADR-7/STATE; no action required.
- **Notes:** git hooks are MISSING (`ledger-guard status`) — reported to the operator; gates were run manually. Untracked `.freebuff/` and `tmp_fix_encoding.py` were present before the pull and left untouched. Office headcount 10 at check-in (limit 20) — no close needed.
- **Report:** none
