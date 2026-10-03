# Brief: run the scraper from the Kenyan machine

For an agent working on a machine whose own internet connection is in Kenya. Read
`CLAUDE.md` and `AGENTS.md` first and follow the working protocol they point to; this
brief is the task, those files are the rules. Everything below was measured or read from
the code, and where something is not verified it says so.

## 1. Why this machine, and what "done" looks like

The scraper is finished for betwinner, melbet and 22bet and runs from anywhere. **linebet**
is the exception: its website refuses non-allowed countries and, on top of that, a Gcore
"browser validation" page challenges any client that is not a real browser. From the
operator's US machine the only way in was a rented Kenyan tunnel, which is slow
(10-12 s per request) and drops. From a Kenyan connection the country block should not
apply, no tunnel is needed, and the validation can be passed once by a person and then
reused by a persistent browser profile.

Done means:
1. linebet scrapes end to end from this machine into the shared database, with the same
   data as the other skins (section 3), and it keeps working on a second and third run
   without a person present.
2. betwinner, melbet and 22bet also run from this machine and store their data per skin.
3. You report what you measured (section 9). You do not build around a block you cannot
   pass; you report it.

## 2. What already exists (do not rebuild)

- **Hybrid mode** (default, no `--direct`): a browser opens a named profile, passes the page,
  the scraper harvests its cookies, then polls the feeds over HTTP with them. linebet needs
  this mode. The other skins use `--direct` (plain HTTP, no browser).
- **Persistent browser profiles** (`src/browser/profiles/`): a named user-data directory
  (`~/.scrapamoja/profiles/<name>/`, override `$SCRAPAMOJA_PROFILE_DIR`) so cookies and a
  passed validation survive between runs. linebet uses `betb2b-linebet`. One process per
  profile (a lock); a second concurrent run falls back to a throwaway browser.
- **Block handling** (`src/security/`): every response is classified (`geo_block`,
  `js_challenge`, `captcha`, `rate_limited`, `ip_banned`, ...); each has a ladder
  (wait, real Chrome, headed Chrome, human handoff, cooldown). A site that keeps failing
  rests for 5 minutes and is refused immediately until the rest ends (you will see
  `in cooldown for N s more`). `python -m src.security status|clear|evidence`.
- **Storage**: SQLite by default, the shared Neon Postgres when `DATABASE_URL` is set.
  Event ids are shared across skins; odds are stored per skin.
- **Skip-by-default**: a stored match is not fetched again. `--refetch` fetches everything,
  `--skip-processed SECONDS` re-fetches matches stored longer ago than that. A stored match
  whose totals fetch failed is fetched again (at most hourly). H2H and stat-id probes
  remember "the source has none" for 24 hours.
- **Output**: `scrape` prints a short summary. `--json` prints everything, `--output FILE`
  writes it.

## 3. What a complete run stores

| Data | Where |
|---|---|
| Every market and odds line of the match, each quarter, each half, and per-stat groups | `odds_snapshots` (`scope`, plus `subject` MATCH/HOME_TEAM/AWAY_TEAM and `period` FULL_TIME/HALF_n/QUARTER_n for totals) |
| Which sub-games exist | `sub_games` |
| Head-to-head history with quarter scores (overtime is `OVERTIME_1`) | `h2h_games`, `h2h_period_scores` |
| What was offered / absent / never asked / failed, per subject x period, H2H, stat id, result | `coverage` |
| Final score and winner, per-quarter scores of played matches | `events` (`final_score_*`, `result_status`), `period_scores` |
| Team and player statistics of played matches | `match_stats`, `player_stats` |

A gap is meaningful: `not_offered` means the source was asked and has none, `not_attempted`
means it was never asked, `fetch_failed` means the request failed and is retried.
`result_status = -1` means the source never resolved the match within a week.

## 4. The linebet research so far

Measured, not assumed:
- The site sits behind Gcore WAAP: a country block on the website, plus a JS "browser
  validation" for non-browser clients. Plain HTTP from a flagged address returns the
  challenge page. Bare 403/406 from a feed endpoint are not blocks (406 is the known
  header rotation; the per-match `GetGameZip` endpoint is the working data path).
- On 2026-10-03, from a US machine through the operator's Kenyan tunnel, with the
  `betb2b-linebet` profile: the browser bootstrap loaded the site and harvested 11 cookies;
  **82 per-match fetches succeeded against 18 transport errors, with one Gcore challenge in
  the whole run**; a first test (writes off) returned 8 events with 1,063 markets. So
  cookies earned by a real browser were accepted on plain HTTP calls from the same
  address. The limiter was the tunnel (latency, drops), which tripped the unreachable
  guard.
- The stored run that followed got only 2 events (295 markets, every quarter, half and stat scope
  present) before the tunnel dropped again ("server disconnected", then six failures in a row and a
  5-minute rest). The unreached matches were reported as failed, nothing was lost, but the throughput
  is a tunnel limit, not a scraper or Gcore one.
- Cookies earned through the tunnel did not work from the US address directly: the
  validation is tied to the address it was earned from. Therefore: warm the profile and
  run the scraper on the **same** connection, from this machine.
- Not verified: whether the validation survives for days, or whether a changed address
  invalidates it. Measure it (section 8).

## 5. Setup

```bash
git clone https://github.com/TisoneK/scrapamoja.git && cd scrapamoja
python3 -m venv .venv && source .venv/bin/activate     # Python 3.12 or newer
pip install -e ".[dev]" && playwright install chromium
```

Install Google Chrome too if it is not there; the block ladder escalates to it.
Create `src/sites/betb2b/.env` from `src/sites/betb2b/.env.example`. Required:
`DATABASE_URL` (the operator gives it to you; it is a secret: never echo it, log it or
commit it) and `BETB2B_STORE_MODE=auto`. Useful: `BETB2B_TIMEOUT=3600`, `SCRAPAMOJA_INTERACTIVE=1`
(lets the ladder hand a challenge to a person at the screen).

**Do not set `BETB2B_PROXY_URL` (or any `BETB2B_PROXY_*`).** This machine is the allowed
country; a proxy would only add latency. Confirm: `env | grep BETB2B_PROXY` prints nothing.

Sanity check, no writes:

```bash
python -m src.sites.betb2b.cli probe --skin linebet
python -m src.security status
```

## 6. Runbook

1. **Warm the linebet profile (a person does this once).** This opens a visible browser.
   Pass Gcore's browser-validation page by hand, wait until the normal linebet page shows,
   then close the window. You cannot pass it yourself: completing a bot check is a human
   step, and no solver is to be added.
   ```bash
   python -m src.browser.profiles warmup betb2b-linebet https://linebet.com/en
   ```
   If the scrape in step 2 keeps getting challenged, warm with the installed browser instead
   (`--channel chrome`) and retry, so the warm-up and the run use the same browser.
2. **First linebet run, writes off, to see it work:**
   ```bash
   python -m src.sites.betb2b.cli scrape linebet scheduled --sport basketball --no-db --timeout 900
   ```
   Expect a summary such as `linebet list_prematch: ok - N events, M markets`. Read
   `python -m src.security status` afterwards: no active block, no cooldown.
3. **Stored linebet run** (hybrid mode, not `--direct`; start with the default concurrency,
   raise it with `BETB2B_CONCURRENCY=3` only if there are no 429/403/203 in the log):
   ```bash
   python -m src.sites.betb2b.cli scrape linebet scheduled --sport basketball --timeout 3600
   ```
4. **Second run, no person present**, to prove the profile persists: run step 3 again and
   confirm it needs no challenge handling. Repeat after an hour, and the next day.
5. **The other skins**, one after the other (plain HTTP):
   ```bash
   for s in betwinner melbet 22bet; do
     python -m src.sites.betb2b.cli scrape $s scheduled --sport basketball --direct --skip-processed 60 --timeout 3600
   done
   ```
   `--skip-processed 60` makes each skin fetch its own odds even for matches another skin
   stored. A plain run skips every stored match.

Timing: about 9 minutes for 200 matches per skin from a normal connection, around 1,500
requests, paced at about 3 requests per second on purpose.

## 7. Verify what landed

Run from the repo root (the CLI loads `.env` for you):

```bash
python - <<'E'
import sys; sys.path.insert(0, '.')
import src.sites.betb2b.cli.main
from src.sites.betb2b import store
from sqlalchemy import text
c = store.init_db()
q = lambda s: [tuple(r) for r in c.execute(text(s))]
print(q("select skin, count(distinct event_id), count(*) from odds_snapshots group by 1 order by 1"))
print(q("select dataset, status, count(*) from coverage group by 1,2 order by 1,2"))
print("duplicate h2h:", q("select count(*) from (select 1 from h2h_games group by event_id, game_id, status, score1, score2 having count(*) > 1) t"))
print(q("select scope, count(distinct event_id) from odds_snapshots where skin='linebet' group by 1 order by 1"))
E
```

linebet is healthy when it has events, the quarter and half scopes appear for the leagues
that have them, `fetch_failed` is a small share, and the duplicate count is 0.

## 8. Rules and guardrails

- **Pace**: do not raise request rates to go faster. An earlier run at roughly 20 requests per
  second made the hosts refuse this IP for about half an hour. The default pacing is
  deliberate.
- **One process per profile**: do not run two linebet scrapes at once.
- **Evasion boundary**: acceptable means real-browser fidelity, patience, and a person at the
  screen. Not acceptable: CAPTCHA solvers, TLS-fingerprint spoofing, exporting cookies to
  another machine, anything that bypasses a protection rather than passing it.
- **Secrets**: never print, log or commit `DATABASE_URL`, proxy credentials or keys.
- **Destructive commands**: `reset` and any delete need the operator's explicit instruction.
  Remember `BETB2B_STORE_MODE=mirror` makes `reset` hit the local mirror, not the shared
  database.
- **Scope**: the scraper acquires and structures data. No prediction, no engine work, and the
  engine ingest step (`--ingest`) is not part of this task.

## 9. If something fails

| Symptom | Meaning | Do |
|---|---|---|
| `block=js_challenge/gcore` repeats after a warm-up | validation not accepted or expired | warm up again with the other browser channel; note how long it lasted |
| `ERR_CONNECTION_RESET` on the home page | the connection to linebet is being dropped | check from the same machine in a normal browser; try later; report |
| `in cooldown for N s more` | the guard is resting the site after failures | wait it out; `python -m src.security clear linebet` only if the cause is fixed |
| `geo_block` | the connection is not seen as Kenyan | stop and report; do not try a different route unasked |
| 406 on a list feed | known header rotation | ignore; the per-match path is the data path |
| many `fetch_failed` coverage rows | transient request failures | re-run; stored matches with failed totals are fetched again hourly |

`python -m src.security evidence` shows what blocked requests looked like.

## 10. Report back

1. Whether the warm-up passed from Kenya, with the browser channel used.
2. Run 2, 3 and next-day results: events, markets, and whether any challenge appeared.
3. Per-skin rows from the section 7 query, and the share of `fetch_failed` for linebet.
4. How long a validated profile kept working, and what ended it if it ended.
5. Anything in the failure table that happened, with the log lines.

## 11. Out of scope

Other sports, live in-play scraping, prediction and pick generation, and the engine ingest.
If a requirement seems to pull you toward those, say so instead of building it.
