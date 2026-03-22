# Memory System - BMAD Crew Advisor v0.2.0

## Memory Location
`{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/`

## Memory Structure

### Core Memory Files

#### session-state.md
Tracks current session status and progression:
```markdown
# Session State

## Current Phase
- Phase: [active-monitoring|violation-detection|checkpoint-enforcement|instruction-generation]
- Last Completed Gate: [gate-name]
- Session Start: [timestamp]
- Version: v0.2.0

## Auto-Discovered Context
- Sprint Status: [found/missing]
- Story Files: [count] ready-for-dev, [count] in-progress
- Project Context: [found/missing]
- Locked Decisions: [found/missing]
- Additional Artifacts: [count] discovered

## Discovery Cache
- Scanned Folders: [list]
- Found Files: [list with paths]
- Approved for Loading: [list]

## Current Work
- Active BMAD Command: [command]
- Last Output File: [path]
- Verification Status: [pending/passed/failed]
- Blocked Issues: [list]

## Locked Decisions Reference
- Last Loaded: [timestamp]
- Key Decisions Affecting Session: [list]
- New Decisions This Session: [list]

## Violations Detected
- Role Violations: [list]
- Process Violations: [list]
- Quality Violations: [list]
- Resolved Violations: [list]

## Instructions Issued
- Last Instruction: [summary]
- Instruction Effectiveness: [tracking]
- Recurring Patterns: [list]
```

#### discovery-cache.md
Caches auto-discovery results for efficiency:
```markdown
# Discovery Cache

## Last Scan
- Timestamp: [timestamp]
- Scanned Paths: [list]
- Total Files Found: [count]

## Standard Artifacts
- sprint-status.yaml: [path/status]
- Stories Directory: [path/file-count]
- project-context.md: [path/status]
- locked-decisions.md: [path/status]

## Additional Context Found
- Proposals: [list]
- Brainstorming Sessions: [list]
- Architecture Docs: [list]
- Feature Specs: [list]

## File Signatures
- [file-path]: [last-modified-timestamp]
- [file-path]: [last-modified-timestamp]
```

#### verification-results.md
Tracks document verification outcomes:
```markdown
# Verification Results

## Verification History
- Total Documents Verified: [count]
- Passed: [count]
- Failed: [count]
- Warnings: [count]

## Recent Verifications
### [timestamp] - [document-name]
- Type: [story|architecture|prd|etc]
- Status: [passed/failed]
- Issues: [count]
- Warnings: [count]
- Critical Issues: [list]

## Common Issues Patterns
- Missing Acceptance Criteria: [frequency]
- Scope Creep: [frequency]
- Locked Decision Conflicts: [frequency]
- Format Issues: [frequency]

## Verification Quality Metrics
- Average Issues per Document: [metric]
- Most Common Issue Type: [type]
- Verification Success Rate: [percentage]
```

#### escalation-log.md
Tracks code review escalation outcomes:
```markdown
# Code Review Escalation Log

## Escalation History
- Total Escalations: [count]
- Patch: [count]
- Defer: [count]
- Intent Gap: [count]
- Bad Spec: [count]

## Recent Escalations
### [timestamp] - [finding-description]
- Classification: [patch|defer|intent_gap|bad_spec]
- Resolution: [outcome]
- Impact: [high/medium/low]
- Coordinator Decision: [summary]

## Escalation Patterns
- Most Common Classification: [type]
- Average Resolution Time: [metric]
- Escalations Requiring Re-planning: [count]
- Stories Requiring Correction: [count]

## Quality Insights
- Code Review Quality Trend: [improving/stable/declining]
- Common Finding Types: [list]
- Escalation Success Rate: [percentage]
```

### Memory Access Patterns

#### Load Sequence (On Activation)
1. **access-boundaries.md** - Always load first
2. **session-state.md** - Current session context
3. **discovery-cache.md** - Auto-discovery results
4. **locked-decisions.md** - Project decisions (from project root)
5. **verification-results.md** - Recent verification history
6. **escalation-log.md** - Escalation patterns

#### Save Triggers
- **After auto-discovery** - Update discovery-cache.md
- **After document verification** - Update verification-results.md
- **After code review escalation** - Update escalation-log.md
- **After session phase completion** - Update session-state.md
- **When new locked decisions identified** - Update session-state.md
- **When violations detected/resolved** - Update session-state.md

#### Memory Cleanup
- **Discovery cache** - Refresh weekly or when project structure changes
- **Verification results** - Keep last 50 verifications
- **Escalation log** - Keep last 100 escalations
- **Session state** - Archive monthly, keep current active

## Memory Integration Points

### Auto-Discovery Integration
- Cache scan results to avoid repeated file system operations
- Track file changes to detect when re-scanning is needed
- Store approved context lists for quick session initialization

### Document Verification Integration
- Store verification results for pattern analysis
- Track common issues to improve detection
- Maintain quality metrics over time

### Code Review Escalation Integration
- Log escalation outcomes for pattern analysis
- Track which classifications lead to re-planning
- Monitor escalation effectiveness and quality impact

### Session Monitoring Integration
- Update session state in real-time
- Track violation patterns and resolution effectiveness
- Maintain coordinator instruction effectiveness metrics

## Memory Consistency Rules

### Data Integrity
- All timestamps in ISO format
- File paths use forward slashes, relative to project root
- Counts are integers, lists are comma-separated
- Status values use predefined enums

### Version Compatibility
- Memory structure supports v0.2.0 features
- Backward compatibility with v0.1.0 session-state.md
- Migration path for existing memory data

### Access Control
- Read access: All capabilities can read all memory files
- Write access: Only specific capabilities write to specific files
- Atomic updates: Use file locking for concurrent access

This memory system provides persistent context and intelligence for the enhanced advisor capabilities while maintaining data integrity and supporting the v0.2.0 feature set.
