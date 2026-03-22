# Save Memory

## Purpose
Explicitly save session state to the memory sidecar. Triggered automatically at phase transitions, violation detection, and session end. Also available as [SM] manual capability.

## Memory Location
`{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/`

## Save Sequence

1. **Validate memory directory** — create if missing
2. **Write session-state.md** — current phase, active story, git state, violations, checkpoint history, file counters
3. **Update index.md** — essential context: active sprint, story, last gate completed
4. **Flush discovery-cache.md** — if discovery was re-run this session
5. **Append to escalation-log.md** — if code review escalations occurred this session
6. **Confirm write** — read back to verify

## index.md Platform Fields (write once on first run, never overwrite)
```markdown
## Platform
- OS: [Windows | macOS | Linux]
- Python Binary: [python | python3]
```

## session-state.md Template
```markdown
## Current Phase
- Phase: [brainstorming/planning/implementation/code-review]
- Active Story: [story-id or none]
- Last Completed Gate: [gate-name]
- Session Start: [timestamp]
- Last Saved: [timestamp]

## Context Loaded
- Sprint Status: [loaded/missing] — Sprint [N]
- Active Stories: [comma-separated list]
- Locked Decisions: [N loaded, last-read: timestamp]
- Additional Context: [list]

## Git State
- Status: [clean/dirty]
- Last Commit: [hash] [message]
- Last Verified: [timestamp]

## Active Violations
[list or "None"]

## Checkpoint History (last 5)
- [timestamp]: [gate] — [pass/block/bypass]

## File Counters
- mistakes_file_counter: [N]
- last_mistakes_file: [path or none]
- summary_file_counter: [N]
- last_summary_file: [path or none]
```

## Auto-Save Triggers

Save automatically when:
- Any violation detected
- Any gate passes or blocks
- Locked decision added or updated
- Story state changes
- Mistakes file generated
- Summary file generated
- Session end detected (any trigger from checkpoint-enforcement.md)
