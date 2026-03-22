# Document Verification v0.2.0

## Purpose
Verify all Builder outputs before allowing progression. This capability implements the "read-before-validate" principle - never accept completion claims without reading actual output files.

## On Activation

1. **Load Context**
   - Load current session state and last completed BMAD command
   - Review locked decisions and standards
   - Identify what type of document was produced

2. **Determine Verification Type**
   Based on the last BMAD command:
   - **create-story** → Story file verification
   - **create-architecture** → Architecture document verification
   - **create-prd** → PRD verification
   - **create-epics-and-stories** → Epics/stories verification
   - **code-review** → Code review triage verification
   - **retrospective** → Retrospective report verification

## Verification Framework

### Universal Verification Steps
For any document produced by a Builder:

1. **Read the Actual File**
   ```
   CRITICAL: Never accept Builder's completion claim without reading the file
   
   - Load the actual file that was supposedly created/modified
   - Verify file exists and is not empty
   - Check basic file structure and readability
   ```

2. **Validate Against Locked Decisions**
   ```
   - Cross-reference every decision against locked-decisions.md
   - Flag any contradictions or scope creep
   - Verify architectural alignment
   - Check for violations of established boundaries
   ```

3. **Validate Against Project Context**
   ```
   - Ensure alignment with project-context.md
   - Verify consistency with sprint goals
   - Check technical feasibility within current architecture
   - Validate scope against current story/epic boundaries
   ```

4. **Quality Standards Check**
   ```
   - Verify document follows required format/template
   - Check for completeness of required sections
   - Validate technical accuracy and consistency
   - Ensure clarity and actionable content
   ```

## Document-Specific Verifications

### Story File Verification (create-story)
```
## Story File Validation Checklist

**Required Elements:**
- Story ID follows naming convention
- Acceptance criteria are specific and testable
- Technical requirements are clear and bounded
- Dependencies are properly identified
- Scope aligns with epic and sprint goals

**Validation Against Standards:**
- No scope creep beyond current story boundaries
- Technical approach aligns with architecture
- All acceptance criteria can be tested
- Story is ready for development assignment

**Common Issues to Flag:**
- Missing acceptance criteria
- Vague technical requirements
- Dependencies not identified
- Scope includes future story items
- Contradicts locked decisions
```

### Architecture Document Verification (create-architecture)
```
## Architecture Document Validation

**Required Elements:**
- Clear architectural decisions with rationale
- Component relationships and boundaries
- Technology choices with justification
- Integration points and interfaces
- Non-functional requirements addressed

**Validation Against Standards:**
- Aligns with locked architectural decisions
- No conflicts with existing system architecture
- Technology choices are consistent with project standards
- Integration points are properly defined
- Scalability and maintainability considerations

**Common Issues to Flag:**
- Missing rationale for architectural decisions
- Conflicts with existing architecture
- Technology choices inconsistent with project
- Undefined integration interfaces
- Missing non-functional requirements
```

### PRD Verification (create-prd)
```
## PRD Validation Checklist

**Required Elements:**
- Clear problem statement and user needs
- Specific acceptance criteria
- Success metrics and KPIs
- Scope boundaries and exclusions
- Dependencies and constraints

**Validation Against Standards:**
- Problem statement aligns with project goals
- Success metrics are measurable and realistic
- Scope is properly bounded and achievable
- Dependencies are identified and feasible
- No conflicts with locked decisions

**Common Issues to Flag:**
- Vague problem statement
- Non-measurable success criteria
- Scope creep beyond project boundaries
- Missing or unclear dependencies
- Contradicts established product strategy
```

### Code Review Triage Verification (code-review)
```
## Code Review Triage Validation

**Required Elements:**
- Clear classification of each finding (patch/defer/intent_gap/bad_spec)
- Specific remediation instructions for each finding
- Priority assessment and impact analysis
- Verification criteria for fixes

**Validation Against Standards:**
- Classifications follow escalation paths correctly
- Remediation instructions are actionable
- Priority assessment considers impact and complexity
- No findings outside current story scope (unless flagged as future scope)

**Common Issues to Flag:**
- Incorrect classification of findings
- Missing remediation instructions
- Findings outside current story scope not properly flagged
- Priority assessment doesn't consider impact
- Missing verification criteria
```

## Verification Outcomes

### PASS - Document is Valid
```
## Verification Result: PASS

**Document:** [document name]
**Type:** [document type]
**Verified:** [timestamp]

**Summary:**
Document passes all verification checks and is ready for progression.

**Next Steps:**
- Commit the document to version control
- Proceed with next BMAD command
- Update session state with verification result

**Command:**
```
[Next BMAD command]
```
```

### FAIL - Document Has Issues
```
## Verification Result: FAIL - Issues Found

**Document:** [document name]
**Type:** [document type]
**Issues Found:** [number]

**Critical Issues (Must Fix):**
1. [Issue 1] - [specific description and impact]
2. [Issue 2] - [specific description and impact]

**Minor Issues (Should Fix):**
1. [Issue 1] - [specific description]
2. [Issue 2] - [specific description]

**Required Actions:**
1. [Specific action to fix issue 1]
2. [Specific action to fix issue 2]

**Blocking:** Progression is blocked until critical issues are resolved.

**After Fixing:**
Re-run document verification before proceeding.
```

### SCOPE_ISSUE - Document Outside Current Scope
```
## Verification Result: SCOPE_ISSUE

**Document:** [document name]
**Issue:** Document includes elements outside current story scope

**Out-of-Scope Elements:**
- [Element 1] - belongs to [future story/epic]
- [Element 2] - belongs to [future story/epic]

**Recommendation:**
Split document into:
1. Current scope elements (proceed with these)
2. Future scope elements (move to appropriate future story)

**Action Required:**
Remove out-of-scope elements or create separate documents for future work.
```

## Integration with Workflow

### Before Checkpoint Enforcement
- Always run document verification before allowing checkpoint validation
- Block progression if verification fails
- Provide specific remediation instructions

### Before Instruction Generation
- Use verification results to generate precise instructions
- Include specific file locations and issues in instructions
- Provide clear criteria for verification success

### Memory Integration
After verification:
1. Update `session-state.md` with verification results
2. Store verification findings in memory
3. Track patterns of common issues
4. Update locked decisions if verification reveals new decisions

## Automated Script Support

```python
# document-verifier.py - Automated verification helper
python scripts/document-verifier.py \
  --document-type [story|architecture|prd|epics|code-review|retrospective] \
  --file-path [path/to/document] \
  --locked-decisions [path/to/locked-decisions.md] \
  --project-context [path/to/project-context.md]
```

## Error Handling

**File Not Found:**
```
Document verification failed: File not found at [path]

Builder claimed to create/modify [document] but file doesn't exist.

**Required Action:**
Ask Builder to re-run the command and ensure file is actually created.
```

**File Empty/Corrupted:**
```
Document verification failed: File is empty or corrupted at [path]

**Required Action:**
Builder must re-create the document with proper content.
```

**Locked Decisions Conflict:**
```
Document verification failed: Conflicts with locked decisions

**Conflicts:**
- [Conflict 1]
- [Conflict 2]

**Required Action:**
Either:
1. Update document to align with locked decisions
2. Formally update locked decisions (requires consensus)
```

This verification gate ensures that no bad artifacts progress through the BMAD workflow, maintaining quality and preventing scope creep.
