---
description: Entry point for reference file filling workflow
---

# Reference Fill Workflow - Start

## LLM Instructions

When user loads this workflow:

### Step 1: Run Scanner
Execute scanner to assess current state:
```powershell
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\scanner.ps1"
```

**CRITICAL:** If scanner fails, STOP the workflow immediately. Display this error:

```
❌ Scanner script failed to execute.

The workflow cannot continue without a successful scan because:
- Results must be saved to scan_results.json
- Status.json must be updated
- We need reliable baseline data

Please fix the scanner script first, then re-run this workflow.
```

DO NOT attempt manual scanning as fallback.

### Step 2: Show Results
Display scan results in table format, then STOP.

DO NOT ask questions. Wait for user response.

### Step 3: Route Based on User Choice
After showing results, wait for user to choose:
- If user wants to fill files → Read and execute `docs/workflows/reference-fill/templates/reference-fill.fill.md`
- If user wants validation → Read and execute `docs/workflows/reference-fill/templates/reference-fill.validate.md`
- If user wants status → Read and execute `docs/workflows/reference-fill/templates/reference-fill.status.md`

---

## Quick Commands

**PowerShell (Windows):**
```powershell
# Run scanner to find files needing attention
powershell -ExecutionPolicy Bypass -File ".\docs\workflows\reference-fill\scripts\pwsh\scanner.ps1"

# Run validator
powershell -ExecutionPolicy Bypass -File ".\docs\workflows\reference-fill\scripts\pwsh\validator.ps1"
```

**Bash (Linux/Mac):**
```bash
./docs/workflows/reference-fill/scripts/bash/scanner.sh
./docs/workflows/reference-fill/scripts/bash/validator.sh
```

---

## File Locations

- **Target Directory:** `docs/references/flashscore/html_samples/`
- **Template Reference:** `docs/references/flashscore/html_samples/README.md`
- **Status:** `docs/workflows/reference-fill/status.json`
- **Scan Results:** `docs/workflows/reference-fill/outputs/scans/scan_results.json`
