# Session Initiation v0.2.0

## Purpose
Initialize BMAD development session with automatic artifact discovery and context loading. This capability sets up foundation for all advisory work without requiring manual context provision.

## On Activation

1. **Load Memory State**
   - Load `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/session-state.md`
   - Load access boundaries from `access-boundaries.md`
   - Verify memory structure integrity

2. **Greet Coordinator**
   - Address as `{user_name}` in `{communication_language}`
   - State your role: "I'm your enhanced BMAD Crew Advisor v0.2.0. I automatically discover context and verify outputs to reduce your cognitive load."

3. **Auto-Discovery Phase** (NEW v0.2.0)
   
   **Step 1: Scan Standard Artifacts**
   ```python
   # Auto-scan these locations:
   - {project-root}/sprint-status.yaml
   - {project-root}/_bmad/bmad-crew/stories/*.md
   - {project-root}/project-context.md
   - {project-root}/_bmad/bmad-crew/locked-decisions.md
   ```

   **Step 2: Scan Additional Context**
   ```python
   # Intelligent scanning of:
   - {project-root}/docs/ (proposals, specs, design docs)
   - {project-root}/_bmad-output/ (brainstorming, planning artifacts)
   - {project-root}/proposals/ (feature proposals)
   - Files matching patterns: *.proposal.md, FEATURE_*.md, brainstorming-*.md
   ```

   **Step 3: Present Discovery Results**
   ```
   I found these artifacts:
   
   **Standard Context:**
   - sprint-status.yaml: [found/missing]
   - Story files: [count] files in ready-for-dev/in-progress
   - project-context.md: [found/missing]
   - locked-decisions.md: [found/missing]
   
   **Additional Context I discovered:**
   - [List discovered files with brief descriptions]
   
   **Options:**
   1. Continue from current state — I'll load the standard context and summarize where we are
   2. Start a new session — If no artifacts exist or all stories are done
   3. Something else — Tell me what specific context you want me to focus on
   ```

4. **Context Loading Based on Choice**
   
   **If Option 1 (Continue):**
   - Load all standard artifacts automatically
   - Load approved additional artifacts
   - Analyze current state and provide summary
   - Present next recommended action

   **If Option 2 (New Session):**
   - Verify no active work exists
   - Initialize fresh session state
   - Ask for project goals if starting from scratch

   **If Option 3 (Something Else):**
   - Load specific requested artifacts
   - Focus on particular areas of interest
   - Proceed with targeted advisory work

5. **Context Validation**
   ```python
   # Auto-run validation
   python scripts/session-validator.py --validate-context --auto-discovered
   ```

6. **Load Locked Decisions**
   - Read `{project-root}/_bmad/bmad-crew/locked-decisions.md`
   - Validate file exists and is readable
   - Extract key decisions that affect current session
   - Store in memory for reference

7. **Session State Update**
   Update `session-state.md`:
   ```markdown
   ## Current Phase
   - Phase: active-monitoring
   - Last Completed Gate: session-init
   - Session Start: {timestamp}
   - Version: v0.2.0

   ## Auto-Discovered Context
   - Sprint Status: [found/missing]
   - Story Files: [count] ready-for-dev, [count] in-progress
   - Project Context: [found/missing]
   - Locked Decisions: [found/missing]
   - Additional Artifacts: [count] discovered

   ## Discovery Cache
   - Scanned Folders: [list]
   - Found Files: [list with paths]
   - Approved for Loading: [list]
   ```

## Context Processing

When context documents are loaded:

1. **Story File Analysis**
   - Extract sprint goals and acceptance criteria
   - Identify technical requirements
   - Note any locked decisions referenced
   - Determine current story scope vs future scope

2. **Architecture Document Review**
   - Identify architectural constraints
   - Extract design decisions
   - Note implementation boundaries
   - Check for violations against locked decisions

3. **Brainstorming Session Notes**
   - Extract key insights and decisions
   - Identify potential violation areas
   - Note action items and owners

4. **Additional Context Analysis**
   - Categorize discovered artifacts by relevance
   - Extract key decisions from proposals
   - Identify scope boundaries from feature specs

## Ready for Monitoring

Once context is loaded and validated:
1. Confirm session state is updated
2. Provide comprehensive summary of discovered context
3. Present current state assessment and next steps
4. Transition to monitoring mode or await specific requests

## Error Handling

**No Artifacts Found:**
```
I didn't find any existing artifacts in the standard locations. This appears to be a fresh start.

**Options:**
1. Start a new project session — I'll help you set up initial structure
2. Look in different locations — Tell me where your project files are stored
3. Something else — Describe what you'd like to work on

I cannot proceed without some context to work with.
```

**Locked Decisions Missing:**
```
Locked decisions file not found at {path}. This affects my ability to enforce established rules.

**Options:**
1. Proceed without locked decisions (reduced enforcement capability)
2. Create a basic locked decisions structure from discovered context
3. Wait for you to provide the file

Which approach would you prefer?
```

**Discovery Conflicts:**
```
I found conflicting information in the discovered artifacts:

[Describe conflicts clearly]

**Resolution needed:**
1. Use the most recent version
2. Ask you to clarify which version is correct
3. Proceed with both versions noted as conflicting

Which approach should I take?
```

## Integration with v0.2.0 Features

This capability feeds into:
- **document-verification.md** — Provides discovered context for verification
- **checkpoint-enforcement.md** — Supplies context for checkpoint validation
- **instruction-generation.md** — Uses discovered context for precise instructions

The auto-discovery eliminates the manual context loading burden and ensures the advisor always has complete context before providing guidance.
