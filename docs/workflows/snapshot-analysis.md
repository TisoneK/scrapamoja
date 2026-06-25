---
description: Analyze snapshot artifacts for debugging and system health monitoring
---

# Snapshot Analysis Workflow

**Owner:** Snapshot System  
**Scope:** System Health  
**Applies To:** All snapshot types  
**Last Reviewed:** 2026-02-14  
**Status:** stable

## Purpose

Use this workflow to examine snapshot artifacts and diagnose system issues.

## Steps

1. **Locate Snapshots**
   ```bash
   # List all snapshots by site
   ls data/snapshots/
   
   # Find recent snapshots
   find data/snapshots -name "*.json" -type f -mtime -7
   ```

2. **Analyze Structure**
   - Verify metadata.json exists in all snapshot directories
   - Check for complete artifact sets (html, screenshots, logs)
   - Identify missing or corrupted artifacts

3. **Review Metadata**
   - Examine failure patterns and frequencies
   - Analyze performance metrics
   - Track selector strategy effectiveness

4. **Cross-Reference Artifacts**
   - Correlate HTML content with screenshot evidence
   - Match console logs with failure patterns
   - Validate timestamp consistency

## Expected Outcomes

- Complete system health assessment
- Identification of chronic issues
- Performance baseline establishment
- Data-driven improvement recommendations
