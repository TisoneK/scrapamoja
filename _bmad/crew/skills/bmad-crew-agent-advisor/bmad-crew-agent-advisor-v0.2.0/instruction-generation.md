# Instruction Generation v0.2.0

## Purpose
Generate exact, actionable Coordinator instructions for violation remediation, process compliance, and code review escalations. This capability reduces cognitive load by providing precise guidance with intelligent escalation paths.

## On Activation

1. **Load Context**
   - Load current session state and violations
   - Review locked decisions and standards
   - Load verification results from document-verification.md
   - Identify specific issue requiring instruction

2. **Determine Instruction Type**
   Based on the issue:
   - **Violation remediation** - Fix specific violations
   - **Process compliance** - Follow correct workflow
   - **Quality improvement** - Meet quality standards
   - **Decision alignment** - Align with locked decisions
   - **Code review escalation** - Handle finding classifications (NEW v0.2.0)

## Code Review Escalation Paths (NEW v0.2.0)

### Classification-Based Escalation

**PATCH - Fix in Current Review Session**
```
## Code Review: Patch Required

**Finding:** [specific finding description]
**Classification:** patch
**Impact:** Can be fixed immediately in current review

**Required Action:**
Fix this issue now in the current code review session:

1. [Specific step 1 to fix the issue]
2. [Specific step 2 to fix the issue]
3. [Specific step 3 to verify the fix]

**Why this matters:** [brief impact explanation]

**Verification:** [how to confirm the fix is complete]

**Do NOT hand back to dev-story** - this is a review-level fix.
```

**DEFER - Acknowledge and Move On**
```
## Code Review: Finding Deferred

**Finding:** [specific finding description]
**Classification:** defer
**Impact:** Non-critical or out of current scope

**Action:** Acknowledge and move on

**Rationale:** [why this finding is deferred]
- [Reason 1]
- [Reason 2]

**Documentation:** Note this finding for future consideration:
- Add to technical debt backlog
- Schedule for appropriate future sprint
- Document in project notes

**Proceed to next finding or complete review.
```

**INTENT_GAP - May Require Re-planning**
```
## Code Review: Intent Gap Detected

**Finding:** [specific finding description]
**Classification:** intent_gap
**Impact:** May indicate fundamental misunderstanding or scope issue

**IMMEDIATE ACTION:**
Stop the review process. This finding requires Coordinator decision.

**Analysis:**
This finding suggests a potential gap between:
- What was implemented vs. what was intended
- Current story scope vs. actual requirements
- Technical approach vs. architectural goals

**Coordinator Decision Required:**
Choose one option:

1. **Continue with current implementation** 
   - Accept the current approach
   - Document the intent gap for future reference
   - Proceed with review completion

2. **Modify the implementation**
   - Re-plan the approach to align with intent
   - May require additional development work
   - Re-run code review after changes

3. **Update the story/specification**
   - The implementation may be correct, but the story was wrong
   - Update story to match what was actually needed
   - Re-validate story before proceeding

**My Recommendation:** [provide specific recommendation based on context]

**Which option would you like to pursue?**
```

**BAD_SPEC - Requires Story Correction**
```
## Code Review: Bad Specification Detected

**Finding:** [specific finding description]
**Classification:** bad_spec
**Impact:** Story specification is incorrect or incomplete

**BLOCKING:** Progression is BLOCKED until story is corrected.

**Issue Analysis:**
The story specification has these problems:
- [Problem 1] - [specific issue with story]
- [Problem 2] - [specific issue with story]
- [Problem 3] - [specific issue with story]

**Required Actions:**
1. **STOP** - Do not proceed with code review
2. **CORRECT STORY** - Update the story file to fix these issues:
   - [Specific correction 1]
   - [Specific correction 2]
   - [Specific correction 3]
3. **REVALIDATE** - Run story validation after corrections
4. **RE-DEVELOP** - May require additional development work
5. **RE-REVIEW** - Run new code review after story is fixed

**Story Correction Template:**
```
Update story [story-id] to fix these specification issues:

1. [Section to update]:
   Current: [current text]
   Corrected: [corrected text]

2. [Section to update]:
   Current: [current text]  
   Corrected: [corrected text]
```

**After Story Correction:**
1. Commit the corrected story file
2. Open a new chat and run:
```
/bmad-bmm-dev-story [story-id]
```

**Do NOT proceed with current code review** - the implementation is based on a bad specification.
```

## Enhanced Instruction Framework

### Structure for All Instructions
```
## [Action Category]: [Specific Issue]

**What needs to happen:** [Clear, concise statement of required action]

**Step-by-step instructions:**
1. [First specific action]
2. [Second specific action]
3. [Third specific action]

**Why this matters:** [Brief explanation of impact/importance]

**Verification:** [How to confirm the action is complete]

**Next Command:** [Exact next BMAD command in code block]
```

### Violation Remediation Instructions

#### Role Boundary Violations
```
## Role Correction: Agent Boundary Violation

**What needs to happen:** Redirect agent to proper role boundaries

**Step-by-step instructions:**
1. Stop the current agent action immediately
2. Say: "That task is outside your role boundaries. Let me handle this."
3. Assign the task to the appropriate role/person
4. Reinforce the agent's proper role: "Your focus should be on [proper role]."

**Why this matters:** Role boundaries prevent confusion and ensure proper workflow execution.

**Verification:** Agent is working within their defined role and not overstepping.

**Next Command:**
```
[Continue with appropriate next command]
```
```

#### Process Violations
```
## Process Compliance: Complete Missing Phase

**What needs to happen:** Complete the [Phase Name] phase before proceeding

**Step-by-step instructions:**
1. Stop current work in [Current Phase]
2. Return to [Missing Phase]
3. Complete these required artifacts:
   - [Artifact 1]: [Specific requirement]
   - [Artifact 2]: [Specific requirement]
4. Run automated validation: `python scripts/checkpoint-validator.py --phase [Missing Phase]`
5. Once validated, proceed to [Current Phase]

**Why this matters:** Each phase builds necessary foundations for the next. Skipping creates risks.

**Verification:** Checkpoint validator confirms phase completion.

**Next Command:**
```
[Appropriate next BMAD command]
```
```

### Quality Standards Instructions

#### Document Quality Issues
```
## Quality Compliance: Fix Document Issues

**What needs to happen:** Address document verification failures

**Step-by-step instructions:**
1. Review verification report for [document name]
2. Fix these critical issues:
   - [Issue 1]: [Specific fix required]
   - [Issue 2]: [Specific fix required]
3. Update document with corrections
4. Re-run document verification: `python scripts/document-verifier.py --document-type [type] --file-path [path]`
5. Commit corrected document

**Why this matters:** Quality standards ensure consistency and prevent downstream issues.

**Verification:** Document verification passes without critical issues.

**Next Command:**
```
[Continue with workflow after document is fixed]
```
```

## Output Format Standards (IDEA-005 Extensions)

### Command Format Rules
```
ALWAYS follow these format rules:

**CORRECT:**
Plain text instructions explaining what to do, followed by:

```
/exact-bmad-command
```

**INCORRECT:**
```
Plain text and command mixed in same block
```

**INCORRECT:**
/bmad-bmm-dev-story story-name.md  # Never add arguments to commands
```

### Instruction Placement
```
**Instructions:** Always in plain text
**Commands:** Always in separate code blocks
**Arguments:** Never add arguments to BMAD commands
```

## Memory Integration

After generating instructions:
1. **Update session-state.md** with issued instructions
2. **Track instruction effectiveness** 
3. **Note patterns** for recurring instruction types
4. **Update locked decisions** if instructions lead to new decisions
5. **Store escalation outcomes** for future reference

## Integration with v0.2.0 Features

### Document Verification Integration
- Use verification results to generate specific instructions
- Include exact file paths and line numbers in instructions
- Provide clear criteria for verification success

### Auto-Discovery Integration  
- Use discovered context to make instructions more relevant
- Reference specific artifacts found during discovery
- Align instructions with current project state

### Code Review Integration
- Handle all four classification types appropriately
- Provide clear escalation paths for each type
- Ensure instructions prevent similar issues in future

## Error Handling

**Ambiguous Instructions:**
```
My instructions may need clarification. Here's what I need to know:

[Specific question about context]
[Specific question about constraints]
[Specific question about desired outcome]

Please provide these details so I can give you exact instructions.
```

**Conflicting Requirements:**
```
I detected conflicting requirements in the current situation:

[Conflict 1] vs [Conflict 2]

**Resolution needed:**
1. [Option to resolve conflict 1]
2. [Option to resolve conflict 2]
3. [Option to escalate decision]

Which approach should I take?
```

This enhanced instruction generation capability provides precise, actionable guidance while handling the complexity of code review escalations and maintaining strict output format standards.
