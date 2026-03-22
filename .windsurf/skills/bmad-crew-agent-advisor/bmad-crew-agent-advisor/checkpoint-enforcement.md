# Checkpoint Enforcement

## Purpose
Validate all required gates before phase transitions and before any "open a new chat" instruction. Every output-producing BMAD command has a checkpoint. None are optional.

## Commit Checkpoint — Full Lifecycle (IDEA-002)

Every command that produces output files requires a commit before the next session opens.

**Validate automatically using:**
```
{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/git-validator.py --check-commits-after-output
```

**Commands covered:**
| Command | Commit required before |
|---------|----------------------|
| brainstorming | Any new session |
| create-prd | architecture or epics session |
| create-architecture | epics or dev session |
| create-epics-and-stories | first dev session |
| create-story | dev-story session |
| dev-story | code-review session |
| code-review (patches) | next create-story session |
| retrospective | next sprint session |

**If uncommitted changes detected:**
```
CHECKPOINT BLOCKED: Uncommitted output from [last command].

Run:
git add -A && git commit -m "[descriptive message]"

Then tell me the commit hash to proceed.
```

## Git Validation (IDEA-004)

The Advisor runs git validation automatically — never asks the Coordinator to run git commands and paste back.

**On session start:**
```
{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/git-validator.py --check-clean
```

**Before any phase transition:**
```
{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/git-validator.py --validate-commits --since-last-checkpoint
```

**After Builder claims completion:**
```
{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/git-validator.py --verify-commit --expected-files [list]
```

Report results directly. If git is dirty: block and give exact commit command. Do not ask the Coordinator to investigate.

## Phase Transition Checkpoints

### create-story → dev-story
Required before giving the dev-story instruction:
1. ✓ Story file exists at expected path
2. ✓ Advisor has read the file (not just confirmed its existence)
3. ✓ Validated against locked decisions, architecture, project-context.md
4. ✓ No violations found (or violations resolved)
5. ✓ Story file committed (git log confirms)
6. ✓ Locked decisions re-read (IDEA-012)

All six must pass. If any fail: block with specific fix instructions.

### dev-story → code-review
Required before giving the code-review instruction:
1. ✓ Git shows new commits since story start
2. ✓ All changed files committed
3. ✓ Story file updated with implementation notes
4. ✓ Locked decisions re-read (IDEA-012)

### code-review → next create-story
Execute these steps IN ORDER before giving the next create-story instruction:

1. Verify all patch findings addressed and committed — check git log for patch commit hash
2. Verify no unresolved bad_spec or intent_gap findings
3. **GENERATE mistakes file now** — do not skip, do not ask — write `ADVISOR_SESSION_MISTAKES_NNN.md` to `{bmad_builder_output_folder}/bmad-crew-sessions/` using mistakes-file.md instructions
4. **GENERATE summary file now** — do not skip, do not ask — write `SUM-00X-[project]-advisor-story-[N]-summary.md` to `{bmad_builder_output_folder}/bmad-crew-sessions/` using the Phase Summary Files template below
5. Only after both files are written: tell the Coordinator to instruct the Builder to update sprint-status.yaml and commit, then give the create-story command

The Advisor writes these files itself. It does not ask the Coordinator to generate them.

## Phase Summary Files (IDEA-008)

A summary file is mandatory before any "open a new chat" instruction at a phase boundary. The Advisor does not give the next-chat instruction until the summary is written and confirmed saved.

**Trigger conditions:**
- End of brainstorming phase → planning
- End of planning phase → implementation
- End of story cycle → next story
- Coordinator says "we are done", "open a new chat", closes story, or makes final commit of a phase (IDEA-013)

**File naming:** `SUM-00X-[project]-advisor-[phase]-summary.md`
(X = incrementing number, stored in session-state.md)

**Content:**
```markdown
# Session Summary — [phase] — [timestamp]

## What Was Validated
- [list of documents read and validated]

## Corrections Issued
- [list of corrections given to Builder]

## Locked Decisions Carried Forward
- [decisions referenced or updated this session]

## Issues Found and Resolved
- [violations caught and their resolutions]

## Next Action
[single confirmed next command]
```

**Save to:** `{bmad_builder_output_folder}/bmad-crew-sessions/`

**Do not give the next-chat instruction until:**
```
Summary saved to [path]. Confirm saved, then open a new chat and run:

/bmad-bmm-[next-command]
```

## Session-End Detection (IDEA-013)

Trigger summary file generation when any of these occur (not just phase boundaries):

- Coordinator says "we are done" / "that's it for today" / "wrapping up"
- Coordinator explicitly closes a story
- Coordinator says "open a new chat" without the Advisor prompting it
- A commit is made that completes the current phase work
- No activity for a phase that appears complete in sprint-status.yaml

On detection:
1. Check if a summary already exists for this session
2. If not: generate summary file before yielding
3. Offer the next-command instruction
4. Update session-state.md with session end timestamp

## Session Scope Rule

**One Advisor session = one story cycle.**

After giving the create-story command, the Advisor ends its own session:

```
Session complete for story [N.M]. Close this chat.

Open a fresh Advisor session for the next story:

/bmad-crew-agent-advisor
```

This is mandatory. Context drift in long sessions causes the Advisor to lose its rules and improvise. Short sessions keep context clean.

## Checkpoint Response Formats

### PASS
```
CHECKPOINT PASSED: [phase transition]
[Single next instruction in plain text]

[command in code block]
```

### BLOCK
```
CHECKPOINT BLOCKED: [specific failure]
[One sentence: why this blocks]
[Exact action required]
```

### BYPASS (Coordinator override)
```
BYPASS DOCUMENTED: [what was bypassed] — [timestamp]
Risk: [one sentence]
Proceeding under Coordinator authority.
```
