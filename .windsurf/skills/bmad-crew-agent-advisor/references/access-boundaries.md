# Access Boundaries for Crew Advisor

## Read Access
- `{project-root}/_bmad/bmad-crew/` — module files, locked decisions, stories
- `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/` — own memory
- `{bmad_builder_output_folder}/bmad-crew-sessions/` — session reports, mistakes files, summaries
- `sprint-status.yaml` (project root) — sprint tracking
- `project-context.md` (project root) — project context
- `docs/` (project root) — proposals, specs (discovery only, not exhaustive reads)
- `proposals/` (project root) — feature proposals (discovery only)
- `{project-root}/_bmad-output/` — brainstorming, planning artifacts
- User-provided context documents (any path Coordinator explicitly provides)

## Write Access
- `{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/` — own memory only
- `{bmad_builder_output_folder}/bmad-crew-sessions/` — session reports, mistakes files, summaries
- `{project-root}/_bmad/bmad-crew/locked-decisions.md` — locked decisions updates only

## Deny Zones
- No direct code writing or modification
- No git operations (validation scripts only — never `git commit`, `git push`)
- No cross-Coordinator/Builder boundary actions
- No writing to any path outside Write Access above
- No reading files larger than 500KB without Coordinator approval
- No reading files outside the project root
