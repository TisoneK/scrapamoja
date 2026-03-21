# Violation Types

## Role Violations

### Advisor Becoming Executor
**Rule**: Advisors must not execute BMAD commands directly
**Detection**: Advisor attempts to run commands, make decisions, or take actions meant for Executor
**Severity**: Critical
**Correction**: Return to advisory role, provide instruction to Coordinator for Executor

### Executor Self-Certifying Completion
**Rule**: Executors must not self-certify their own work completion
**Detection**: Executor claims work is done without external validation or commit evidence
**Severity**: High
**Correction**: Require external validation, commit evidence, or Coordinator confirmation

### Agent Role Confusion
**Rule**: Each agent must stay within their defined role boundaries
**Detection**: Agent performing actions outside their role (e.g., Coordinator executing commands)
**Severity**: Medium
**Correction**: Clarify roles, provide role-appropriate instructions

## Process Violations

### New Session Before Commit
**Rule**: All output from previous session must be committed before opening new session
**Detection**: Git status shows uncommitted changes from previous session when starting new work
**Severity**: Critical
**Correction**: Commit all previous work before proceeding with new session

### Skipping Code Review
**Rule**: Code changes must be reviewed before being considered complete
**Detection**: Code changes committed without review process or review acknowledgment
**Severity**: High
**Correction**: Require code review, incorporate feedback, recommit if needed

### Dev-Story Without Clean Git Status
**Rule**: dev-story commands require clean git status to start
**Detection**: Running dev-story with uncommitted changes present
**Severity**: High
**Correction**: Commit or stash changes before running dev-story

### Session Boundary Violations
**Rule**: Sessions must have clear boundaries and proper handoffs
**Detection**: Overlapping sessions, unclear session transitions
**Severity**: Medium
**Correction**: Establish clear session boundaries, document handoffs

## Quality Violations

### Completion Without Commit Hash
**Rule**: Claimed completion must have corresponding commit hash in git log
**Detection**: Executor claims completion but no new commit exists
**Severity**: Critical
**Correction**: Require commit before accepting completion claim

### Documents Confirmed Without Reading
**Rule**: Documents must be read before being confirmed as reviewed
**Detection**: Agent confirms document review without evidence of reading
**Severity**: High
**Correction**: Require actual document reading with specific references

### Incomplete Output
**Rule**: All required outputs must be present and complete
**Detection**: Missing required sections, incomplete artifacts
**Severity**: Medium
**Correction**: Complete missing outputs before proceeding

### Quality Standard Violations
**Rule**: Work must meet established quality standards
**Detection**: Outputs below quality thresholds, missing required elements
**Severity**: Medium
**Correction**: Improve quality to meet standards before proceeding

## Violation Severity Levels

### Critical (Session Halt)
- Must be resolved before any further work
- Cannot proceed with current session until fixed
- Examples: Role violations, commit requirement failures

### High (Block Progress)
- Blocks current task progression
- Must be resolved before continuing current work
- Examples: Process violations, quality violations

### Medium (Note and Fix)
- Should be fixed but doesn't halt current work
- Can be addressed alongside current task
- Examples: Role confusion, minor quality issues

### Low (Document and Monitor)
- Note for future reference
- Monitor for patterns
- Examples: Minor process deviations

## Violation Response Patterns

### Immediate Response
- State violation clearly
- Cite specific rule
- Provide exact correction instruction
- Specify verification method

### Pattern Detection
- Track repeated violations by same agent
- Identify systemic issues
- Recommend process improvements

### Escalation
- Critical violations: Immediate halt
- Repeated violations: Coordinator notification
- Pattern violations: Process review

## Violation Documentation

### Session Report Entry
```yaml
violations:
  - type: "role_violation"
    subtype: "advisor_becoming_executor"
    severity: "critical"
    rule_reference: "advisors_must_not_execute_commands"
    detected_at: "2025-03-21T10:30:00Z"
    correction_provided: true
    resolved: false
```
