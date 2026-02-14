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

1. **Cleanup Legacy Directories**
   ```bash
   # Remove unknown/ directory if empty
   rmdir data/snapshots/unknown/
   
   # Clean old checkpoints
   rm .checkpoints/checkpoint_interrupt_*.json
   ```

2. **Archive Old Snapshots**
   ```bash
   # Move snapshots older than 30 days to archive
   find data/snapshots -mtime +30 -exec mv {} archive/ \;
   ```

3. **Validate System Health**
   - Check disk space usage
   - Verify all snapshot types working
   - Test browser session storage
   - Validate flow snapshot creation

4. **Update Documentation**
   - Record maintenance activities
   - Update performance metrics
   - Document any system changes

## Expected Outcomes

- Clean and efficient snapshot storage
- Optimal system performance
- Up-to-date documentation
- Early detection of system issues
