# Session 50 notes — dead ends and detail not worth promoting

- **Provider/hosting detours.** Railway subscription ended; Vercel considered for running the scraper (rejected: serverless, no long-running worker) and for the DB (only via a Postgres marketplace integration); Neon free chosen (1 GB, 100 compute-hours, scale-to-zero). A Neon "Functions" quickstart (`neon deploy`, a hello function) was pasted by the operator and deliberately NOT run — irrelevant to storage and outward-facing. Neon Data API URL/token placeholders added to `.env`; the scraper doesn't use them.
- **Proxy investigation.** linebet returned a Gcore "Browser Validation" JS challenge to plain HTTP clients from both the dev IP and the Kenya proxy while 22bet/melbet/betwinner returned JSON; a real browser (the in-app one) passed the challenge in ~8 s from the same IP; the scraper's headless Chromium did not. Earlier ledger entries already say the block is IP/behaviour-based, not geographic, and that direct-from-an-allowed-IP works. The bore.pub tunnel needed the NEW port and the CURRENT credentials (the saved ones answered 407); later it answered 502 and the operator ruled proxies out for API calls ("used when bypassing the website, not the API").
- **Cause of "only 1/3 of discovered ids return an event" — NOT established.** Throttling was the first theory; the retry step never fired on a run that saved 103 of 235, so those were server answers with no usable event. Relisted/stale ids explain some (the old id returns nothing). Needs a live sample.
- **Mistaken claims corrected mid-session:** (1) "event ids are identical across skins" — mostly, not always (ADR-27); (2) "the sub_games table doesn't store sub-game ids" — it does (`sub_game_id`), I queried the wrong column; (3) "`.env` exists in the repo root" — it didn't; the `.env` printed by `git check-ignore` was the path, not a file.
- **Auto-mode blocked a bulk wipe** of the Neon store + local mirror; the operator ran the identical command in their own terminal (14 tables, 0 rows confirmed in the Neon dashboard). A narrower cleanup (10 junk events) the operator approved explicitly went through.
- **Automated ADR strip:** regex pass kept rationale but produced six grammar breakages (`retires's`, `the's market`, stray `)`, `(backlogged —)`, `(addendum)`, `(point 3)`) — all caught by reviewing the whole diff, not by tests (comments don't fail tests).

Promoted: ADR-26, ADR-27, inefficiencies entries, backlog rows, preferences, flaws entry. Nothing else needs to survive.

## Follow-up: Gcore WAAP research (linebet)
- Web search/fetch tools were unavailable (their backend errored), so the docs were read directly: the in-app browser on `docs.gcore.com`, and the public docs repo `g-core/product-documentation` via the GitHub trees API + raw files (`waap/waap-policies/anti-automation-and-bot-protection.mdx`, `waap/threat-intelligence/tls-fingerprinting.mdx`, `waap/frequently-asked-questions/javascript-injection.mdx`, `waap/waap-rules/advanced-rules*.mdx`). Detail is in ADR-28.
- Operator's observation (validated once per browser; new tab no re-validation; other browser re-validates) = cookie + fingerprint per browser profile.
- Seen in the in-app browser: validation page → `/en/block` "not available in your country" (US, 135.180.70.225). Earlier the feed URL (not the website) passed the same validation and returned JSON in that browser.

## Open-items round (after Session 51)
- Order worked: B-11 guard direct calls → B-13 no-browser rungs → B-14 probe → B-2 shared rest/budget → live run → pacing → B-6 reset → B-7 docs. B-12 (needs an allowed-country egress + the operator) and the proxy pool were not done.
- Dead end avoided: a first idea was to treat every transport failure as a whole-skin rest; the live run showed the optional statistics service timing out while the odds feed was fine, so failures got a `scope` (stats) and in-flight failures stopped doubling the rest.
- Tests initially "passed first time" — checked by running them against the OLD scraper (they failed there), so they test the change.
- The live run was on the code BEFORE the scoped-rest and pacing fixes; its log is the evidence for ADR-30. Afterwards all three hosts refused TCP connections (connect time 0) — not a challenge page and not a timeout on a slow answer.

## Diagnosis round ("find out why it's blocking")
- Method: DNS (each host = ONE IP, no CDN) → raw TCP `connect()` per port with a 4 s timeout → ipinfo ownership of the IPs. No HTTP traffic to the sites, to avoid prolonging a drop.
- Result table at ~13:30Z: betwinner 443/80 DROPPED; melbet 443 DROPPED / 80 open; 22bet 443 open (recovered); linebet open. Owners: Melbikomas UAB; Redstart Group x2; G-Core Labs (linebet only).
- `bore` log pasted by the operator showed the tunnel crashing ("frame error, invalid byte length") after repeated bursts of ~12 simultaneous new connections through it — the browser path opens many parallel connections; worth remembering when sizing anything that goes through bore.
- The operator's phrasing "proxy is still up" was based on the pasted log; the port was refused 36 minutes after its last line. Check with a connect() before relying on it.
