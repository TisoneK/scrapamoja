# First-Run Setup

## Initialize Memory Sidecar

1. **Create memory directory structure:**
   ```
   {project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/
   ├── access-boundaries.md
   ├── session-state.md
   ├── locked-decisions.md
   └── index.md
   ```

2. **Create access-boundaries.md:**
   ```markdown
   # Access Boundaries for BMAD Crew Advisor

   ## Read Access
   - {project-root}/_bmad/bmad-crew/
   - {bmad_builder_output_folder}/bmad-crew-sessions/
   - User-provided context documents

   ## Write Access
   - {project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/
   - {bmad_builder_output_folder}/bmad-crew-sessions/
   - {project-root}/_bmad/bmad-crew/locked-decisions.md

   ## Deny Zones
   - Direct code execution
   - Git operations (validation only)
   - Coordinator/Executor boundary crossing
   ```

3. **Create session-state.md:**
   ```markdown
   # Session State

   ## Current Phase
   - Phase: initialization
   - Last Completed Gate: none
   - Session Start: {timestamp}

   ## Context Loaded
   - Sprint Status: pending
   - Story File: pending
   - Architecture Doc: pending
   - Brainstorming Session: pending

   ## Active Violations
   - None detected

   ## Session Notes
   - First run - memory initialized
   ```

4. **Create locked-decisions.md:**
   ```markdown
   # Locked Decisions

   ## Module Decisions
   - Agent: BMAD Crew Advisor
   - Module: bmad-crew
   - Created: {timestamp}

   ## Session Rules
   - Context required before advisory work
   - No escalation mechanism
   - Coordinator decides on violations

   ## Technical Decisions
   - Interactive only (no autonomous mode)
   - MVP scope (essential validation only)
   - Memory persistence for session state and locked decisions
   ```

5. **Create index.md:**
   ```markdown
   # BMAD Crew Advisor Configuration

   ## User Preferences
   - User Name: {user_name}
   - Communication Language: {communication_language}
   - Document Output Language: {document_output_language}

   ## Paths
   - Session Reports: {bmad_builder_output_folder}/bmad-crew-sessions/
   - Locked Decisions: {project-root}/_bmad/bmad-crew/locked-decisions.md
   - Memory Sidecar: {project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/

   ## Session History
   - Sessions Completed: 0
   - Last Session: Never
   ```

## Validation

After creating memory structure:
1. Verify all files exist and are readable
2. Test access boundaries compliance
3. Validate locked decisions location exists
4. Confirm session reports folder is writable

## Ready State

Once memory is initialized and validated, the agent is ready for session initiation. The next activation will load this memory and proceed with context gathering.
