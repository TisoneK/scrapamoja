# Workflow Gates

## Gate Definitions

### Session Initialization Gate
**Requirement**: Session must be properly initialized before monitoring begins
**Check**: Locked decisions loaded, session report created, initial assessment complete
**Pass Condition**: User confirms session state is accurate
**Fail Action**: Do not proceed to violation detection until initialization complete

### Violation Detection Gate
**Requirement**: All violations must be identified and classified before instruction generation
**Check**: Session validation complete, violations documented with rule citations
**Pass Condition**: Either no violations found OR all violations have clear correction instructions
**Fail Action**: Do not proceed to checkpoint enforcement until violations are properly documented

### Checkpoint Enforcement Gate
**Requirement**: All applicable checkpoints must be validated before proceeding
**Check**: Commit checkpoints, summary checkpoints, code review checkpoints
**Pass Condition**: All checkpoints pass OR all failures have exact fix instructions
**Fail Action**: Do not proceed to instruction generation until checkpoints are validated

### Instruction Generation Gate
**Requirement**: Instructions must be exact, copy-pasteable, and contextually appropriate
**Check**: Instructions follow assessment→instruction→next-action pattern, include rule citations
**Pass Condition**: Instructions are ready for Coordinator to execute
**Fail Action**: Refine instructions until they meet precision requirements

## Gate Progression Logic

### Sequential Progression
Gates must be completed in order:
1. Session Initialization → 2. Violation Detection → 3. Checkpoint Enforcement → 4. Instruction Generation

### Feedback Loops
- **Instruction Generation → Violation Detection**: After instructions executed, return to violation detection to verify fixes
- **Checkpoint Enforcement → Session Initialization**: If session state changes significantly, reinitialize
- **Violation Detection → Checkpoint Enforcement**: Violations may affect checkpoint requirements

### Gate Bypass Conditions
**No bypass conditions exist. Gates are absolute and must be satisfied without exception.**

## Gate State Management

### Gate States
- **LOCKED**: Cannot proceed, prerequisite not met
- **UNLOCKED**: Can proceed to next gate
- **WARNING**: Can proceed but with noted risks

### State Persistence
Gate states are maintained in the session report:
```yaml
gates:
  session_init: UNLOCKED
  violation_detection: LOCKED
  checkpoint_enforcement: LOCKED
  instruction_generation: LOCKED
```

### State Transitions
- **LOCKED → UNLOCKED**: Requirements satisfied, documented in session report
- **UNLOCKED → LOCKED**: New information invalidates previous completion
- **WARNING**: Documented risks that Coordinator accepts

## Gate Validation Rules

### Validation Requirements
Each gate must validate:
1. **Inputs**: Required data from previous gates is available
2. **Processing**: Gate logic executed completely
3. **Outputs**: Required artifacts created and documented
4. **Quality**: Outputs meet precision and completeness standards

### Failure Modes
- **Input Missing**: Return to previous gate to generate missing input
- **Processing Error**: Retry gate with error handling, escalate if persistent
- **Output Invalid**: Regenerate output with clearer requirements

## Gate Integration with Locked Decisions

### Decision Documentation
When locked decisions affect gates:
1. Document the decision in session report
2. Reference decision ID in gate validation
3. Include decision impact in gate output

**Note**: Locked decisions provide context but do not override gate requirements. Gates must still be satisfied.
