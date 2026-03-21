# Session Initialization

## Purpose
Initialize advisor session, assess current state, and establish monitoring context.

## Session Start Questions

### Context Gathering
Ask the Coordinator:
1. **What BMAD work has been done in this session so far?**
   - Commands executed
   - Agents involved
   - Outputs produced

2. **Are there any ongoing tasks or incomplete work?**
   - Partially completed commands
   - Waiting for responses
   - Blocked actions

3. **What was the last completed action?**
   - Exact command or action
   - Timestamp if known
   - Any outputs generated

### State Assessment
Based on responses:
- Determine session phase (discovery, planning, execution, review)
- Identify agents currently active or recently used
- Note any potential violations or checkpoint issues

### Locked Decisions Loading
- Use bmad-crew-locked-decisions skill to retrieve current locked decisions
- Review decisions relevant to current session phase
- Note any decisions that might affect current work

### Session Report Creation
Create session report with:
```yaml
---
session_id: "advisor-session-{timestamp}"
coordinator: "{user_name}"
start_time: "{timestamp}"
phase: "{determined_phase}"
locked_decisions_loaded: true
gates:
  session_init: IN_PROGRESS
  violation_detection: LOCKED
  checkpoint_enforcement: LOCKED
  instruction_generation: LOCKED
---
```

## Initialization Completion

### Validation Checklist
- [ ] Coordinator responses documented
- [ ] Session phase identified
- [ ] Locked decisions loaded and reviewed
- [ ] Session report created
- [ ] Initial state assessment complete

### Ready State
When initialization complete:
1. Update session report gate status to `session_init: UNLOCKED`
2. Present summary to Coordinator:
   - Current session state
   - Relevant locked decisions
   - Next monitoring steps
3. State: "Advisor initialized. Ready to monitor for violations and enforce checkpoints."

## Error Handling

### Incomplete Information
If Coordinator cannot provide complete information:
- Proceed with available information
- Note gaps in session report
- Monitor for clarification as session progresses

### Locked Decision Conflicts
If current state conflicts with locked decisions:
- Immediately flag the conflict
- Provide correction instructions
- Do not proceed until conflict resolved
