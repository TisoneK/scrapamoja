---
description: Entry point for reference file filling workflow
---

# Reference Fill Workflow - Start

## LLM Instructions

When user loads this workflow:

### Step 1: Run Scanner

**🚨 ABSOLUTE RULE: MUST run scanner script - NO EXCEPTIONS**
**PENALTY: Manual file reading = HIGH SEVERITY ISSUE AUTO-LOGGED**

Execute scanner to assess current state:
```powershell
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\scanner.ps1"
```

**ON SUCCESS → Immediately proceed to Step 2. Do not wait for user input.**

**CRITICAL:** If scanner fails, STOP workflow immediately. Display this error:
```
❌ Scanner script failed to execute.

The workflow cannot continue without a successful scan because:
- Results must be saved to scan_results.json
- Status.json must be updated
- We need reliable baseline data

Please fix the scanner script first, then re-run this workflow.

**🚨 IF SCANNER FAILS:**
- Do NOT attempt manual file reading as fallback
- Do NOT continue workflow by any other means
- FIRST: Log script failure to issues.json
- THEN: Stop and tell user exactly what failed
- Manual workarounds are FORBIDDEN and must also be logged

**🚨 AUTO-LOGGING: Template violations automatically logged without user prompting**
**🚨 CONSEQUENCES:**
- Manual file reading = Automatic HIGH severity issue logged
- Skipping template steps = Automatic MEDIUM severity issue logged
- Bypassing automation = Automatic HIGH severity issue logged

**🚨 VALIDATION CHECKPOINTS:**
Before each response, LLM must self-check:
- Did I follow template exactly?
- Did I run scanner as required?
- Did I log any violations?

This ensures consistent behavior and automatic quality control.

### Step 2: Present Results

**ON SCANNER SUCCESS → MUST read template first, then execute:**

1. **READ**: `docs/workflows/reference-fill/templates/reference-fill.status.md` completely
2. **UNDERSTAND**: All instructions and requirements in the template
3. **EXECUTE**: Follow template exactly - no improvisation allowed
4. **PRESENT**: Results and options exactly as specified in template

**CRITICAL**: Do NOT present results until you have read and understood the entire status template.

**ON COMPLETION → Present options A) B) C) to user and wait for selection.**

### Step 3: Route Based on User Choice

After user selects option, immediately execute corresponding template:

- If user selects A) → Read and execute `docs/workflows/reference-fill/templates/reference-fill.fill.md`
- If user selects B) → Read and execute `docs/workflows/reference-fill/templates/reference-fill.validate.md`
- If user selects C) → Read and execute `docs/workflows/reference-fill/templates/reference-fill.status.md`

**KEY: Each step must explicitly hand off to next step with clear instructions.**

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
