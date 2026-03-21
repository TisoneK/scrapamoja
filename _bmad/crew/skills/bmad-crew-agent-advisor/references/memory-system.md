# Memory System for BMAD Crew Advisor

## Overview

The BMAD Crew Advisor uses a sidecar memory system to maintain state across sessions. This enables persistent tracking of violations, decisions, and session progress.

## Memory Structure

### Location
```
{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/
```

### Core Files

**access-boundaries.md** - Defines what the agent can access
**session-state.md** - Current session progress and violations
**locked-decisions.md** - Decisions that persist across sessions
**index.md** - Configuration and session history

## Memory Loading Sequence

### On Agent Activation
1. **Load access-boundaries.md first** - Establish permissions before any operations
2. **Load index.md** - Get user preferences and session history
3. **Load session-state.md** - Resume current session or initialize new one
4. **Load locked-decisions.md** - Get established decisions for reference

### Memory Validation
After loading:
1. **Verify file integrity** - Check for corruption or incomplete data
2. **Validate permissions** - Ensure read/write access to memory location
3. **Check consistency** - Verify cross-references between files
4. **Test paths** - Confirm stored paths are still valid

## Memory Operations

### Reading Memory
- **Always load access-boundaries.md first** - This is non-negotiable
- **Use full paths** for all memory file references
- **Validate content** before using memory data
- **Handle missing files** gracefully with defaults

### Writing Memory
- **Atomic updates** - Write to temporary file, then rename
- **Backup before changes** - Keep previous version for recovery
- **Validate after write** - Read back to confirm integrity
- **Handle write failures** with clear error messages

### Memory Persistence
- **Save on state changes** - Violations, checkpoints, decisions
- **Periodic backups** - Every 10 minutes during active sessions
- **Session end save** - Complete state preservation
- **Cleanup old data** - Archive sessions older than 30 days

## Data Models

### Session State
```yaml
session:
  id: "session-uuid"
  start_time: "2026-03-21T10:20:00Z"
  current_phase: "implementation"
  last_checkpoint: "architecture-complete"
  
context:
  sprint_status: "loaded"
  story_file: "/path/to/story.md"
  architecture_doc: "/path/to/arch.md"
  brainstorming_session: "/path/to/brainstorm.md"

violations:
  active:
    - type: "role-boundary"
      description: "Agent implementing code"
      status: "flagged"
      instructions_issued: true
  resolved:
    - type: "process"
      description: "Missing documentation"
      resolved_at: "2026-03-21T10:15:00Z"

checkpoints:
  - timestamp: "2026-03-21T10:10:00Z"
    phase: "planning"
    result: "passed"
  - timestamp: "2026-03-21T10:15:00Z"
    phase: "architecture"
    result: "passed"
```

### Locked Decisions
```yaml
decisions:
  module:
    - id: "decision-001"
      area: "architecture"
      decision: "Use REST APIs for all external communication"
      rationale: "Standardization and tooling support"
      made_at: "2026-03-20T15:30:00Z"
      made_by: "Coordinator"
  
  session:
    - id: "decision-002"
      area: "process"
      decision: "Skip brainstorming phase for this sprint"
      rationale: "Requirements already clear from previous work"
      made_at: "2026-03-21T10:05:00Z"
      made_by: "Coordinator"
```

### Access Boundaries
```yaml
access:
  read:
    - "{project-root}/_bmad/bmad-crew/"
    - "{bmad_builder_output_folder}/bmad-crew-sessions/"
    - "User-provided context documents"
  
  write:
    - "{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/"
    - "{bmad_builder_output_folder}/bmad-crew-sessions/"
    - "{project-root}/_bmad/bmad-crew/locked-decisions.md"
  
  deny:
    - "Direct code execution"
    - "Git operations (validation only)"
    - "Coordinator/Executor boundary crossing"
```

## Memory Best Practices

### File Operations
- **Use forward slashes** in all paths (cross-platform compatibility)
- **Never use relative paths** like `../` or `./`
- **Always validate paths** before file operations
- **Handle file not found** gracefully with defaults

### Data Integrity
- **Validate JSON/YAML structure** before saving
- **Use atomic writes** (temp file + rename)
- **Keep backups** of important state changes
- **Implement recovery** for corrupted files

### Performance
- **Load only what's needed** for current operations
- **Cache frequently accessed data** in memory
- **Batch writes** when possible
- **Compress old data** to save space

## Error Handling

### Memory Access Errors
**Directory not found:**
```
"Memory directory not found at {path}. Creating new memory structure..."
```

**File corruption:**
```
"Memory file corrupted: {file}. Attempting recovery from backup..."
```

**Permission denied:**
```
"Cannot access memory directory. Please check permissions for {path}"
```

### Data Validation Errors
**Invalid structure:**
```
"Invalid memory structure in {file}. Rebuilding with defaults..."
```

**Missing required fields:**
```
"Required field missing from {file}: {field}. Adding default value..."
```

## Memory Security

### Access Control
- **Restrict memory access** to authorized users only
- **Use file permissions** to control access
- **Validate paths** to prevent directory traversal
- **Sanitize inputs** before storing in memory

### Data Protection
- **Mask sensitive information** in memory logs
- **Encrypt sensitive session data** if required
- **Implement retention policies** for different data types
- **Provide data export** capability for users

## Integration Notes

### With Session Init
- Load existing session state or create new
- Validate access boundaries before any operations
- Initialize memory structure for new sessions

### With Violation Detection
- Update active violations in memory
- Track violation resolution status
- Store violation patterns for analysis

### With Checkpoint Enforcement
- Save checkpoint results to memory
- Update phase progression status
- Record checkpoint history

### With Instruction Generation
- Store issued instructions for reference
- Track instruction effectiveness
- Maintain instruction history
