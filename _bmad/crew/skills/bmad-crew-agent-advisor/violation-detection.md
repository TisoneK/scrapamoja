# Violation Detection

## Purpose
Monitor BMAD development sessions for role violations, process violations, and quality violations. This capability provides real-time oversight to catch issues before the Coordinator notices them.

## On Activation

1. **Load Current Session State**
   - Load memory from `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/session-state.md`
   - Verify context is loaded and session is active
   - Load locked decisions for reference

2. **Establish Monitoring Scope**
   Based on loaded context, determine:
   - **Active workflow phase** (brainstorming, planning, architecture, implementation, code review)
   - **Participants and their roles** (Coordinator, agents, developers)
   - **Current focus area** (what work is being done)

3. **Violation Categories**

### Role Violations
Monitor for:
- **Agent boundary crossing** - Agents performing Coordinator duties
- **Coordinator overreach** - Coordinator performing implementation tasks
- **Role confusion** - Unclear who should be doing what
- **Unauthorized decisions** - Decisions made outside established authority

### Process Violations  
Monitor for:
- **Skipping phases** - Moving to next phase without completing current
- **Missing checkpoints** - Not validating required artifacts
- **Workflow deviations** - Not following established BMAD process
- **Documentation gaps** - Missing required documentation

### Quality Violations
Monitor for:
- **Standards non-compliance** - Not following established standards
- **Technical debt accumulation** - Ignoring quality issues
- **Incomplete work** - Claiming completion when work is partial
- **Decision contradictions** - New decisions conflicting with locked decisions

## Detection Process

### Real-time Monitoring
1. **Listen for role indicators** in conversation:
   - "I think we should..." (decision making)
   - "Let me implement..." (implementation)
   - "I'll handle that..." (task ownership)

2. **Check process compliance**:
   - Verify phase completion criteria met
   - Validate required artifacts exist
   - Check checkpoint compliance

3. **Quality assessment**:
   - Compare against locked decisions
   - Verify standards compliance
   - Check for technical debt indicators

### Violation Confirmation
Before flagging a violation:
1. **Verify context** - Ensure you understand the full situation
2. **Check rules** - Reference locked decisions and standards
3. **Confirm impact** - Ensure this is actually a violation, not a valid exception

## Violation Reporting

When a violation is detected:

### Immediate Response Format
```
**VIOLATION DETECTED:** [Type] - [Brief Description]

**What happened:** [Clear description of the violation]
**Why it matters:** [Impact on the session/quality]
**What to do:** [Exact instructions for resolution]
```

### Examples

**Role Violation:**
```
**VIOLATION DETECTED:** Role Boundary - Agent implementing code

**What happened:** The tech-writer agent is writing implementation code, which crosses the Coordinator/Executor boundary.

**Why it matters:** This creates confusion about ownership and bypasses the proper implementation workflow.

**What to do:** 
1. Ask the tech-writer to stop implementation
2. Have the Coordinator assign implementation to the appropriate agent
3. Ensure the tech-writer focuses on documentation tasks
```

**Process Violation:**
```
**VIOLATION DETECTED:** Process - Skipping Architecture Phase

**What happened:** Moving to implementation without completing architecture documentation.

**Why it matters:** This risks technical debt and misaligned implementation.

**What to do:**
1. Pause implementation work
2. Complete architecture phase requirements
3. Validate architecture artifacts before proceeding
```

**Quality Violation:**
```
**VIOLATION DETECTED:** Quality - Contradicting Locked Decision

**What happened:** New approach conflicts with locked decision about using REST APIs.

**Why it matters:** This undermines architectural consistency and creates integration risks.

**What to do:**
1. Reference locked decision: [specific decision]
2. Explain why current approach conflicts
3. Suggest aligning with locked decision or formally updating it
```

## Memory Updates

After detecting violations:
1. **Update session-state.md** with active violations
2. **Track resolution status** for each violation
3. **Note patterns** for recurring issues

## Escalation Policy

**No escalation mechanism** - The Advisor flags violations and provides exact instructions. The Coordinator decides whether to act. The Advisor never overrides Coordinator decisions.

## Continuous Monitoring

The Advisor should:
1. **Monitor continuously** during active sessions
2. **Provide real-time feedback** on violations
3. **Maintain violation log** in memory
4. **Update session state** as violations are resolved

## Integration Points

This capability works with:
- **checkpoint-enforcement.md** - Validate violations before phase transitions
- **instruction-generation.md** - Provide detailed remediation instructions
- **External skills** - Use bmad-crew-session-validator for complex validation
