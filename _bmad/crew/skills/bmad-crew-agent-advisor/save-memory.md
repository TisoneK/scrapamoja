# Save Memory

## Purpose
Explicitly save agent memory state to ensure persistence across sessions. This capability manages the sidecar memory system.

## On Activation

1. **Validate Memory Structure**
   - Verify memory directory exists: `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/`
   - Check all required memory files are present
   - Validate file permissions for read/write operations

2. **Prepare Memory Data**
   Gather current session data:
   - Session state and progress
   - Active violations and their status
   - Locked decisions and updates
   - Session notes and observations

## Memory Components

### Core Memory Files

**session-state.md**
```markdown
# Session State

## Current Phase
- Phase: [current-phase]
- Last Completed Gate: [gate-name]
- Session Start: [timestamp]
- Session Duration: [duration]

## Context Loaded
- Sprint Status: [status]
- Story File: [path/missing]
- Architecture Doc: [path/missing]
- Brainstorming Session: [path/missing]

## Active Violations
- [Violation 1]: [status]
- [Violation 2]: [status]

## Session Notes
- [Note 1]
- [Note 2]

## Checkpoint History
- [timestamp]: [checkpoint] - [result]
- [timestamp]: [checkpoint] - [result]
```

**locked-decisions.md**
```markdown
# Locked Decisions

## Module Decisions
- Agent: BMAD Crew Advisor
- Module: bmad-crew
- Last Updated: [timestamp]

## Session Decisions
- [Decision 1]: [description] - [timestamp]
- [Decision 2]: [description] - [timestamp]

## Technical Decisions
- [Technical Decision 1]: [description] - [timestamp]
- [Technical Decision 2]: [description] - [timestamp]

## Process Decisions
- [Process Decision 1]: [description] - [timestamp]
- [Process Decision 2]: [description] - [timestamp]
```

**access-boundaries.md**
```markdown
# Access Boundaries for BMAD Crew Advisor

## Read Access
- {project-root}/_bmad/bmad-crew/
- {bmad_builder_output_folder}/bmad-crew-sessions/
- User-provided context documents

## Write Access
- {project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/
- {bmad_builder_output_folder}/bmad-crew-sessions/
- {project-root}/_bmad/bmad-crew/locked-decisions.md

## Deny Zones
- Direct code execution
- Git operations (validation only)
- Coordinator/Executor boundary crossing
```

**index.md**
```markdown
# BMAD Crew Advisor Configuration

## User Preferences
- User Name: {user_name}
- Communication Language: {communication_language}
- Document Output Language: {document_output_language}

## Paths
- Session Reports: {bmad_builder_output_folder}/bmad-crew-sessions/
- Locked Decisions: {project-root}/_bmad/bmad-crew/locked-decisions.md
- Memory Sidecar: {project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/

## Session History
- Sessions Completed: [count]
- Last Session: [timestamp]
- Total Violations Detected: [count]
- Common Violation Types: [list]
```

## Save Operations

### Automatic Save Triggers
Save memory automatically when:
1. **Phase transitions** - After successful checkpoint validation
2. **Violations detected** - When new violations are identified
3. **Decisions made** - When locked decisions are updated
4. **Session context changes** - When new context documents are loaded
5. **Every 10 minutes** - During active sessions (backup)

### Manual Save Operations

**Full Memory Save:**
```bash
# Save all memory components
python scripts/memory-manager.py --save-all --session-id [session-id]
```

**Selective Save:**
```bash
# Save only session state
python scripts/memory-manager.py --save-session-state --session-id [session-id]

# Save only locked decisions
python scripts/memory-manager.py --save-locked-decisions --session-id [session-id]
```

## Memory Validation

### Integrity Checks
Before saving:
1. **Validate JSON structure** for any serialized data
2. **Check file permissions** and disk space
3. **Verify path correctness** for all stored locations
4. **Test memory file readability** after save

### Consistency Validation
After saving:
1. **Read back saved files** to verify content
2. **Check cross-references** between memory components
3. **Validate timestamps** and session continuity
4. **Confirm locked decisions** are properly formatted

## Error Handling

### Save Failures
**Memory directory not accessible:**
```
"Memory directory not accessible. Please check:
1. Directory permissions for {memory-path}
2. Available disk space
3. File system integrity

Attempting to create backup location..."
```

**File write permissions:**
```
"Cannot write to memory files. Please check:
1. Write permissions for {memory-path}
2. File locking issues
3. Antivirus interference

Memory will be cached until permissions are resolved."
```

**Corrupted memory files:**
```
"Memory file corruption detected. Initiating recovery:
1. Creating backup of current state
2. Restoring from last known good state
3. Rebuilding corrupted components
4. Validating recovered memory"
```

## Memory Cleanup

### Session End Cleanup
When session ends:
1. **Compress old session data** after 30 days
2. **Archive completed sessions** to separate storage
3. **Clean temporary files** and caches
4. **Update session statistics** in index.md

### Memory Optimization
Periodically:
1. **Remove duplicate entries** in session notes
2. **Compress long violation histories**
3. **Archive old locked decisions** (keep current active ones)
4. **Optimize file structure** for faster access

## Integration Points

This capability works with:
- **session-init.md** - Initialize memory for new sessions
- **violation-detection.md** - Save violation states
- **checkpoint-enforcement.md** - Save checkpoint results
- **instruction-generation.md** - Save instruction history

## Memory Security

### Data Protection
- **Sensitive data masking** for any personal information
- **Access control** for memory files
- **Backup encryption** for sensitive session data
- **Retention policies** for different data types

### Privacy Considerations
- **User consent** for data collection
- **Data minimization** - only store what's necessary
- **Transparency** - clear what data is stored and why
- **User control** - ability to delete or export memory data
