# Mistakes File Generation (IDEA-001)

## Purpose
After each story cycle completes (code-review patches committed, before next create-story), the Advisor automatically produces a mistakes file. This is mandatory — not prompted by the Coordinator.

## Trigger

Generate when ALL of the following are true:
1. code-review triage validated by Advisor
2. All patch findings addressed
3. All patches committed (git log confirms)
4. No unresolved bad_spec or intent_gap findings

This happens automatically before the next create-story instruction.

## File Naming

`ADVISOR_SESSION_MISTAKES_[NNN].md`

NNN = incrementing 3-digit number, zero-padded. Current counter stored in session-state.md under `mistakes_file_counter`.

Example sequence: `ADVISOR_SESSION_MISTAKES_001.md`, `ADVISOR_SESSION_MISTAKES_002.md`

## Save Location

`{bmad_builder_output_folder}/bmad-crew-sessions/`

## Content Template

```markdown
# Advisor Session Mistakes — [story ID] — [timestamp]

## Story
[Story ID and title]

## Violations Detected This Cycle
[List each violation caught, with category and when it was caught]
- VIOLATION: [type] — [description] — Caught at: [gate]

## Corrections Issued
[Each correction given to the Builder or Coordinator]
- [What was wrong] → [What was instructed]

## Code Review Findings Summary
| Finding | Classification | Resolution |
|---------|---------------|------------|
| [description] | patch/defer/intent_gap/bad_spec | [how resolved] |

## Process Notes
[Any escalations, bypasses, or unusual decisions this cycle]

## Carry-Forward Reminders
[Any patterns worth watching in the next story cycle]
```

## If No Violations

Still generate the file — a clean cycle is worth recording:

```markdown
# Advisor Session Mistakes — [story ID] — [timestamp]

## Story
[Story ID and title]

## Result
Clean cycle. No violations detected. No corrections required.

## Code Review
[N] findings: [X patch, Y defer, Z intent_gap, 0 bad_spec] — all resolved.
```

## After Generating

Tell the Coordinator:
```
Mistakes file saved: [path/ADVISOR_SESSION_MISTAKES_NNN.md]
```

Then give the next create-story instruction. Do not wait for acknowledgement.

## Memory Update

After generating, update session-state.md:
```
mistakes_file_counter: [incremented value]
last_mistakes_file: [path]
```
