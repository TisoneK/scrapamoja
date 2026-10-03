# Office 001 — accomplishments record (permanent)

- Opened: 2026-09-07
- Closed: 2026-10-03
- Sessions: 13

The frozen office lives at history/office-001/ until it is zipped into
archive/office-001.tar.gz. This record stays in history/ forever — even after
the tarball is garbage-collected, the office is never forgotten. Not read at
session start; deliberate lookback only.

## Accomplished
- **BetB2B family scraper** (`src/sites/betb2b/`): one parameterised base scraper, brands as YAML skins (linebet, 22bet, betwinner, melbet, megapari, 888starz, helabet, paripesa), per-sport modules, hybrid access (browser cookie harvest, then plain-HTTP feed polling, DOM extraction as the drift-proof fallback).
- **Full capture and store:** every labelled sub-game (quarters, halves, per-stat groups) fetched by default; odds rows carry subject and period; a `coverage` table records offered / not offered / not attempted / failed; H2H with period scores and de-duplication; finished-match results, per-period scores and team/player statistics; probes remember answers so nothing is re-asked pointlessly. Local SQLite is the default target, any Postgres (Neon) the optional shared store, with an outbox fallback and a quota monitor.
- **Scorewise-engine export:** one match becomes up to nine prediction scopes with the H2H scope contract guarded by a summing test.
- **Security guard and browser profiles:** block types classified with their own response ladders, persisted cooldowns, evidence capture, persistent Chromium profiles with a warm-up CLI; every request path guarded and paced; a burst of identical blocks counts as one incident.
- **linebet / Gcore:** the browser-validation contract was measured (challenge is cookie-bound, full cookie jar required, statisticfeed stricter than the feed) and the two bugs that actually broke runs were fixed (session cookies dropped from the harvested header; concurrent challenges walking the ladder).
- **Diagnostics and test health:** browser-free evidence bundles, per-scrape health events, snapshot retention; `tests/unit` taken from 131 failures to green with the remaining 95 marked xfail (reason prefix `B-24`).
- **Ledger core** moved 1.1.3 to 2.0.3; this office closed at the end of that migration.

## Decisions still in force
- Deploy the control plane via Dockerfile; no scrape jobs in the API service. Transport/access is a separate axis from extraction mode. DOM extraction is the reliable primary path; never chase the rotating auth-header contract in code.
- Per-match `GetGameZip` is the market-depth path; the sports/odds pipeline is proxy-free (discovery works from any IP).
- Scraped data goes into a structured time-series store (the full match model); local SQLite is the default scrape target, a stored match is scraped once, `--refetch` overrides.
- Match identity: event ids are not stable across skins or time, sub-games are not matches, failed is not empty.
- H2H scope contract: team-total scopes zero the other team's score (the engine sums home + away).
- Every request path goes through the security guard; timeouts rest a site like blocks do; requests are paced per second. Challenge handling by a real browser is allowed; reimplementing a vendor's JS never is.
- linebet: geo-block on the website plus Gcore browser validation; the measured contract is the reference and no bypass is built.
- Retention and a quota monitor are mandatory for any hosted store (free-tier limits caused a forced read-only outage once).
- Import health is a tested invariant; fix safe findings in the tree you touch.
- Full text of every ADR: `history/office-001/plans/decisions.md`; the product-facing summary table is in `AGENTS.md`.

## Open threads
Re-seeded into the new backlog (20 rows): linebet live re-verification in a rested window; Neon sub-game volume and schema check; CLI batches' burst halt; statisticfeed session refresh; the post-run CLI hang; stale-secret and quota-limit housekeeping; the import/test-health clusters (webgl field, selector integration module, plugin permissions, dashboard API tests, undefined names, test isolation, the 95 xfails); diagnostics coverage beyond betb2b; block-time screenshots; deleting the local safety branch.

Not re-seeded (kept here as knowledge):
- Finding rate limits: the hosts drop connections per source address after a ~20 req/s burst (about 30 min); 3 req/s with one pooled client ran ~500 requests cleanly. Open only if more speed is wanted: one slow ramp 3 to 4 to 5 req/s, stopping at the first drop.
- Relist linking (`superseded_by`) and the sub-game filter were verified on basketball only.
- Smaller import oddities: a telemetry alerting integration missing its interface; flashscore CLI importing the top-level `tests` package; `resilience/config.py` shadowed by `resilience/config/` (importing writes a JSON into the cwd); a setup script inside the import tree.
- Legacy pre-2026-09 backlog items (linebet HAR discovery, replay mode, scraper classifier, proxy-layer migration, etc.) were superseded by the hybrid design and are not carried; they remain in `history/office-001/tasks/backlog.md`.
- Package-level protocol flaws logged against core 0.x/1.1 (flows upstream; most addressed by 2.0.x): the `ledger-mem lint --tree` entry-point false positives remain relevant (ADR citations in `AGENTS.md`/`CLAUDE.md`).
