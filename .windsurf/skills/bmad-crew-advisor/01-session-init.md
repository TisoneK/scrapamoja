Language: {communication_language}
Output Language: {document_output_language}
Output Location: {bmad_builder_output_folder}

# Session Initialization

## Purpose
Initialize advisor session, assess current state, and load locked decisions for ongoing monitoring.

## On Activation

1. **Greet the Coordinator** and confirm session start
2. **Assess current session state:**
   - Ask: "What BMAD work has been done in this session so far?"
   - Ask: "Are there any ongoing tasks or incomplete work?"
   - Ask: "What was the last completed action?"

3. **Load locked decisions:**
   - Use bmad-crew-locked-decisions skill to retrieve current locked decisions
   - Review any locked decisions that might affect current session

4. **Initialize session tracking:**
   - Create session report at `{bmad_builder_output_folder}/advisor-session-{timestamp}.md`
   - Document initial state and locked decisions

5. **Present assessment:**
   - Summarize current session state
   - Highlight any locked decisions relevant to current work
   - State: "Advisor initialized. Ready to monitor for violations and enforce checkpoints."

## Progression Condition
Proceed to violation detection when user confirms: "Session state looks correct, proceed with monitoring" OR user provides corrections to initial assessment

## On User Approval
Route to `02-violation-detection.md`
