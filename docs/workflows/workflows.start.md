# Scrapamoja Workflows

## Current Status

**Main Issues Found:**
- Authentication/cookie consent failures
- Navigation selector failures (sport selection, basketball links)

**Session saved:** `docs/workflows/debug_session_20260214_223149.json`

<details>
<summary>Details</summary>
10 failure clusters processed, 0 newly fixed.
Action Required:
- Review cluster snapshots in src/sites/flashscore/selector_engine/snapshot_storage/20260214/
- Update selectors in selectors/unknown.yaml files for each cluster
- Run validation to mark fixes
</details>

---

## What do you want to fix first?

1. **[Automated Debugging](scripts/selectors/Debug-Selectors.ps1)** - Process failure clusters automatically
2. **[Manual Debugging](selectors/workflows/selectors.debug.md)** - Step-by-step analysis
3. **[Design Standards](selectors/workflows/selectors.design.standards.md)** - Review selector rules
4. **[System Maintenance](system-maintenance.md)** - Cleanup and optimization
5. **[Complete Analysis](selectors/workflows/selectors.debug.complete.md)** - Comprehensive investigation
6. **[Snapshot Analysis](snapshot-analysis.md)** - Performance and patterns

---

## Quick Commands

```bash
# Start automated debugging
./docs/scripts/selectors/Debug-Selectors.ps1

# View current failures
./docs/scripts/selectors/Debug-Selectors.ps1 -ListFailures

# Check system health
./docs/workflows/system-maintenance.md
