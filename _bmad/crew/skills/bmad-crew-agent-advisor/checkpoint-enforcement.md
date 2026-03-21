# Checkpoint Enforcement

## Purpose
Validate required artifacts and compliance before allowing phase transitions. This capability ensures BMAD process integrity by enforcing checkpoint gates.

## On Activation

1. **Load Session Context**
   - Load current session state from memory
   - Identify current phase and attempted transition
   - Load locked decisions for reference

2. **Determine Checkpoint Type**
   Based on transition:
   - **Brainstorming → Planning** - Ideas validation
   - **Planning → Architecture** - Requirements completeness
   - **Architecture → Implementation** - Design readiness
   - **Implementation → Code Review** - Implementation completeness
   - **Code Review → Completion** - Quality validation

## Checkpoint Validation Process

### Step 1: Artifact Existence Check
Use `checkpoint-validator.py` to verify required artifacts:
```python
python scripts/checkpoint-validator.py --phase [current-phase] --check-artifacts
```

**Required Artifacts by Phase:**

**Brainstorming Complete:**
- Brainstorming session notes
- Key insights captured
- Decision log updated

**Planning Complete:**
- Product brief or PRD
- User stories defined
- Acceptance criteria clear

**Architecture Complete:**
- Architecture document
- Technical decisions documented
- Integration approach defined

**Implementation Complete:**
- Code implemented
- Unit tests passing
- Documentation updated

**Code Review Complete:**
- Review completed
- Issues resolved
- Quality gates passed

### Step 2: Quality Validation
For each required artifact:
1. **Read and validate** the artifact content
2. **Check against standards** and locked decisions
3. **Verify completeness** and accuracy
4. **Identify gaps** or issues

### Step 3: Git Status Validation
Use `git-validator.py` to ensure clean state:
```python
python scripts/git-validator.py --check-clean --validate-commits
```

**Required Git State:**
- Clean working directory (no uncommitted changes)
- Meaningful commit messages
- Proper branch structure (if applicable)

### Step 4: Violation Check
Review active violations from session state:
1. **Check for unresolved violations**
2. **Assess impact on phase transition**
3. **Determine if violations block progression**

## Enforcement Decisions

### ALLOW TRANSITION
When:
- All required artifacts exist and are valid
- Git status is clean
- No blocking violations
- Quality standards met

**Response:**
```
**CHECKPOINT PASSED:** [Phase] → [Next Phase]

All requirements satisfied:
✅ Required artifacts complete and validated
✅ Git status clean
✅ No blocking violations
✅ Quality standards met

You may proceed to [Next Phase].
```

### BLOCK TRANSITION
When:
- Required artifacts missing or invalid
- Git status not clean
- Blocking violations exist
- Quality standards not met

**Response:**
```
**CHECKPOINT BLOCKED:** [Phase] → [Next Phase]

**Issues requiring resolution:**
❌ [Specific issue 1]
❌ [Specific issue 2]
❌ [Specific issue 3]

**Required actions:**
1. [Exact instruction for issue 1]
2. [Exact instruction for issue 2]
3. [Exact instruction for issue 3]

**Validation commands:**
```bash
python scripts/checkpoint-validator.py --phase [current-phase] --recheck
```

Complete these actions before attempting phase transition.
```

### CONDITIONAL PROCEED
When:
- Minor issues exist but don't block progression
- Work can continue in parallel with fixes
- Issues documented for later resolution

**Response:**
```
**CHECKPOINT PASSED WITH CONDITIONS:** [Phase] → [Next Phase]

You may proceed, but address these items:
⚠️ [Minor issue 1] - [Timeline for resolution]
⚠️ [Minor issue 2] - [Timeline for resolution]

**Documented in session state** for tracking.
```

## Memory Updates

After checkpoint evaluation:
1. **Update session-state.md** with checkpoint result
2. **Record artifacts validated** and their status
3. **Note any conditions** or requirements
4. **Update phase status** if transition allowed

## Special Cases

### Emergency Exceptions
If Coordinator needs to bypass checkpoint:
1. **Document the exception** clearly
2. **Record the reason** for bypass
3. **Note the risks** introduced
4. **Update session state** with exception details

**Response:**
```
**CHECKPOINT BYPASS DOCUMENTED:** [Phase] → [Next Phase]

**Exception recorded:**
- Reason: [Coordinator's reason]
- Risks: [Identified risks]
- Mitigation: [Planned mitigation]

**Note:** This exception has been documented in session state and locked decisions.
```

### Partial Completion
When some but not all requirements met:
1. **Identify what's complete**
2. **Specify what's missing**
3. **Provide options** for proceeding
4. **Document the decision**

## Integration Points

This capability works with:
- **session-init.md** - Validate initial session setup
- **violation-detection.md** - Check for violations before transitions
- **instruction-generation.md** - Provide detailed remediation instructions
- **External skills** - Use bmad-crew-checkpoint-enforcer for complex validation

## Validation Scripts

The checkpoint-validator.py script handles:
- Artifact existence verification
- File structure validation
- Basic content quality checks
- Git status integration

For complex validation, delegate to external skills as needed.
