# Instruction Generation

## Purpose
Generate exact Coordinator instructions after gates pass. One line of plain text, one command in a code block. No options menus. No step-by-step when one line covers it.

## Output Format (IDEA-005)

**Always:**
- Plain text: the instruction sentence
- Code block: the command only — nothing else inside it

**Correct format:**
```
Story 2.3 validated. Commit the story file, then open a new chat and run:

/bmad-bmm-dev-story
```

**Never:**
- Instructions inside code blocks
- Multiple commands in one response
- "Would you like me to..." options
- Step-by-step numbered lists when one sentence covers it
- Arguments added to BMAD commands

**BMAD command syntax — never add arguments:**
- `/bmad-bmm-dev-story` ✓
- `/bmad-bmm-dev-story story-3.1` ✗

---

## Code Review Escalation Paths (IDEA-014)

### PATCH — Fix in current review session
```
PATCH required: [finding description]

Fix this in the current review session — do not hand back to dev-story.

Tell the Builder: [exact correction instruction]

Verify: [how to confirm the fix]
```

### DEFER — Acknowledge and move on
```
DEFER: [finding description]
[One sentence: why this is deferred]

Document in technical debt backlog and proceed to next finding.
```

### INTENT_GAP — Requires Coordinator decision

**Stop the review. This requires Coordinator judgment before proceeding.**

```
INTENT_GAP detected: [finding description]

This may indicate a fundamental misunderstanding of requirements or a scope issue.

Options:
A. Clarify intent and continue review
B. Stop review, update story requirements, re-run dev-story

Verify your understanding before choosing: [specific question to resolve the ambiguity]

Note: Verify this finding before acting — the Advisor may have misread the intent. (IDEA-011)
```

### BAD_SPEC — Block progression, require story correction

**Block all progression until story is corrected.**

```
BAD_SPEC: [finding description]

Progression blocked. The story specification is incorrect or incomplete.

Required actions:
1. Tell the Builder to stop — do not commit current work
2. Open a new chat and run:

/bmad-bmm-create-story

3. Correct the story to address: [specific gap]
4. Re-validate the story before re-running dev-story

Do not proceed to code review completion until the spec is corrected.
```

---

## Locked Decisions Re-Reference (IDEA-012)

Before every next-command recommendation, re-read `locked-decisions.md`.

In long sessions the decisions loaded at init drift out of the active context window. The file is always the source of truth.

**Before giving any instruction that touches architecture or scope:**
1. Read `{project-root}/_bmad/bmad-crew/locked-decisions.md`
2. Check the proposed next step against each active decision
3. If a conflict is found: flag it before giving the next command

**This is not optional in long sessions.** The Advisor re-reads the file, does not rely on what was loaded at session start.

---

## Self-Doubt Flag (IDEA-011)

When the Advisor produces complex validation results — especially intent_gap or bad_spec classifications — it flags its own output for Coordinator review before action.

**Add to any complex validation output:**
```
Note: Verify this finding before acting — complex classifications can be wrong.
```

**When to add the flag:**
- intent_gap classification
- bad_spec classification
- Any finding that would block progression or require re-running a BMAD command
- Validation results involving multiple documents cross-referenced

**When not to add the flag:**
- Simple commit checkpoint failures
- Missing file errors
- Clean gate passes

The flag does not change the instruction — it adds one sentence telling the Coordinator to sanity-check before acting on it.

---

## Standard Instruction Templates

### Next story command
```
[Story N.M] validated. Commit the story file, then open a new chat and run:

/bmad-bmm-dev-story
```

### Next code review
```
Implementation committed ([hash]). Open a new chat and run:

/bmad-bmm-code-review
```

### All patches resolved
```
All findings resolved and committed. [Generate mistakes file first — see mistakes-file.md]

Open a new chat and run:

/bmad-bmm-create-story
```

### Phase boundary
```
[Phase] complete. [Summary file saved to path]. Open a new chat and run:

/bmad-[next-phase-command]
```
