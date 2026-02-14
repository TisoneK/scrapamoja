---
description: Debug selector failures using snapshot observability
---

# Selector Debugging Workflow

**Owner:** Snapshot System  
**Scope:** Selector Engine  
**Applies To:** All supported sites  
**Last Reviewed:** 2026-02-14  
**Status:** stable

## Purpose

Prevents stale procedures, establishes responsibility, and supports auditability through standardized selector debugging processes.

## Steps

1. **Analyze Snapshot Artifacts**
   - **Selector Engine Failures**: `data/snapshots/<site>/selector_engine/<timestamp>/`
   - **Flow-Level Failures**: `data/snapshots/<site>/flow/<timestamp>/`
   - **Browser Session Issues**: `data/snapshots/<site>/browser_sessions/<timestamp>/`
   - Review metadata.json for failure context
   - Inspect HTML for actual DOM structure
   - Check screenshots for visual state
   - Review console logs for errors

2. **Classify Failure Type**
   - `selector_not_found`: Target element absent
   - `blocked`: Element present but inaccessible (cookie consent, overlays)
   - `timeout`: Selector resolution exceeded time limit
   - `multiple_matches`: Too many elements found
   - `invalid_selector`: Syntax or structure errors
   - `timeout`: Element exists but resolution timed out
   - `layout_shift`: DOM structure changed
   - `blocked`: Content hidden by overlay
   - `stale_dom`: Selector references outdated structure

3. **Update Selector Strategy**
   - Use captured HTML as test input
   - Prefer stable attributes over dynamic classes
   - Add fallback hierarchy for robustness
   - Document change rationale

4. **Validate and Record**
   - Test updated selector against snapshot HTML
   - Record selector evolution metadata
   - Track performance metrics over time

## Quick Debug Workflow

### Step 1: Find Recent Failures

```bash
# Check if snapshots directory exists
if not exist "data/snapshots/" (
    echo "❌ No snapshots directory found"
    echo "Please run scraper first to generate failures"
    exit /b
)

# Detect available sites
echo "Available sites:"
ls data/snapshots/

# Find most recent date directory (works for any site)
for /f "delims=" %%i in ('dir /od /b data/snapshots/*/selector_engine/snapshot_storage/* 2^>nul ^| findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$"') do set LATEST_DATE=%%i
if "%LATEST_DATE%"=="" (
    echo "❌ No failure snapshots found"
    echo "Run scraper to generate selector failures"
    exit /b
)

echo "Using latest date: %LATEST_DATE%"

# Check all snapshot types for failures
echo "Checking selector_engine failures:"
ls data/snapshots/*/selector_engine/snapshot_storage/%LATEST_DATE%/failure_* 2>nul

echo "Checking flow failures:"
ls data/snapshots/*/flow/%LATEST_DATE%/failure_* 2>nul

echo "Checking browser_session failures:"
ls data/snapshots/*/browser_sessions/%LATEST_DATE%/failure_* 2>nul
```

### Step 2: Analyze Specific Failure

```bash
# Get current date and site (from Step 1)
set SITE=<site_name_from_step1>
set DATE=%LATEST_DATE%

# For selector engine failures
cd "data/snapshots/%SITE%/selector_engine/snapshot_storage/%DATE%/<timestamp>/"
if not exist "metadata.json" (
    echo "❌ No metadata.json found in failure directory"
    echo "Check directory path and try again"
    exit /b
)
type metadata.json

if exist "html/fullpage_failure_.html" (
    echo "Analyzing HTML structure..."
    type html/fullpage_failure_.html | findstr /c:"selector_pattern"
) else (
    echo "❌ No HTML file found in this failure"
)

# For flow-level failures  
cd "data/snapshots/%SITE%/flow/%DATE%/<timestamp>/"
if exist "metadata.json" (
    type metadata.json
    if exist "html/fullpage.html" (
        type html/fullpage.html | findstr /c:"target_element"
    )
)

# For browser session issues
cd "data/snapshots/%SITE%/browser_sessions/%DATE%/<timestamp>/"
if exist "metadata.json" (
    type metadata.json
    if exist "html/page.html" (
        type html/page.html | findstr /c:"navigation"
    )
)
```

### Step 3: Update Selector

```bash
# Edit selector file
notepad src/sites/flashcore/selectors/navigation/sport_selection/<selector>.yaml

# Add more specific primary selector
# Increase timeout and retry count
# Document known blockers
```

### Step 4: Validate Fix

```bash
# Use dynamic paths from previous steps
cd "data/snapshots/%SITE%/selector_engine/snapshot_storage/%DATE%/<timestamp>/"

# Test selector against snapshot
if exist "html/fullpage_failure_.html" (
    findstr /c:"selector_pattern" html/fullpage_failure_.html
    if %errorlevel% equ 0 (
        echo "✅ Selector validation PASSED"
        # Mark as fixed if successful
        echo "status: FIXED" > snapshot_status.txt
        echo "✅ Snapshot marked as FIXED"
    ) else (
        echo "❌ Selector validation FAILED"
        echo "Please update selector strategy and try again"
    )
) else (
    echo "❌ No HTML file available for validation"
)
```

### Step 5: Record Changes

```bash
# Record evolution with dynamic paths
echo "Selector: <name>" > evolution.txt
echo "Date: %date%" >> evolution.txt
echo "Site: %SITE%" >> evolution.txt
echo "Snapshot: %DATE%_<timestamp>" >> evolution.txt
echo "Result: SUCCESS" >> evolution.txt
echo "State: FIXED" >> evolution.txt

# Store in ledger (create if doesn't exist)
if not exist "data/snapshots/%SITE%/selector_evolution.txt" (
    echo "# Selector Evolution Ledger" > data/snapshots/%SITE%/selector_evolution.txt
    echo "# Generated: %date%" >> data/snapshots/%SITE%/selector_evolution.txt
    echo "" >> data/snapshots/%SITE%/selector_evolution.txt
)
cat evolution.txt >> data/snapshots/%SITE%/selector_evolution.txt

echo "✅ Changes recorded in evolution ledger"
```

---

## 🎯 Debugging Complete - Next Steps

**Check for remaining failures:**

```bash
# Count remaining failures dynamically
set REMAINING=0
for /f %%i in ('dir /b data/snapshots/%SITE%/selector_engine/snapshot_storage/%DATE%/failure_* 2^>nul') do (
    if not exist "data/snapshots/%SITE%/selector_engine/snapshot_storage/%DATE%/%%i/snapshot_status.txt" (
        set /a REMAINING+=1
        echo %%i
    )
)

echo "Remaining failures: %REMAINING%"
```

**If failures remain (select option A, B, or C):**

**A. Debug Next Failure** - Choose from remaining selector failures:
```
Available failures to debug:
[Dynamic list will show actual remaining failures]
```
(Select failure number to debug)

**B. Run Complete Analysis** - Use comprehensive debugging workflow  

**C. Check Design Standards** - Review selector engineering rules

**If no failures remain (select option 1 or 2):**

**1. Return to Main Menu** - Go back to workflow selection
**2. Exit Workflow** - Complete debugging session

**Select option letter or number to continue:**

---

## Quick Commands

```bash
# List all failures across all sites and snapshot types
echo "Available sites:"
ls data/snapshots/

echo "Selector engine failures:"
ls data/snapshots/*/selector_engine/snapshot_storage/*/failure_* 2>nul

echo "Flow failures:"
ls data/snapshots/*/flow/*/failure_* 2>nul

echo "Browser session failures:"
ls data/snapshots/*/browser_sessions/*/failure_* 2>nul

# Check if snapshot already fixed (any type)
if exist "data/snapshots/%SITE%/selector_engine/%DATE%/<timestamp>/snapshot_status.txt" (
    echo "Selector engine already fixed - skip"
) else if exist "data/snapshots/%SITE%/flow/%DATE%/<timestamp>/snapshot_status.txt" (
    echo "Flow already fixed - skip"
) else if exist "data/snapshots/%SITE%/browser_sessions/%DATE%/<timestamp>/snapshot_status.txt" (
    echo "Browser session already fixed - skip"
) else (
    echo "Needs debugging"
)

# Validate selector against different snapshot types
findstr /c:"data-sport-id=\"3\"" html/fullpage_failure_.html
findstr /c:"data-sport-id=\"3\"" html/fullpage.html
findstr /c:"data-sport-id=\"3\"" html/page.html
```

---

## 🔧 LLM Governance & Constraints

### 📋 LLM Creation Guidelines

**When creating or modifying this workflow:**

#### ✅ Required Structure
- **Clear Purpose**: Simple, focused debugging steps
- **Direct Commands**: CLI commands must be accurate and testable
- **Cross-References**: Link to comprehensive workflow and design standards

#### 🚫 Forbidden Changes
- **Remove Core Steps**: Cannot eliminate essential debugging procedures
- **Over-simplify**: Cannot remove critical analysis steps
- **Break Navigation**: Cannot alter links to other workflows
- **Change Scope**: Cannot expand beyond selector debugging

#### 🎯 Quality Gates
- **Command Accuracy**: All CLI examples must be tested
- **Step Clarity**: Each step must be actionable
- **Path Validation**: All file paths must be correct
- **Link Integrity**: All references must work

### 🤖 LLM Modification Constraints

#### ✅ Allowed Modifications
- **Add New Examples**: Include recent debugging scenarios
- **Update Commands**: Keep CLI commands current
- **Improve Step Descriptions**: Add explanations for complex steps
- **Add Cross-References**: Include new related workflow links

#### 🚫 Restricted Modifications
- **Remove Snapshot Analysis**: Cannot eliminate core debugging steps
- **Simplify Beyond Recognition**: Cannot remove technical details
- **Break Command Structure**: Cannot alter essential CLI workflows
- **Change Fundamental Flow**: Cannot modify step-by-step process

### 📊 Compliance Validation

#### Before Commit:
- [ ] Commands tested and accurate?
- [ ] All steps clear and actionable?
- [ ] Cross-references working?
- [ ] No essential steps removed?
- [ ] Governance guidelines followed?

#### Before Merge:
- [ ] Debugging scenarios validated?
- [ ] CLI commands verified?
- [ ] Technical accuracy maintained?
- [ ] LLM compliance confirmed?

---

*This governance ensures LLMs maintain debugging workflow effectiveness while preserving essential functionality.*
