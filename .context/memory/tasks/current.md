# ✅ Done — Session Complete

> **Cross-skin H2H investigation — paripesa domain fix (5/8 skins working)**

## Session Results

### H2H Endpoint: 5/8 Skins Working from Kenya

| Skin | Status | Fix applied |
|------|--------|-------------|
| linebet | ✅ Working | — |
| betwinner | ✅ Working | — |
| helabet | ✅ Working | — |
| 22bet | ✅ Working | Timing-sensitive bootstrap (30-90s). Not a code issue. |
| paripesa | ✅ Working | **`paripesa.bet` → `paripesa.cool`** in YAML (`.bet` redirects to bonus page) |
| 888starz | ❌ Blocked | Geo-blocked from Kenya (ERR_CONNECTION_TIMED_OUT). Needs proxy. |
| megapari | ❌ Blocked | Same as above. |
| melbet | ❌ Blocked | Same as above. |

### Key Discovery
- All 5 working skins return **identical H2H data** (19 games, 12 teams) — confirms fully shared BetB2B backend
- paripesa correct domain is **`paripesa.cool`** (not `.bet` or `.com`)
- 22bet works but is timing-sensitive (bootstrap 30-90s)

### Next Steps
- Investigate proxy for 3 blocked skins (888starz, megapari, melbet)
- Wire H2H data into the BetB2B scraper (markets enrichment)

  but not odds/scores cells. Need selector tuning for the rendered Vue grid structure.
- **406 API drift confirmed** — all feed polls return HTTP 406, confirming ADR-4's DOM-primary path.
- **paripesa** boots fine but finds 0 basketball events — may need investigation.

### Validation Data
All summaries in `data/betb2b_validate_{skin}_{sport}/summary.json`:
- `betb2b_validate_linebet_basketball/` (v1)
- `betb2b_validate_linebet_basketball_v2/` (v2)
- `betb2b_validate_linebet_football/`
- `betb2b_validate_helabet_basketball/`
- `betb2b_validate_megapari_basketball/`
- `betb2b_validate_melbet_basketball/`
- `betb2b_validate_betwinner_basketball/`
- `betb2b_validate_888starz_basketball/`
- `betb2b_validate_paripesa_basketball/`
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