# In Progress — Match-Level API Extraction Gaps

**Session 19 — 2026-07-20 — GitHub Copilot / DeepSeek V4 Flash Free**

## Task
Wire `SC.PS[]` (period scores) extraction from GetGameZip API responses into the `Event` dataclass. Update `.context/memory/` files to record the session.

## Status
- ✅ `PeriodScore` dataclass, `period_scores` field on `Event`, `_extract_period_scores()` in `rules.py`
- ✅ 29 tests passing (2 new period_score tests)
- ✅ `compare_match.py` gap flags updated
- ⬜ `.context/memory/` updates, commit & push pending

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