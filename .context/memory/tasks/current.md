# Current Task (overwrite each session)

> **NEXT AGENT: Run live betb2b e2e validation (PENDING).**

## ⚡ Immediate Task — Live E2E Validation

**This is the top priority for the next session.** The telemetry and snapshot systems
are now wired into the betb2b scraper (see wiring status below). The scraper itself
(DOM fallback, hybrid mode) has NOT been live-tested since Session 12's initial build
and Session 14's DOM-extraction wiring. Session 13 diagnosed the 406 drift but no
subsequent session has run the actual `validate_live` script against a real site.

### What to run

```bash
cd scrapamoja && \
  BETB2B_PROXY_URL=http://bore.pub:55068 \
  BETB2B_PROXY_USER=TisoneK \
  BETB2B_PROXY_PASS=Taalib01 \
  BETB2B_PROXY_COUNTRY=KE \
  BETB2B_PROXY_ID=kenya \
  python -m src.sites.betb2b.scripts.validate_live --skin linebet
```

**Proxy:** `bore.pub:55068` (updated from the old `bore.pub:1074` which was down).
**Credentials:** user=`TisoneK`, pass=`Taalib01`.

### Expected outcomes

- **If API 406 → DOM fallback:** `list_live`/`list_prematch` should fall back to DOM
  extraction per ADR-4. Check that `events` come back non-empty and
  `raw_endpoint="dom"`.
- **If API succeeds (unlikely but possible):** events extracted from the terse-key JSON.
- **If 0 events AND 0 captures:** check proxy connectivity (egress must be KE), Cloudflare
  WAF 203 redirect, or session-harvest failure.
- **Telemetry output:** verify `data/telemetry/betb2b/linebet_*.json` files are written
  with bootstrap/poll/extract/scrape_complete phases.
- **Snapshot on error:** if any phase fails with `snapshot_on_error=True` (default), verify
  a snapshot JSON or HTML artifact appears in `data/telemetry/betb2b/snapshots/`.

### Troubleshooting

- **0 events but >0 captures:** inspect `raw_capture_captures.json` for schema drift.
- **Proxy down:** ask the operator for a new bore.pub port; update env vars.
- **DOM selectors miss events:** capture page HTML, tune `[class*=...]` selectors in
  `src/sites/betb2b/extraction/dom.py`.

## Wiring Status (as of this session)

| Subsystem | Status | Notes |
|-----------|--------|-------|
| **Telemetry** | ✅ Fully wired | `BetB2BTelemetry` in `telemetry_integration.py`, called from `scraper.py` at every lifecycle point. JSON file output, auto-flush, customizable. |
| **Snapshot** | ⚠️ Error-path only | `capture_error_snapshot()` in telemetry triggers `SnapshotManager` on failures. No success-path / periodic snapshots yet. |
| **DOM extraction** | ✅ Wired as fallback | `extraction/dom.py` called by `scraper.py` on API 406/failure (ADR-4). Untested live. |
| **API extraction** | ✅ Wired as primary | `extraction/rules.py` terse-key JSON → Event/Market/Selection. Best-effort per ADR-4. |
| **Session harvest** | ✅ Wired | `session.py` bootstraps browser through proxy, harvests ~21 cookies. |

## Other open items
- **Per-skin `partner`/`gr` confirmation pending** for melbet/betwinner/22bet/megapari/
  888starz/helabet/paripesa (linebet's `partner=189`/`gr=650`/`country=87` are
  verified-true; the other 7 ship `partner=1`/`gr=1` placeholders — not a blocker,
  just returns the wrong affiliate skin). Bootstrap each through the proxy, read
  `partner`/`ref`/`gr` off the SPA's `bff-api/config/group/get?...` call, patch the YAML.
- **Success-path snapshots** (future): add periodic DOM snapshots on successful scrapes
  + diff-based drift detection across sessions.
- **Pre-existing UI issues:** no `.eslintrc` in `ui/app` (`npm run lint` fails); `tsc --noEmit`
  has ~33 errors (unused imports/vars, field mismatch); `npm run build` fails even though
  `vite build` alone succeeds.
- **Credential hygiene:** a bore.pub proxy password and a GitHub PAT were pasted into
  chat in Session 14 — rotate when convenient.

## Context pointers
- ADR-3/ADR-4 in `plans/decisions.md` — extraction mode history (hybrid → DOM-primary).
- `src/sites/linebet/RECON.md` — recon the betb2b scraper generalizes from.
- `src/sites/betb2b/README.md` — operator guide.
- `AGENTS.md` — updated telemetry/snapshot wiring status.
- `agents/sessions.md` — Sessions 12–17 have the full build/fix/wiring log.