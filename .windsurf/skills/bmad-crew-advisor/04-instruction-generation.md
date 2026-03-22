Language: {communication_language}
Output Language: {document_output_language}

# Instruction Generation

## Purpose
Generate exact "tell the Executor" instructions that the Coordinator can paste directly.

## On Activation

1. **Read session report** to understand violations and checkpoint status
2. **Load instruction patterns** from `references/instruction-patterns.md`
3. **Generate instructions based on findings:**

**If violations found:**
- Generate exact correction instructions for each violation
- Format as copy-pasteable commands for Coordinator
- Include context about why the instruction is needed

**If checkpoints failed:**
- Generate step-by-step instructions to fix each checkpoint
- Include exact git commands, file operations, or validation steps
- Specify verification commands to confirm checkpoint passes

**If session is clean:**
- Generate "proceed with next step" instruction
- Include any locked decisions that affect next actions
- Provide guidance on what to monitor next

4. **Instruction format:**
```
Assessment first, then instruction in code block, then next action:

[ASSESSMENT]
Current status: [brief summary]

[INSTRUCTION]
Tell the Executor:
```
[exact command or instruction to paste]
```

[NEXT ACTION]
[what Coordinator should do after Executor completes instruction]
```

5. **Update session report:**
   - Document all generated instructions
   - Track which violations/checkpoints were addressed
   - Note any new locked decisions established

## Response Templates

**Violation Correction Template:**
```
Assessment: [Violation type] detected - [brief description]

Tell the Executor:
```
[exact instruction to fix violation]
```

Next Action: Verify the fix by [verification method]
```

**Checkpoint Fix Template:**
```
Assessment: [Checkpoint name] failed - [what's missing]

Tell the Executor:
```
[step-by-step commands to fix checkpoint]
```

Next Action: Confirm [checkpoint] passes before proceeding
```

## Progression Condition
Continue monitoring session - this stage runs continuously as the session progresses. Return to violation detection after each major action or when Coordinator requests new assessment.

## On Completion
Update session report with final status and remain available for ongoing monitoring.
