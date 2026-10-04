# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Carry-over — the standing technical decisions of the previous office (2026-10-03)
- **Status:** accepted
- **Context:** the office closed; its ADRs are frozen in `history/office-001/plans/decisions.md`, which the new office does not read at session start.
- **Decision:** the following stay in force: control plane via Dockerfile with no scrape jobs in the API; transport separate from extraction mode; DOM extraction is the primary BetB2B path and the rotating auth header is never chased in code; `GetGameZip` is the market-depth path and the discovery pipeline is proxy-free; scraped odds live in a structured time-series store (local SQLite default, any Postgres optional, a stored match is scraped once); event ids are not stable across skins or time, sub-games are not matches, failed is not empty; team-total scopes zero the other team's H2H score; every request path goes through the security guard and is paced; a real browser may clear a vendor challenge but its JS is never reimplemented; hosted stores need retention and a quota monitor; import health is a tested invariant.
- **Consequences:** reverse any of these only with a new ADR that supersedes this one. Per-decision rationale and evidence: `history/office-001/plans/decisions.md`.

---
## ADR-2: Geo-restricted machines never load a site's pages without a proxy (2026-10-04)
- **Status:** accepted
- **Context:** betting sites country-block whole countries by redirecting a *page* request (HTTP 203 to `/en/block`); their data feeds are not country-gated. A browser/hybrid run from a blocked connection was recorded as a `geo_block` against the machine, and the per-site cooldown then also stopped the direct feed runs. An unattributed run on the operator's US Mac produced exactly this on 2026-10-04.
- **Decision:** on a machine outside the allowed countries, nothing loads a site's pages (browser bootstrap, DOM render, hybrid-mode scrape, profile warm-up, probe/compare/discover scripts, "testing the site") unless traffic goes through the allowed-country proxy. Data is fetched only on the page-free path (`scrape ... --direct`). Enforced in code (`src/security/egress.py`): `SCRAPAMOJA_GEO_RESTRICTED=1` in the machine's `.env`, or a page-level country block seen without a proxy (learned marker beside the block ledger), makes the browser paths raise `PageLoadsRefused`. A page-level geo-block without a proxy switches page loads off for the site and no longer starts a cooldown, so the feed path keeps running. `python -m src.security status|clear <site>` shows/lifts it.
- **Consequences:** agents must not unset the variable, clear the marker, or route around the refusal to make a run proceed; a task that needs a browser is handed to an allowed-country machine (the Kenyan machine, `docs/proposals/KENYA_MACHINE_BRIEF.md`). Tests must use offline fixtures. Feed-level geo-blocks still rest the site. Full rule: `overrides/project-guide.md` (BetB2B rule 18); standing override in `overrides/rules.md`.

---
## ADR-3: Store everything the source offers, and record what was offered, absent or never asked (2026-10-04)
- **Status:** accepted
- **Context:** the consumer needed totals lines for every subject x period, unambiguous labels, period scores, and gaps it could trust. A default scrape only fetched the main game, so "the source has none" and "we never looked" were indistinguishable; H2H was stored for ~28% of events although the source returns it for ~70%; the statistics table was empty because the feed is empty before a match.
- **Decision:** sub-games (periods and per-stat groups) are fetched by default and stored under a scope (`QUARTER_n`, `FIRST_HALF`, `SECOND_HALF`, `STAT_<NAME>[__<PERIOD>]`); every odds row carries `subject` (MATCH/HOME_TEAM/AWAY_TEAM, totals ladders only) and `period` (FULL_TIME/HALF_n/QUARTER_n/PERIOD_n) from one vocabulary (`src/sites/betb2b/labels.py`); H2H periods use QUARTER_n/HALF_n/OVERTIME_1 and a missing score stays empty (never filled with 0); a `coverage` table records, on change only, `offered | not_offered | not_attempted | fetch_failed` per subject x period, and for `h2h`, `stat_id`, `result`, `result_periods`, `match_stats`; played matches get final + per-period scores and team/player statistics (`match_stats`, `player_stats`) from a post-match pass; matches the source never resolves within a week are marked `result_status = -1`. Both stores (SQLite and ORM/Postgres) implement all of it.
- **Consequences:** a gap now means something; do not omit rows or switch a step off because it returns nothing — find out why (the statistics feed needed a post-match pass, not removal). New datasets get a coverage row. H2H history is not per-bookmaker and is stored once across skins; odds are per skin.

---
## ADR-4: Skip what is already stored, and remember the source's "no data" (2026-10-04)
- **Status:** accepted
- **Context:** re-scrapes re-probed every event (in-scrape H2H/stat-id steps, the stat-id backfill), doubled the H2H history, dumped hundreds of events of JSON to the terminal, and a hard timeout discarded a whole pass.
- **Decision:** a stored match is not fetched again by default (`--refetch` / `--skip-processed SECONDS` override; live scrapes are never filtered); a stored match whose totals coverage is `fetch_failed`/`not_attempted` is fetched again at most hourly; H2H and stat-id probes skip events that already have the data or got a "no data" answer in the last 24 h (`probe_state`, `probe_filter`); a re-scrape stores each H2H game once per result; a timeout keeps the events already fetched and reports the rest as failed ids; `scrape` prints a short summary (`--json` / `--output FILE` for the data).
- **Consequences:** odds of stored matches do not refresh (and line movement does not accumulate) unless `--skip-processed SECONDS`/`--refetch`; the skip list is per match, not per skin, so another skin's own odds need `--skip-processed` (backlog B-2026-10-04-1).

