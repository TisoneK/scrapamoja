# Current Task (overwrite each session)

> **⚠️ READ FIRST (Session 16): protocol-compliance correction — no code changed.**
> The prior two sessions in this same conversation (14, 15) skipped `.context/kickoff.md`
> Entry Steps entirely: never ran `context-sync verify/status`, never read this
> directory before acting, never loaded the protocol edition, no session-log entries,
> no review reports, and used the wrong git commit identity (`Claude
> <noreply@anthropic.com>` instead of `Tisone Kironget <tisonekironget@gmail.com>` per
> `user/preferences.md`). This session backfilled honest Session 13–15 entries in
> `agents/sessions.md` and fixed the commit identity going forward. **Two already-pushed
> commits violate the "two surfaces, never one commit" rule** — `30f8c0f` (mixed
> `current.md` into a `feat(betb2b):` commit) and `f53b1df` (mixed `current.md` with
> stray `ui/app/dist/` build artifacts). Not rewritten (shared, already-pushed history) —
> see the Session 16 entry in `sessions.md` for full detail. **Going forward: project
> and `.context/` changes always get separate commits.**

**NEXT: live-validate the DOM fallback wired in Session 14.** Run `validate_live`
(command below) through the Kenya proxy. Expect `list_live`/`list_prematch` to 406
(per Session-13 finding) and then fall back to DOM — check the result's `events` come
back non-empty and `raw_endpoint="dom"`. If DOM selectors in `_PAGE_SCRIPT` (in
`src/sites/betb2b/extraction/dom.py`) miss real events, capture a page screenshot/HTML
dump and tune the `[class*=...]` selectors against actual markup.

```bash
cd scrapamoja && \
  BETB2B_PROXY_URL=http://bore.pub:1074 \
  BETB2B_PROXY_USER=TisoneK \
  BETB2B_PROXY_PASS=<rotated-password> \
  BETB2B_PROXY_COUNTRY=KE \
  BETB2B_PROXY_ID=kenya \
  python -m src.sites.betb2b.scripts.validate_live --skin linebet
```

Expected: writes a summary + per-action captures to
`download/betb2b_validate_linebet/` and prints `DONE: <N> events, <M> captures from
skin=linebet.`

- **If 0 events but >0 captures:** inspect `raw_capture_captures.json` for schema
  drift; `lookup_market` degrades gracefully to `G=<g_id>`/`T=<t_id>` labels, but
  unknown `E[]`/`AE[]` shapes yield zero markets.
- **If 0 events AND 0 captures:** check `summary.json` → `steps[]` →
  `step="verify_proxy"` for egress country (must be KE), and `session_harvested` under
  `list_live` (False → bootstrap raised, likely geo/WAF 203→`/en/block`).
- **If `bore.pub:1074` is down:** ask the operator to re-run the tunnel and send the
  new port; update the env vars above.

## Other open items
- **Per-skin `partner`/`gr` confirmation pending** for melbet/betwinner/22bet/megapari/
  888starz/helabet/paripesa (linebet's `partner=189`/`gr=650`/`country=87` are
  verified-true; the other 7 ship `partner=1`/`gr=1` placeholders — not a blocker,
  just returns the wrong affiliate skin). Bootstrap each through the proxy, read
  `partner`/`ref`/`gr` off the SPA's `bff-api/config/group/get?...` call, patch the YAML.
- **`ui/app` Dependabot alerts:** resolved 46→0 in Session 15 (`npm audit fix` +
  lockfile resync + a `@typescript-eslint` 6→8 bump). Verified clean.
- **Pre-existing, unrelated to the above, not yet fixed:** no `.eslintrc` exists in
  `ui/app` (`npm run lint` fails outright); `tsc --noEmit` has ~33 errors (unused
  imports/vars, a `flagged_at`/`flagged` field mismatch in `FailureDashboard.tsx`,
  missing test-lib types) — since `build` is `tsc && vite build`, `npm run build`
  currently fails even though `vite build` alone succeeds.
- **Credential hygiene:** a bore.pub proxy password and a GitHub PAT were pasted into
  chat in Session 14 — rotate when convenient.

## Context pointers
- ADR-3/ADR-4 in `plans/decisions.md` — extraction mode history (hybrid → DOM-primary).
- `src/sites/linebet/RECON.md` — recon the betb2b scraper generalizes from.
- `src/sites/betb2b/README.md` — operator guide.
- `agents/sessions.md` — Sessions 12–16 have the full build/fix/correction log.
- `reviews/2026-07-18-betb2b-base-scraper-build.md` — Session 12 review.
- `reviews/2026-07-19-session16-protocol-compliance-failures.md` — full itemized
  list of Session 14–16 protocol violations (wrong commit identity, surface-mixing,
  skipped Entry Steps, missing registry entries) — read before assuming this repo's
  process has been followed correctly in recent history.
