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
# Check all selector-related snapshot types
ls data/snapshots/flashscore/selector_engine/snapshot_storage/20260214/
ls data/snapshots/flashscore/flow/20260214/
ls data/snapshots/flashscore/browser_sessions/20260214/

# Find most recent failure across all types
dir /od data/snapshots/flashscore/selector_engine/snapshot_storage/20260214/
dir /od data/snapshots/flashscore/flow/20260214/
dir /od data/snapshots/flashscore/browser_sessions/20260214/
```

### Step 2: Analyze Specific Failure

```bash
# For selector engine failures
cd "data/snapshots/flashscore/selector_engine/snapshot_storage/20260214/<timestamp>/"
type metadata.json
type html/fullpage_failure_.html | findstr /c:"selector_pattern"

# For flow-level failures  
cd "data/snapshots/flashscore/flow/20260214/<timestamp>/"
type metadata.json
type html/fullpage.html | findstr /c:"target_element"

# For browser session issues
cd "data/snapshots/flashscore/browser_sessions/20260214/<timestamp>/"
type metadata.json
type html/page.html | findstr /c:"navigation"
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
# Test selector against snapshot
findstr /c:"selector_pattern" html/fullpage_failure_.html

# Mark as fixed if successful
echo "status: FIXED" > snapshot_status.txt
```

### Step 5: Record Changes

```bash
# Record evolution
echo "Selector: <name>" > evolution.txt
echo "Date: %date%" >> evolution.txt
echo "Result: SUCCESS" >> evolution.txt
echo "State: FIXED" >> evolution.txt

# Store in ledger
cat evolution.txt >> data/snapshots/flashscore/selector_evolution.txt
```

---

## 🎯 Debugging Complete - Next Steps

**Check for remaining failures:**

```bash
# Count remaining failures
ls data/snapshots/flashscore/selector_engine/snapshot_storage/20260214/ | find /c "failure_"

# List specific failures
ls data/snapshots/flashscore/selector_engine/snapshot_storage/20260214/failure_*
```

**If failures remain (1-3):**

1. **Debug Next Failure** - Choose from remaining selector failures:
   ```
   Available failures to debug:
   1. 181436_failure_cookie_consent_1771071276.696055
   2. 181442_failure_authentication.cookie_consent_1771071282.029415  
   3. 181449_failure_cookie_consent_1771071289.201868
   4. 181455_failure_authentication.cookie_consent_1771071295.088147
   ```
   (Select failure number to debug)

2. **Run Complete Analysis** - Use comprehensive debugging workflow  
3. **Check Design Standards** - Review selector engineering rules

**If no failures remain (1-2):**
1. **Return to Main Menu** - Go back to workflow selection
2. **Exit Workflow** - Complete debugging session

**Select option number to continue:**

---

## Quick Commands

```bash
# List all failures across snapshot types
ls data/snapshots/flashscore/selector_engine/snapshot_storage/
ls data/snapshots/flashscore/flow/
ls data/snapshots/flashscore/browser_sessions/

# Check if snapshot already fixed (any type)
if exist "data/snapshots/flashscore/selector_engine/<timestamp>/snapshot_status.txt" (
    echo "Selector engine already fixed - skip"
) else if exist "data/snapshots/flashscore/flow/<timestamp>/snapshot_status.txt" (
    echo "Flow already fixed - skip"
) else if exist "data/snapshots/flashscore/browser_sessions/<timestamp>/snapshot_status.txt" (
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
