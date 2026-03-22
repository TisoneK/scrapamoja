# Memory System for Crew Advisor

**Memory location:** `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/`

## Core Principle

Tokens are expensive. Only remember what matters. Condense everything to its essence.

## File Structure

### `index.md` — Primary Source
Load on activation. Contains:
- Current sprint and active story
- Session continuity (what we were doing)
- User preferences (terse vs. verbose output)
- Path to locked-decisions.md

Update when: sprint changes, story changes, session ends.

### `access-boundaries.md` — Access Control (Required)
Load before any file operations. Defines read/write/deny zones.

### `session-state.md` — Session Tracking
Updated throughout each session:
```markdown
## Current Phase
- Phase: [brainstorming/planning/implementation/code-review]
- Active Story: [story-id]
- Last Completed Gate: [gate-name]
- Session Start: [timestamp]

## Context Loaded
- Sprint Status: [loaded/missing] — Sprint [N]
- Active Stories: [list]
- Locked Decisions: [N loaded, last-read: timestamp]
- Additional Context: [list]

## Git State
- Status: [clean/dirty]
- Last Commit: [hash] [message]
- Last Verified: [timestamp]

## Active Violations
- [violation type]: [description] — status: [open/resolved]

## Checkpoint History
- [timestamp]: [gate] — [pass/block/bypass]

## Mistakes File Counter
- mistakes_file_counter: [N]
- last_mistakes_file: [path]

## Summary File Counter
- summary_file_counter: [N]
- last_summary_file: [path]
```

### `discovery-cache.md` — Auto-Discovery Results (v0.2.0)
Cached from last `--discover` run. Invalidated when sprint-status.yaml changes.

### `verification-results.md` — Document Verification History (v0.2.0)
Per-document read-and-validate results. Used to avoid re-reading unchanged files.

### `escalation-log.md` — Code Review Escalation Tracking (v0.2.0)
Tracks escalation outcomes for pattern analysis.

## Save Triggers

**Immediate (write-through):**
- Violation detected
- Gate passed or blocked
- Locked decision updated
- Story changes state

**On session end:**
- Full session-state.md write
- Summary file generated
- Mistakes file generated (if story cycle complete)

## Memory Discipline

Before writing, ask:
1. Is this worth remembering? → If no, skip
2. What is the minimum tokens that capture this? → Condense
3. Which file? → index.md for active context, session-state.md for gate/violation tracking

## First Run

If sidecar doesn't exist, load `init.md` to create the structure.
