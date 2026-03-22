# Session Init

## Purpose
Initialize advisory session. The Advisor reads all available context before presenting options — it never asks the Coordinator to load files manually.

## On Activation

### Step 1 — Load Memory
- Load `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/session-state.md`
- Load access boundaries
- If session already in progress: read state and resume from last completed gate

### Step 2 — Run Discovery Script
```
{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/session-validator.py --discover
```
This returns a file index only. Do not stop here — Step 3 reads the actual files.

### Step 3 — Read All Discovered Files

Open and read every file from the discovery output. Do not skip any. Do not summarise by count.

**Read in this order:**

1. `sprint-status.yaml` — if found, read fully and extract sprint number, story list, statuses
2. `{project-root}/_bmad/bmad-crew/stories/*.md` — read each story with status ready-for-dev or in-progress
3. `project-context.md` — read fully if found
4. `{project-root}/_bmad/bmad-crew/locked-decisions.md` — read fully if found
5. `_bmad-output/planning-artifacts/prd.md` — read fully if found
6. `_bmad-output/planning-artifacts/*.md` — read every other file in this folder
7. `_bmad-output/brainstorming/*.md` — read the most recent file
8. `docs/evidence/*.md` — read any IDEAS, SPEC, MISTAKES, or PLAN files found
9. `bmad-builder-creations/` — note what has been built (folder names only, no deep read)

After reading each file, note in one line: filename — what it is and what phase it represents.

### Step 4 — Detect Project Type

Based on what was read, determine which workflow applies:

**BMM project** (building software):
- Has `sprint-status.yaml`
- Has stories in `_bmad/bmm/stories/` or similar
- Has architecture doc, epics, code in the repo
- Next step is in the story lifecycle: create-story → dev-story → code-review

**BMB project** (building agents, workflows, or modules):
- Has `_bmad-output/planning-artifacts/` with PRD or product brief
- Has `bmad-builder-creations/` with built skills
- No sprint-status.yaml, no stories
- Next step is in the builder lifecycle: build → optimize → distribute

**Unknown / fresh:**
- No artifacts found
- Ask the Coordinator what they are building before suggesting a next step

### Step 5 — Present Findings

Show what was actually read with one-line summaries, then present options based on detected project type:

```
Read:
- [filename]: [one-line summary]
- [filename]: [one-line summary]
...

Project type detected: [BMM / BMB / unknown]
Current phase: [analysis / planning / build / optimize / distribute / unknown]

1. Continue — [specific: what was last completed and exact next command]
2. Start over — [only if genuinely nothing active]
3. Something else — tell me
```

Option 1 must name the exact next command — never "start fresh with sprint planning" for a BMB project that already has a PRD and builder outputs.

### Step 6 — Route Based on Choice

**Option 1 — Continue:**
- For BMM: resume story lifecycle, run git validation, give next story command
- For BMB: identify what has been built vs what remains (build remaining skills, optimize, or distribute)
- Run git validation: `{python} {project-root}/_bmad/crew/skills/bmad-crew-agent-advisor/scripts/git-validator.py --check-clean`
- Flag dirty git before anything else

**Option 2 — Start over:**
- Confirm no active work exists
- Ask: BMM or BMB project?
- Route to appropriate starting command

**Option 3 — Something else:**
- Load specific requested context
- Proceed with targeted advisory

### Step 7 — Update Session State
Write to `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/session-state.md`:
```markdown
## Current Phase
- Project Type: [BMM / BMB]
- Phase: [detected phase]
- Last Completed Gate: session-init
- Session Start: [timestamp]

## Context Loaded
- Sprint Status: [loaded/missing]
- Active Stories: [list or none]
- Locked Decisions: [N loaded]
- Planning Artifacts: [list]
- Builder Creations: [list]

## Git State
- Status: [clean/dirty]
- Last Commit: [hash and message]
```

## Error Handling

**No artifacts found:**
```
No project artifacts found. Are we starting a new BMM software project or a new BMB agent/module project?
```

**Git is dirty at session start:**
```
VIOLATION: Uncommitted changes detected before session start.
Commit or stash all changes before we proceed.
```
