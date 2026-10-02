# Changelog

All notable changes to Scrapamoja. Format loosely based on [Keep a Changelog](https://keepachangelog.com/).
Technical detail lives in the agent session reviews kept with the project's agent memory;
this file is the plain-language public record.

## [Unreleased]

### Added — blocked and failed requests now leave evidence automatically (2026-10-02)

Working out why a site was dropping or challenging us took hand-made probes,
because the existing snapshot tooling only recorded successful runs (and, in
browser mode, page snapshots) and nothing for the direct requests the scraper
actually makes. Now, every challenge page, geo block, ban, timeout or dropped
connection is recorded the moment it happens, in the snapshot system's own
compact, redacted format (what the response said, which provider's page it was,
which exception, how often). Identical failures are stored a few times and then
only counted; old days are deleted after a week. Read it with
`python -m src.security evidence` (`--days`, `--site`, `--tail`). Scraping
outright and placeholder listings that are skipped are recorded too. The
snapshot folder no longer grows without limit: only the newest 20 results per
site and action are kept (`BETB2B_KEEP_RESULT_SNAPSHOTS`), and runs that found
nothing new are not dumped.

### Fixed — about 85 modules that could not be loaded at all now load (2026-10-02)

A check that tries to load every module found that roughly a hundred of them
failed on startup, so features built on them (navigation, the selector
dashboard API, telemetry storage and reporting, the plugin permission system,
several resilience tools) could never have run. The causes were ordinary:
names used without being imported, import paths with the wrong number of
dots, classes defined but not exported from their package, a field order a
data class does not allow, a repeated argument in the plugin permission
definitions (a hard error on its own), and dashboard routes that declared a
service object as a web query parameter. All of those are fixed, and the
dashboard API now starts and answers requests. The few that remain need a
design decision (for example the abort-handling classes that other code
imports but nobody wrote) and are listed, with reasons, in a test that fails
if any new module stops loading or a listed one starts working.

Scraping also no longer fetches season-long outright markets (such as "NBA
2026/27 MVP") or generic "Home (Points) / Away (Points)" listings: they were
requested on every run and never became matches, about a quarter of all
requests.

### Changed — no country is special: wording and default labels made neutral (2026-10-02)

Docs, comments, examples and the skin files described one country as if it
were the way in. Any allowed-country connection that the site has not
penalised works; the tunnel's exit country is incidental. The proxy label in
the skin files, the examples, and the `validate_live` script's default is now
`proxy` instead of a country name (it is only a label, and the command line
already used `proxy`; if you set `BETB2B_PROXY_ID` yourself nothing changes).

### Added — the scraper now tells blocks apart and answers each properly; persistent browser profiles (2026-10-02)

A website that turns us away is now recognised for what it is — a country block,
a JavaScript browser check (Gcore, Cloudflare), a CAPTCHA, a rate limit, a ban or
an expired session — instead of every refusal triggering the same "start the
browser again". Each kind has its own response: wait for a self-clearing check, retry in a
more browser-like way (real Google Chrome, then a visible window), ask a person to pass
it once, switch to a backup skin, or rest the site for a while. Resting persists across
runs, so a fresh run no longer walks straight back into a site that just blocked the last
one. A country block is reported as such: no browser setting changes the country a request
comes from. `python -m src.security status` shows where every site stands.

The browser can now keep a **profile** between runs (`~/.scrapamoja/profiles`), so a check
passed once is remembered. `python -m src.browser.profiles warmup <name> <url>` opens a visible
window to pass a check by hand. The betb2b scraper uses one profile per skin
(`BETB2B_PROFILE=off` restores a fresh browser each run).

### Changed — scrapes are saved on your machine by default, and matches are scraped once (2026-10-02)

Every scrape now saves its results into the local database file
(`data/betb2b/odds.db`, or wherever `BETB2B_DB_PATH` points) without having to
ask; `--no-db` turns that off. Setting `DATABASE_URL` to any hosted Postgres
makes the same runs read and write a shared database instead, so several
machines can work from one store. A match that is already stored is no longer
fetched again (add `--skip-processed SECONDS` to allow a refresh after that
long), matches that have already started are left to the live scrape, and
finished matches get their final score recorded after each run.

Defaults can now live in a local, untracked `src/sites/betb2b/.env` file:
the skin, sport, action, request limits, retry settings and a list of backup
skins.

### Fixed — a struggling or blocking site is left alone, by every part of the scraper (2026-10-02)

The statistics, head-to-head, final-score and landing-page requests used to
ignore the protection the rest of the scraper respects, so one challenge page
could be fetched and mis-read once per match. They now share the same rules:
a challenge stops the batch with one message and puts the site on a rest
period. In the no-browser mode a challenge goes straight to resting (or the
backup skins) instead of being retried silently. A site that simply stops
answering (timeouts, dropped connections) is rested after a run of such
failures — default six in a row, five minutes, doubling — and an optional
per-hour request cap is available (`BETB2B_HOURLY_BUDGET`). `probe` now says
honestly when no cookies were obtained.

Requests are now also paced per second (default 3 a second to one site, across
all workers; `BETB2B_MAX_RPS`). Limiting how many requests run at once was not
enough: on a fast site four workers still sent about twenty a second, and the
sites answered by cutting this machine's connection off for a while. A slow
optional service (match statistics) that stops answering rests only itself, not
the odds feed, and requests already in flight when a rest begins no longer
extend it.

### Added — a guarded `reset` command (2026-10-02)

`betb2b reset` shows the target and how many rows it holds and deletes nothing
unless `--force` is given. `--scope all` (default) empties every table but
keeps the structure; `--scope facts` clears only odds, states, head-to-head and
run history. On a shared remote database, `--also-local` clears the local copy
and its replay queue too, so the queue cannot refill what was just deleted.

### Fixed — fewer silent gaps, no junk matches (2026-10-02)

- A match request that times out or is blocked is now retried with a short
  wait, can be tried on another brand's site, and is reported instead of being
  quietly counted as "no data". Parallel requests default to 4 instead of 8.
- A run against a blocked or unreachable site is recorded as failed, not as a
  successful run with no events.
- The bookmaker sometimes lists the same match again under a new number. The
  old entry is now linked to the newer one rather than looking like a second
  match. Quarter, half and special-bet listings and the generic
  "Home (Points) / Away (Points)" entries are no longer stored as matches.
- Each match's statistics-feed id is now kept, so its final score can be
  matched up later.

### Added — the scraper can now reset its own history when the database is over the limit (2026-09-08, session 44 cont.)

The size watch described below deletes old odds history gradually, which
prevents the database from growing into the hosting limit — but it cannot
quickly shrink a database that is already past it. When the watch finds the
database over the hard limit, it now performs a full reset of its history in
one step (match results and reference data are always kept) — the same
manual emergency procedure the operator previously had to run by hand, now
executed automatically. While the database is locked by the provider, every
attempt simply waits; the reset completes itself the moment the lock lifts.
The check runs every 10 minutes instead of hourly while over the limit, and
the same reset is available as a deliberate command-line action. Set an
environment variable to require a human for this step instead.

### Added — the scraper now watches the database size and trims old data before hitting the hosting limit (2026-09-08, session 44)

Twice now the free hosting tier has locked the shared database to read-only
because it silently grew past the size limit. The scheduled scraper now runs an
hourly check that reads the database's real size straight from the server (the
same number the hosting dashboard shows). It logs a clear warning once the store
passes 80% of the limit, and past 92% it automatically deletes odds history for
matches older than a week (their final scores are kept) — so the store stops
growing into the wall instead of waking up locked one morning. The same check is
available on demand from the command line, including a dry-run that reports how
much could be trimmed and a preview of what would be deleted. All thresholds are
tunable by environment variables; the monitor never touches final results.

### Added — the scraper keeps collecting when the shared database is unavailable (2026-09-07, session 43)

The scheduled scraper now survives the shared database going down or being
locked. When the free hosting quota locks the database to read-only — or it
can't be reached at all — the scraper used to simply stop saving data and wait.
It now switches to a local fallback database on the machine it runs on, keeps
writing there, and remembers every write it made in a replay queue. It
periodically checks whether the main database accepts writes again; the first
check that succeeds switches collection back and replays everything that was
queued, so no scrape results are lost during an outage or a quota restriction.
The switch, the recovery, and how much is queued are all logged. Set
`BETB2B_FALLBACK=0` to turn the behavior off and get the old fail-loudly
instead.

### Fixed — the always-on scraper boots with live-odds polling OFF again (2026-09-07, session 42)

The scheduled scraper worker on Railway was accidentally re-enabled to poll live
(continuously changing) odds every 15 seconds — the mode that filled the shared
database past the free hosting quota in August. When the low-storage default was
introduced, only one of the two launch configurations was updated, so the worker
service kept booting with live polling on. Both launch configurations now default
to scheduled-only (pre-match odds every 3 hours + final results every 10 minutes);
a new test fails if either config ever ships with live polling on by default.
The deploy guide no longer instructs enabling live polling, and warns that
variables set in the Railway dashboard override the config-file defaults — a
stale dashboard variable can silently re-enable live polling.

### Added — shared PostgreSQL store foundation (2026-07-25, session 29)

The data store can now move from per-file SQLite databases to a single shared
PostgreSQL database (Railway plugin), so the scraper, the prediction engine,
and the apps can all read from one place through the Python/FastAPI layer.

- **One database connection layer.** A new shared module resolves the database
  from the `DATABASE_URL` environment variable: when set, the app talks to
  PostgreSQL (the deployed setup); when unset, it falls back to the local
  SQLite files. Existing local runs and tests keep working unchanged.
- **PostgreSQL driver and a migration tool.** Added `psycopg` (the Postgres
  driver) and `alembic` (schema migrations — the project had none). The first
  migration creates every table in the consolidated store in one stream.
- **Portable schema for the betting data.** The betb2b odds/stats schema is now
  declared as database-agnostic models (was SQLite-only raw SQL): booleans for
  flags, timezone-aware timestamps, auto-incrementing keys that work on both
  databases. The hot query paths (latest odds per event, events by start time)
  now have dedicated indexes.
- **One-time data copy tool.** A script moves existing rows from the old SQLite
  files into the new shared database, for the production cutover.

### Notes
- The live scraper still writes betting data through its original SQLite path
  for now; the shared-Postgres write path is the next step (operator-side,
  needs the Railway database provisioned).
- Local development and tests continue to use SQLite automatically — no setup
  change required for contributors.
