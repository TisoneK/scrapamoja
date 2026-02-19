# Scrapamoja Workflows

## Current Status

**System Ready:** All workflows available

---

## Available Workflows

A) **Reference Fill** - Fill reference files with HTML samples from Flashscore
B) **Automated Debugging** - Process failure clusters automatically
C) **Manual Debugging** - Step-by-step analysis
D) **Design Standards** - Review selector rules
E) **System Maintenance** - Cleanup and optimization
F) **Complete Analysis** - Comprehensive investigation
G) **Snapshot Analysis** - Performance and patterns

⚠️ GATE: Validate format before sending - MUST be lettered A, B, C...
🔍 **CRITICAL CHECK:** Are these options lettered? If not, FIX before sending.

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
