# Access Boundaries for BMAD Crew Advisor v0.2.0

## Read Access

### Project Core Files
- `{project-root}/_bmad/bmad-crew/` - Module files and locked decisions
- `{project-root}/_bmad/bmad-crew/locked-decisions.md` - Locked decisions (critical)
- `{project-root}/_bmad/bmad-crew/stories/` - Story files for context
- `{project-root}/sprint-status.yaml` - Sprint status and progress
- `{project-root}/project-context.md` - Project context and goals

### Output and Session Files
- `{bmad_builder_output_folder}/bmad-crew-sessions/` - Session reports and outputs
- `{project-root}/_bmad-output/` - Planning and brainstorming artifacts
- `{project-root}/docs/` - Documentation, proposals, and design specs

### Auto-Discovery Targets (v0.2.0)
- `{project-root}/proposals/` - Feature proposals and specifications
- `{project-root}/docs/evidence/` - Evidence and research documents
- Files matching patterns: `*.proposal.md`, `FEATURE_*.md`, `brainstorming-*.md`
- Files in known locations: `_bmad-output/planning-artifacts/`, `_bmad-output/brainstorming/`

### Memory and Configuration
- `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/` - Agent memory
- `{project-root}/_bmad/bmb/config.yaml` - BMAD configuration (via bmad-init)

## Write Access

### Agent Memory
- `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/` - All memory files
- `session-state.md` - Current session tracking
- `discovery-cache.md` - Auto-discovery results cache
- `verification-results.md` - Document verification history
- `escalation-log.md` - Code review escalation tracking

### Session Reports
- `{bmad_builder_output_folder}/bmad-crew-sessions/` - Session reports and summaries
- Session summary files with naming convention: `SUM-XXX-[project]-advisor-[phase]-summary.md`
- Mistakes files: `ADVISOR_SESSION_MISTAKES_XXX.md`

### Locked Decisions Updates
- `{project-root}/_bmad/bmad-crew/locked-decisions.md` - Only for decision updates, not initial creation

## Deny Zones

### Direct Code Modification
- Never modify source code files directly
- No implementation work or code fixes
- No changes to development artifacts

### Git Operations
- No direct git commands (commit, push, merge)
- Only validation via scripts (`git-validator.py`)
- No branch operations or repository modifications

### Cross-Role Boundaries
- No Executor-level implementation tasks
- No Coordinator decision-making (only guidance)
- No role assignments outside BMAD framework

### System-Level Operations
- No system file modifications outside project boundaries
- No dependency installation or environment changes
- No network operations or external API calls

## v0.2.0 Enhanced Boundaries

### Auto-Discovery Constraints
- Only scan within project root directory
- Respect .gitignore patterns during discovery
- No access to sensitive configuration files
- Limit file size reading to prevent memory issues

### Document Verification Constraints
- Read-only access to Builder output files
- No modification of documents during verification
- Only report issues, don't fix them automatically

### Code Review Escalation Constraints
- No automatic classification changes
- No implementation of patches or fixes
- Only provide guidance and instruction generation

## Access Patterns

### Sequential Access
1. Load access-boundaries.md first (always)
2. Load memory state for session context
3. Load project files for verification
4. Write memory updates after operations
5. Generate reports in designated output locations

### Concurrent Access Safety
- Use file locking for memory file updates
- Atomic writes for critical state changes
- Backup memory files before major updates

### Error Handling
- Log access violations to memory
- Fail gracefully when access is denied
- Report boundary violations to Coordinator

## Security Considerations

### Data Privacy
- No access to user credentials or secrets
- No reading of sensitive configuration files
- Respect file system permissions

### Integrity Protection
- Validate file paths before access
- Prevent path traversal attacks
- Verify file types before processing

### Audit Trail
- Log all file access operations
- Track boundary violations
- Monitor for suspicious access patterns

These access boundaries ensure the advisor operates within its designated role while providing enhanced v0.2.0 capabilities safely and effectively.
