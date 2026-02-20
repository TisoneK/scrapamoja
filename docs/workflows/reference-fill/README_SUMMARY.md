# Reference Fill Workflow - Summary

## Purpose

Fill reference files in `docs/references/flashscore/html_samples/` with HTML samples from Flashscore for selector development and testing.

## Workflow Architecture

```
start.md (Entry Point)
    │
    ├── Step 1: Run Scanner (scanner.ps1)
    │   └── Scans html_samples/ directory → outputs/scans/scan_results.json
    │
    ├── Step 2: Present Results (formatting only)
    │   └── Uses status template for display format
    │
    └── Step 3: Route Based on User Choice
        ├── A) Fill Files → reference-fill.fill.md
        ├── B) Validate → reference-fill.validate.md
        └── C) Status → reference-fill.status.md (full execution)
```

## Modes

| Mode | Template | Purpose |
|------|----------|---------|
| **Fill** | `reference-fill.fill.md` | Collect HTML samples from Flashscore and populate reference files |
| **Validate** | `reference-fill.validate.md` | Check template compliance and HTML quality |
| **Status** | `reference-fill.status.md` | Display progress metrics and file status |

## Fill Mode Flow

0. **Mode Entry** → Confirm fill mode is active. Status template control flow is inactive.
1. **Check Status** → Read `status.json` for completed files
2. **Select File** → Present prioritized file list (A, B, C...)
3. **Verify Status** → Run scanner on selected file
4. **Ask Questions** → Collect URL, Country, League, Teams, HTML (one at a time)
5. **Validate & Generate** → Check for mismatches, save file
6. **Update Status** → Run `status_updater.ps1`
7. **Next File** → Repeat from Step 2

## File Structure

```
docs/references/flashscore/html_samples/
├── scheduled/basketball/     # Not-started matches
│   ├── primary_tabs.md
│   ├── match/secondary.md, tertiary.md
│   ├── odds/secondary.md, tertiary.md
│   ├── h2h/secondary.md, tertiary.md
│   └── standings/secondary.md, tertiary.md
├── live/basketball/          # In-progress matches
└── finished/basketball/      # Completed matches
```

## Current Status (from scanner)

- **Total Files:** 27
- **Complete:** 12
- **Need Fill:** 13
- **Unknown:** 2

## Key Rules

1. **Lettered Options** → User choices use A, B, C...
2. **Numbered Steps** → Procedural steps use 1, 2, 3...
3. **Gates** → Wait for user input before proceeding
4. **Issue Logging** → Log corrections/redirects to `issues.json`
5. **Scope Guards** → Templates only execute control flow when directly invoked.
   Reading a template for formatting reference does not activate its options/gates.

## Bug Fix History

### 2026-02-20: State Collapse Bug

**Issue:** Agent was re-executing status template's A/B/C options when entering fill mode, causing workflow to loop back to status selection instead of proceeding with file filling.

**Root Cause:** `start.md` Step 2 told agent to "execute" the status template, which loaded its control flow (including A/B/C gate with aggressive enforcement language) into active context. When fill mode triggered a status-like display, the agent pattern-matched to the status template's control flow.

**Fixes Applied:**
1. `start.md` Step 2: Changed "execute template" to "use for formatting only"
2. `reference-fill.status.md` Section 6: Added scope guard to skip options when template is read for formatting
3. `reference-fill.fill.md`: Added mode boundary marker at top
4. `reference-fill.fill.md` Step 3: Changed biased example to placeholder format

---

*This document is a living reference. Update as the workflow evolves.*
