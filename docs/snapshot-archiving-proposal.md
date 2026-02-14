# Snapshot Archiving Feature Proposal

## Executive Summary

This proposal outlines a new archiving mechanism for the `core/snapshots/` module that automatically compresses and archives old session snapshots when a new session begins, maintaining only the current session's snapshots in an uncompressed, readily accessible state.

---

## Problem Statement

Currently, all session snapshots remain uncompressed in the snapshots directory, leading to:
- **Disk space inefficiency**: Snapshots accumulate without compression
- **Navigation difficulties**: The snapshots folder becomes cluttered with historical data
- **Unclear active state**: No clear distinction between active and historical snapshots

---

## Proposed Solution

### Overview
Implement an automatic archiving system with ID-based snapshot management and threshold cycling:

1. **Assign** sequential snapshot IDs (001, 002, 003, ..., up to configured max)
2. **Compress** all snapshots from the previous session
3. **Move** the compressed archive to a dedicated archive directory
4. **Maintain** the current session's snapshots uncompressed for immediate analysis
5. **Cycle** back to 001 when the threshold is reached, deleting the oldest archives
6. **Repeat** the process when the next session begins

### Architecture

```
data/
└── snapshots/
    ├── archive/
    │   ├── snapshot_001.zip
    │   ├── snapshot_002.zip
    │   ├── snapshot_003.zip
    │   └── ... (up to max threshold, e.g., 100)
    ├── .snapshot_counter    # Tracks current snapshot ID
    └── [current session files - uncompressed]
```

### ID Management System

**Snapshot ID Assignment:**
- Sequential numbering: `001`, `002`, `003`, ..., `100` (configurable max)
- Zero-padded for consistent sorting and readability
- Stored in `.snapshot_counter` file for persistence

**Threshold Cycling:**
- When ID reaches max limit (e.g., 100), system cycles back to 001
- Oldest archive (001) is automatically deleted before creating new snapshot_001.zip
- Ensures bounded storage growth and automatic cleanup

### ID Cycling Visualization

**Example with MAX_LIMIT = 100:**

```
Timeline of Sessions:

Session 1  → ID: 001 → archive/snapshot_001.zip created
Session 2  → ID: 002 → archive/snapshot_002.zip created
Session 3  → ID: 003 → archive/snapshot_003.zip created
...
Session 99 → ID: 099 → archive/snapshot_099.zip created
Session 100 → ID: 100 → archive/snapshot_100.zip created

Archive state: [001, 002, 003, ..., 099, 100] (100 files)

Session 101 → ID: 001 (CYCLE!) 
  1. Delete old snapshot_001.zip
  2. Create new snapshot_001.zip
  
Archive state: [001*, 002, 003, ..., 099, 100] (100 files, * = newest)

Session 102 → ID: 002 (CYCLE!)
  1. Delete old snapshot_002.zip
  2. Create new snapshot_002.zip
  
Archive state: [001, 002*, 003, ..., 099, 100] (100 files, * = newest)

Pattern continues...
```

**Key Insight:** The archive directory always maintains exactly MAX_LIMIT files, with the oldest being continuously replaced by the newest.

---

## Implementation Details

### 1. Archiving Workflow

```
┌─────────────────────────────────┐
│   New Session Initiated         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Read Current Snapshot ID      │
│   - Load from .snapshot_counter │
│   - Initialize to 001 if new    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Check for Existing Snapshots  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Increment Snapshot ID         │
│   - current_id + 1              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Check Threshold               │
│   - If ID > MAX_LIMIT           │
│   - Reset to 001                │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Delete Old Archive (if cycle) │
│   - Remove snapshot_{ID}.zip    │
│   - Only if cycling back        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Compress Previous Session     │
│   - Create .zip archive         │
│   - Name: snapshot_{ID}.zip     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Move to archive/ Directory    │
│   - Ensure archive/ exists      │
│   - Move compressed file        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Update Snapshot Counter       │
│   - Save new ID to file         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Delete Original Snapshots     │
│   - Remove uncompressed files   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Process New Session           │
│   - Create new snapshots        │
│   - Keep uncompressed           │
└─────────────────────────────────┘
```

### 2. File Naming Convention

**Archive files:**
```
snapshot_{ID}.zip
```

**Examples:**
- `snapshot_001.zip`
- `snapshot_002.zip`
- `snapshot_100.zip`

**ID Format:**
- Zero-padded to 3 digits (supports up to 999 snapshots)
- Sequential numbering for easy tracking
- Cycles back to 001 when threshold reached

**Counter File:**
- File: `.snapshot_counter`
- Content: Current snapshot ID (e.g., `042`)
- Location: `data/snapshots/.snapshot_counter`

### 3. Directory Structure

**Location:** `data/snapshots/archive/`

**Hierarchy:**
```
data/
└── snapshots/
    ├── archive/              # All compressed historical sessions
    │   ├── snapshot_001.zip
    │   ├── snapshot_002.zip
    │   ├── snapshot_003.zip
    │   └── ... (up to max threshold)
    ├── .snapshot_counter     # Tracks current snapshot ID
    ├── session.json          # Current session metadata
    ├── snapshot_001.json     # Current session snapshots
    ├── snapshot_002.json
    └── ...
```

**Threshold Cycling Example (MAX_LIMIT = 100):**
```
State 1: ID = 099
archive/
├── snapshot_001.zip
├── snapshot_002.zip
├── ...
└── snapshot_099.zip

State 2: New session triggered, ID = 100
archive/
├── snapshot_001.zip  # Still present
├── snapshot_002.zip
├── ...
├── snapshot_099.zip
└── snapshot_100.zip

State 3: New session triggered, ID cycles to 001
archive/
├── snapshot_001.zip  # DELETED, then recreated with new data
├── snapshot_002.zip
├── ...
└── snapshot_100.zip

State 4: Next session, ID = 002
archive/
├── snapshot_001.zip
├── snapshot_002.zip  # DELETED, then recreated with new data
├── snapshot_003.zip
├── ...
└── snapshot_100.zip
```

### 4. Technical Specifications

**Compression:**
- Format: ZIP (cross-platform compatibility)
- Compression level: Standard (balance between size and speed)
- Library: Python's `zipfile` module

**ID Management:**
- Storage: `.snapshot_counter` file in `data/snapshots/`
- Format: Plain text, single integer (e.g., "042")
- Initialization: Starts at 001 on first run
- Increment: +1 per new session
- Cycling: Resets to 001 when MAX_LIMIT reached

**Archive Management:**
- Automatic directory creation if `archive/` doesn't exist
- Atomic operations to prevent data loss
- Pre-deletion check before cycling (ensure old archive exists)
- Error handling for disk space issues

**Threshold System:**
- Configurable MAX_LIMIT (default: 100)
- Automatic deletion of oldest archive when cycling
- Bounded storage: Never exceeds MAX_LIMIT archives
- Predictable storage footprint

**Session Detection:**
- Trigger: New session initialization
- ID tracking: Sequential counter in `.snapshot_counter`
- Validation: Ensure previous session is complete

---

## Benefits

### 1. Disk Space Optimization
- **Compression ratio**: Typically 60-80% space savings for JSON/text files
- **Bounded storage**: Maximum storage predictable (MAX_LIMIT × average archive size)
- **Automatic cleanup**: No manual intervention needed when threshold reached
- **Cost efficiency**: Reduced storage requirements for long-running systems

### 2. Improved Navigation & Organization
- **Clean workspace**: Only active snapshots visible in main directory
- **Clear separation**: Historical vs. current data
- **Easy identification**: Active session immediately apparent
- **Simple naming**: Sequential IDs easier to reference than timestamps
- **Reduced clutter**: Archive directory keeps history organized

### 3. Predictable Storage Management
- **No unbounded growth**: Storage ceiling defined by MAX_LIMIT
- **Easy capacity planning**: Storage needs = MAX_LIMIT × avg_archive_size
- **Automatic cycling**: Oldest data automatically removed
- **Simple tracking**: Sequential IDs make it easy to know archive count

### 4. Performance Benefits
- **Faster directory listings**: Fewer files in active directory
- **Quicker analysis**: Current session data readily accessible
- **Reduced I/O**: Less file scanning overhead
- **Consistent performance**: Archive count never exceeds threshold

### 5. Data Retention
- **Rolling window**: Most recent N sessions always available (N = MAX_LIMIT)
- **Complete history**: All sessions within window preserved
- **Easy retrieval**: Archives can be extracted when needed
- **Predictable retention**: Know exactly how many sessions are retained

---

## Implementation Phases

### Phase 1: Core Functionality (Week 1)
- [ ] Implement snapshot ID counter system
  - [ ] Create/read `.snapshot_counter` file
  - [ ] Increment logic with threshold checking
  - [ ] Cycling logic (reset to 001)
- [ ] Implement compression logic
- [ ] Create archive directory structure
- [ ] Develop archive file naming system (snapshot_{ID}.zip)
- [ ] Basic error handling

### Phase 2: Integration & Cleanup (Week 2)
- [ ] Integrate with session initialization
- [ ] Implement old archive deletion logic
- [ ] Add configuration options (MAX_LIMIT, etc.)
- [ ] Implement logging
- [ ] Atomic operation safeguards
- [ ] Testing and validation

### Phase 3: Enhancement & Documentation (Week 3)
- [ ] Add archive retrieval utilities
- [ ] Implement archive size monitoring
- [ ] Add counter reset utility (manual override)
- [ ] Create archive listing/browsing tools
- [ ] Documentation and examples
- [ ] Performance testing with threshold cycling

---

## Configuration Options

```python
ARCHIVE_CONFIG = {
    'enabled': True,
    'archive_path': 'data/snapshots/archive/',
    'max_limit': 100,  # Maximum number of archived snapshots before cycling
    'id_padding': 3,  # Zero-padding for IDs (3 = 001, 002, ..., 999)
    'counter_file': '.snapshot_counter',
    'compression_level': 6,  # 0-9, higher = more compression
    'archive_format': 'zip',
    'naming_pattern': 'snapshot_{id}',  # ID auto-formatted with padding
    'auto_delete_on_cycle': True,  # Delete old archive when cycling
    'safe_mode': True,  # Verify archive before deleting original snapshots
}
```

**Key Parameters:**

- **max_limit**: Defines the cycling threshold (default: 100)
  - When snapshot ID reaches this number, it cycles back to 001
  - Determines maximum number of archives stored simultaneously
  
- **id_padding**: Number of digits for zero-padding (default: 3)
  - 3 = supports up to 999 snapshots
  - 4 = supports up to 9,999 snapshots
  
- **auto_delete_on_cycle**: Controls deletion behavior (default: True)
  - True = automatically delete old archive when cycling
  - False = keep old archives (may exceed max_limit)

---

## Risk Assessment

### Low Risk
- **Compression failures**: Fallback to keep uncompressed
- **Disk full**: Pre-check available space
- **Counter file corruption**: Reinitialize from archive directory scan

### Medium Risk
- **Concurrent sessions**: Implement file locking on counter file
- **Partial compression**: Transaction-like approach
- **ID cycling race condition**: Atomic read-increment-write operations

### High Risk (Mitigated)
- **Data loss during cycling**: Old archive deleted before new one created
  - **Mitigation**: Create new archive first, verify, then delete old
  - **Fallback**: If new archive creation fails, keep old archive

### Mitigation Strategies
1. **Atomic counter updates**: Use file locking for `.snapshot_counter`
2. **Safe cycling**: Create → Verify → Delete order
3. **Logging**: Comprehensive operation logs including ID changes
4. **Validation**: Verify archive integrity before deletion
5. **Counter recovery**: Rebuild from archive directory if counter lost

---

## Future Enhancements

### Potential Extensions
1. **Archive browser**: Web UI for viewing archived sessions by ID
2. **ID-based search**: Quick retrieval by snapshot ID or range
3. **Selective extraction**: Extract specific snapshots without full decompression
4. **Cloud storage**: Option to move archives to S3/cloud storage
5. **Compression algorithms**: Support for additional formats (tar.gz, 7z)
6. **Metadata indexing**: Searchable archive metadata database with ID mapping
7. **Automated cleanup**: Additional policies beyond cycling (e.g., size-based)
8. **ID reservation**: Reserve specific IDs for important sessions
9. **Multi-tier archiving**: Move very old archives to cold storage
10. **Counter analytics**: Track session frequency and archive patterns

---

## Success Metrics

### Quantitative
- **Storage reduction**: Target 60%+ space savings
- **Bounded storage**: Never exceeds (MAX_LIMIT × avg_archive_size)
- **Archive time**: < 5 seconds for typical session
- **Zero data loss**: 100% archive integrity
- **Cycling accuracy**: 100% correct ID sequencing and wraparound
- **Counter reliability**: 99.9%+ counter file persistence

### Qualitative
- **Developer experience**: Easier navigation of snapshot directory
- **System maintainability**: Cleaner folder structure
- **Data accessibility**: Quick access to current session data
- **Predictability**: Clear understanding of retention window
- **Simplicity**: Sequential IDs easier to reference than timestamps

---

## Appendix

### A. Example Code Structure

```python
# core/snapshots/archiver.py

import os
import zipfile
from pathlib import Path

class SnapshotArchiver:
    def __init__(self, config):
        self.config = config
        self.archive_path = Path(config.get('archive_path'))
        self.counter_file = Path(config.get('snapshots_path')) / config.get('counter_file')
        self.max_limit = config.get('max_limit', 100)
        self.id_padding = config.get('id_padding', 3)
        
    def get_current_id(self):
        """Read current snapshot ID from counter file"""
        if self.counter_file.exists():
            with open(self.counter_file, 'r') as f:
                return int(f.read().strip())
        return 0
    
    def increment_id(self):
        """Increment snapshot ID and handle cycling"""
        current_id = self.get_current_id()
        next_id = current_id + 1
        
        # Check if we need to cycle
        if next_id > self.max_limit:
            next_id = 1
        
        # Write new ID to counter file
        with open(self.counter_file, 'w') as f:
            f.write(str(next_id))
        
        return next_id
    
    def format_id(self, snapshot_id):
        """Format ID with zero-padding"""
        return str(snapshot_id).zfill(self.id_padding)
    
    def get_archive_name(self, snapshot_id):
        """Generate archive filename for given ID"""
        formatted_id = self.format_id(snapshot_id)
        return f"snapshot_{formatted_id}.zip"
    
    def archive_session(self, snapshot_files):
        """Archive snapshots from a completed session"""
        snapshot_id = self.increment_id()
        archive_name = self.get_archive_name(snapshot_id)
        archive_path = self.archive_path / archive_name
        
        # Delete old archive if cycling back
        if archive_path.exists():
            print(f"Cycling: Deleting old {archive_name}")
            archive_path.unlink()
        
        # Create archive
        self._create_archive(snapshot_files, archive_path)
        
        return snapshot_id, archive_path
    
    def _create_archive(self, files, archive_path):
        """Create ZIP archive from snapshot files"""
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                zipf.write(file, arcname=os.path.basename(file))
    
    def extract_archive(self, snapshot_id, destination):
        """Extract archived session for review"""
        archive_name = self.get_archive_name(snapshot_id)
        archive_path = self.archive_path / archive_name
        
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive {archive_name} not found")
        
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            zipf.extractall(destination)
    
    def list_archives(self):
        """List all archived sessions with IDs"""
        if not self.archive_path.exists():
            return []
        
        archives = []
        for file in sorted(self.archive_path.glob('snapshot_*.zip')):
            # Extract ID from filename
            id_str = file.stem.replace('snapshot_', '')
            archives.append({
                'id': int(id_str),
                'filename': file.name,
                'path': file,
                'size': file.stat().st_size
            })
        
        return sorted(archives, key=lambda x: x['id'])
    
    def reset_counter(self, new_id=0):
        """Reset counter to specific ID (admin function)"""
        with open(self.counter_file, 'w') as f:
            f.write(str(new_id))
```

### B. Testing Checklist
- [ ] Archive creation with various snapshot sizes
- [ ] Archive extraction and validation
- [ ] Snapshot ID increment and persistence
- [ ] Threshold cycling (ID reaches MAX_LIMIT)
- [ ] Old archive deletion during cycling
- [ ] Counter file creation and recovery
- [ ] Counter file corruption handling
- [ ] Concurrent session handling with ID locking
- [ ] Disk space error scenarios
- [ ] Archive integrity verification
- [ ] Performance benchmarks with cycling
- [ ] ID formatting with different padding values
- [ ] Archive listing and sorting by ID

---

## Conclusion

The snapshot archiving feature provides a robust solution for managing historical session data while maintaining optimal performance and accessibility for active sessions. The implementation is straightforward, low-risk, and offers immediate benefits in terms of storage efficiency and organizational clarity.

---

**Document Version:** 1.0  
**Date:** February 14, 2026  
**Status:** Proposed  
**Owner:** Development Team
