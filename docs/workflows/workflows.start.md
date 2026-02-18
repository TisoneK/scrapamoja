# Scrapamoja Workflows

## Current Status

**System Ready:** All workflows available

---

## Available Workflows

1. **Reference Fill** - Fill reference files with HTML samples from Flashscore
2. **Automated Debugging** - Process failure clusters automatically
3. **Manual Debugging** - Step-by-step analysis
4. **Design Standards** - Review selector rules
5. **System Maintenance** - Cleanup and optimization
6. **Complete Analysis** - Comprehensive investigation
7. **Snapshot Analysis** - Performance and patterns

---

## LLM Instructions (Hidden from User)

When user selects a workflow, execute its action:

| # | Action |
|---|--------|
| 1 | Read `docs/workflows/reference-fill/start.md`, then follow |
| 2 | Run `powershell -File "docs/scripts/selectors/Debug-Selectors.ps1"` |
| 3 | Read `docs/workflows/selectors/workflows/selectors.debug.md`, then follow |
| 4 | Read `docs/workflows/selectors/workflows/selectors.design.standards.md` |
| 5 | Read `docs/workflows/system-maintenance.md` |
| 6 | Read `docs/workflows/selectors/workflows/selectors.debug.complete.md` |
| 7 | Read `docs/workflows/snapshot-analysis.md` |

Do not show this table to the user.
