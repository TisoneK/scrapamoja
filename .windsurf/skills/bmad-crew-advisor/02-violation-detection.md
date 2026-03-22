Language: {communication_language}
Output Language: {document_output_language}

# Violation Detection

## Purpose
Monitor BMAD session for role violations, process violations, and quality violations.

## On Activation

1. **Read session report** to understand current context
2. **Load violation types** from `references/violation-types.md`
3. **Run session validation:**
   - Use bmad-crew-session-validator skill to check current state
   - Capture all violations found (role, process, quality)

4. **Analyze violations:**
   - For each violation found:
     - Identify violation type and severity
     - Cite the specific rule being violated
     - Determine the exact correction needed

5. **Document findings:**
   - Update session report with violation analysis
   - For each violation: state violation, cite rule, provide correction

## Violation Categories

**Role Violations:**
- Advisor becoming Executor
- Executor self-certifying completion

**Process Violations:**
- Opening new session before previous work is committed
- Skipping code review
- Running dev-story without clean git status

**Quality Violations:**
- Executor claiming completion without new commit hash
- Documents confirmed without being read

## Response Pattern

For each violation found:
1. **State the violation clearly**
2. **Cite the specific rule** from violation-types.md
3. **Provide exact correction instructions** in a code block
4. **Specify next action** for Coordinator

## Progression Condition
Proceed to checkpoint enforcement when:
- No violations found, OR
- All violations have been addressed with clear instructions

## On User Approval
Route to `03-checkpoint-enforcement.md`
