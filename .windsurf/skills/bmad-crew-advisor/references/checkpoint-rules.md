# Checkpoint Rules

## Commit Checkpoints

### Output Commit Requirement
**Rule**: Every BMAD command that produces output must be committed before next session opens
**Verification**: `git log` shows new commit hash after command completion
**Failure Mode**: No new commit or commit doesn't contain expected outputs
**Correction**: Commit outputs with descriptive message before proceeding

### Clean Git Status
**Rule**: Git status must be clean before starting new BMAD commands
**Verification**: `git status` shows "working tree clean"
**Failure Mode**: Uncommitted changes, untracked files, or staged changes
**Correction**: Commit or stash changes before proceeding

### Commit Message Standards
**Rule**: Commit messages must follow BMAD format and reference the work completed
**Verification**: Commit message includes command type and brief description
**Failure Mode**: Generic commit messages, missing command reference
**Correction**: Amend commit with proper message format

## Summary Checkpoints

### Phase Boundary Summaries
**Rule**: Summary file must be produced at every phase boundary before next workflow command
**Verification**: Summary file exists in expected location with required sections
**Failure Mode**: Missing summary, incomplete summary, wrong location
**Correction**: Create complete summary before proceeding to next phase

### Summary Content Requirements
**Rule**: Summaries must include completed work, decisions made, and next steps
**Verification**: Summary contains all required sections and is comprehensive
**Failure Mode**: Incomplete sections, missing decisions, unclear next steps
**Correction**: Complete missing sections before proceeding

### Summary Commit
**Rule**: Summary files must be committed before phase transition
**Verification**: Summary file appears in git log for current session
**Failure Mode**: Summary not committed or committed after phase transition
**Correction**: Commit summary before proceeding to next phase

## Code Review Checkpoints

### Review Completion
**Rule**: Code review patches must be identified and addressed in same session
**Verification**: All review feedback incorporated or documented for future work
**Failure Mode**: Outstanding review items, unaddressed feedback
**Correction**: Address all review feedback before claiming completion

### Review Commit
**Rule**: Code review fixes must be committed in same session as original work
**Verification**: Review fixes appear in same commit session as original code
**Failure Mode**: Review fixes delayed to future session or missing
**Correction**: Commit review fixes in current session

### Review Quality
**Rule**: Code reviews must be thorough and address all relevant issues
**Verification**: Review covers functionality, style, security, and performance
**Failure Mode**: Superficial review, missing critical issues
**Correction**: Conduct comprehensive review before approval

## Session Checkpoints

### Session Initialization
**Rule**: Each session must start with clear initialization and state assessment
**Verification**: Session report created with initial state documented
**Failure Mode**: Missing session initialization, unclear starting state
**Correction**: Initialize session properly before proceeding

### Session Closure
**Rule**: Each session must end with proper closure and state documentation
**Verification**: Session report updated with final state and outcomes
**Failure Mode**: Missing session closure, incomplete documentation
**Correction**: Document session completion before ending

### Session Handoff
**Rule**: Session handoffs must include complete state transfer
**Verification**: All relevant information documented for next session
**Failure Mode**: Missing handoff information, incomplete state transfer
**Correction**: Complete handoff documentation before session end

## Checkpoint Verification Commands

### Git Status Check
```bash
git status --porcelain
```
**Expected Output**: Empty (clean working tree)

### Commit Verification
```bash
git log --oneline -5
```
**Expected Output**: New commit with appropriate message

### File Existence Check
```bash
ls -la {expected_file_path}
```
**Expected Output**: File exists with appropriate permissions

### Content Verification
```bash
grep -c "required_section" {summary_file}
```
**Expected Output**: Count > 0 for each required section

## Checkpoint Failure Responses

### Immediate Failure Response
1. **State checkpoint requirement**: "Commit checkpoint failed: No new commit hash found"
2. **Show current vs required**: "Current: git log shows old hash. Required: new hash after claimed completion"
3. **Provide exact fix**: Step-by-step commands to satisfy checkpoint
4. **Verification command**: How to confirm checkpoint now passes

### Batch Failure Response
When multiple checkpoints fail:
1. **List all failures**: Prioritize by severity
2. **Group fixes by type**: Commit fixes, summary fixes, review fixes
3. **Provide sequential instructions**: Fix in logical order
4. **Verify each checkpoint**: Confirm each passes before proceeding

## Checkpoint Exceptions

### Emergency Exceptions
**Rule**: Critical issues may require bypassing non-critical checkpoints
**Requirements**: Explicit Coordinator authorization, documented reason
**Documentation**: Note exception in session report with justification

### Development Exceptions
**Rule**: Development work may have modified checkpoint requirements
**Requirements**: Updated locked decisions, clear communication of changes
**Documentation**: Update checkpoint rules and communicate to all agents

## Checkpoint Monitoring

### Continuous Monitoring
- Monitor checkpoint compliance throughout session
- Alert on potential checkpoint failures before they occur
- Provide proactive guidance to maintain checkpoint compliance

### Trend Analysis
- Track checkpoint failure patterns
- Identify systemic issues
- Recommend process improvements based on checkpoint data
