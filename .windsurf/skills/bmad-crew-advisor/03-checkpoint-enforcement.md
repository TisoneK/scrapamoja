Language: {communication_language}
Output Language: {document_output_language}

# Checkpoint Enforcement

## Purpose
Validate critical checkpoints and ensure BMAD process compliance.

## On Activation

1. **Read session report** to understand current context
2. **Load checkpoint rules** from `references/checkpoint-rules.md`
3. **Run checkpoint validation:**
   - Use bmad-crew-checkpoint-enforcer skill to validate current state
   - Check all required checkpoints based on session progress

4. **Validate critical checkpoints:**

**Every BMAD command that produces output:**
- Must be committed before next session opens
- Check git log for new commit hash

**Phase boundaries:**
- Summary file must be produced before next workflow command
- Verify summary exists and contains required content

**Code reviews:**
- Git log must show new commit hash after claimed completion
- Code review patches must be fixed in same session

5. **Document checkpoint status:**
   - Update session report with checkpoint validation results
   - For each failed checkpoint: provide exact correction instructions

## Checkpoint Types

**Commit Checkpoints:**
- New commit hash present in git log
- All output files committed
- Clean git status before new session

**Summary Checkpoints:**
- Phase summary exists at phase boundaries
- Summary contains required sections
- Summary is committed before proceeding

**Code Review Checkpoints:**
- Review patches identified and fixed
- No outstanding code review issues
- Fixes committed in same session

## Response Pattern

For each failed checkpoint:
1. **State the checkpoint requirement**
2. **Show current status vs required state**
3. **Provide exact commands** to fix the checkpoint
4. **Specify when checkpoint is considered passed**

## Progression Condition
Proceed to instruction generation when:
- All checkpoints pass, OR
- All failed checkpoints have clear correction instructions

## On User Approval
Route to `04-instruction-generation.md`
