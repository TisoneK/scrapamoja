---
description: System maintenance and cleanup procedures for snapshot system
---

# System Maintenance Workflow

**Owner:** Snapshot System  
**Scope:** System Operations  
**Applies To:** All system components  
**Last Reviewed:** 2026-02-14  
**Status:** stable

## Purpose

Maintain system health and organization through periodic cleanup and validation tasks.

---

## Archive Old Snapshots

**Only when:**
- Data exceeds 500MB, OR
- Directories older than 60 days, OR
- Workspace navigation becomes difficult

1. Verify no active debugging in progress
2. Compress old session:
   ```powershell
   Compress-Archive -Path "data/snapshots/flashscore/selector_engine/snapshot_storage/20260214" `
                    -DestinationPath "archive/session_20260214.zip"
   ```
3. Verify archive integrity
4. Delete original directory
5. Update workflow_status.json if needed

---

## Regular Maintenance Tasks

1. **Cleanup Legacy Directories**
   ```bash
   # Remove unknown/ directory if empty
   rmdir data/snapshots/unknown/
   
   # Clean old checkpoints
   rm .checkpoints/checkpoint_interrupt_*.json
   ```

2. **Validate System Health**
   - Check disk space usage
   - Verify all snapshot types working
   - Test browser session storage
   - Validate flow snapshot creation

3. **Update Documentation**
   - Record maintenance activities
   - Update performance metrics
   - Document any system changes

## Expected Outcomes

- Clean and efficient snapshot storage
- Optimal system performance
- Up-to-date documentation
- Early detection of system issues
