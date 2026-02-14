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
   - Open `data/snapshots/<site>/selector_engine/<timestamp>/`
   - Review metadata.json for failure context
   - Inspect HTML for actual DOM structure
   - Check screenshots for visual state
   - Review console logs for errors

2. **Classify Failure Type**
   - `selector_not_found`: Target element absent
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

5. **Quick Debugging Workflow**

**Simple validation commands:**

```bash
# Test selector against snapshot HTML
cd "data/snapshots/flashscore/selector_engine/<timestamp>/"
findstr /c:"selector_pattern" fullpage.html

# Check if element exists in snapshot
findstr /c:"data-sport-id=\"3\"" fullpage.html

# Run selector test (if available)
python -m src.sites.flashscore.test_selector "basketball_link" "fullpage.html"

# Record result with state tracking
echo "Result: SUCCESS/FAILED" > validation_result.txt
echo "State: FIXED/OPEN" >> validation_result.txt

# Mark snapshot status
echo "status: FIXED" > data/snapshots/flashscore/selector_engine/<timestamp>/snapshot_status.txt
```

**State tracking prevents re-analyzing fixed snapshots.**

6. **Check Snapshot Status**

**Before starting, check if already fixed:**

```bash
# Check snapshot status first
if exist "data/snapshots/flashscore/selector_engine/<timestamp>/snapshot_status.txt" (
    findstr /c:"FIXED" "data/snapshots/flashscore/selector_engine/<timestamp>/snapshot_status.txt"
    if %errorlevel% equ 0 (
        echo "✅ Snapshot already FIXED - skip debugging"
        exit /b
    )
)
```

**This prevents infinite debugging loops.**

## Expected Outcomes

- Evidence-based selector fixes
- Reproducible debugging results
- Improved selector stability
- Historical failure analysis capability

## Quick Commands

```bash
# List recent selector failures
ls data/snapshots/flashscore/selector_engine/

# Analyze specific failure
cat data/snapshots/flashscore/selector_engine/20260214/*/metadata.json

# Validate selector against snapshot
# Use snapshot HTML as test input for selector updates
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
