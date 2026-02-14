---
description: Standardized workflow for debugging selector failures using snapshot observability
---

# Selector Debugging Workflow

Execute this workflow when selector resolution fails or needs optimization.

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
