# Agentfile Project — IDE Agent Instructions

This is an **Agentfile project**. When working in this repo, you must follow the slash command protocol below for all workflow operations. Do not improvise — the protocol is exact.

---

## Slash Command Protocol

### `/agentfile:run <workflow-name> <args>`
Run an existing workflow in IDE mode.

1. Read `workflows/<workflow-name>/workflow.yaml`
2. Read `workflows/<workflow-name>/scripts/ide/instructions.md` if it exists
3. Load each step's agent file as your persona, load the skill file as context
4. Execute steps sequentially using your LLM — **do not run any scripts in `scripts/cli/`**
5. The only scripts you may execute are in `scripts/ide/` (e.g. `register.sh`) — these are API-key-free file operations

### `/agentfile:create <workflow-name> <description>`
Create a new workflow using the `workflow-creator` pipeline.

**This is NOT a free-form task. Follow these exact steps:**

1. Set `WORKFLOW_NAME` = the name argument
2. Set `WORKFLOW_REQUEST` = `"Create a workflow named <n>. <description>"`
3. Read `workflows/workflow-creator/scripts/ide/instructions.md` — follow it exactly
4. Generate `RUN_ID` = current UTC timestamp `YYYY-MM-DDTHH-MM-SS` (e.g. `2026-02-23T10-41-22`).
5. Set `ARTIFACT_DIR` = `artifacts/{workflow_name}/{run_id}/`
6. Execute the full workflow-creator pipeline:
   - **Step 0 (Init):** Create `ARTIFACT_DIR`. Write initial `manifest.json` using `skills/generate-manifest.md`. Status: `generating`, all steps `pending`.
   - **Step 1 (Clarify):** Load `agents/analyst.md` + `skills/ask-clarifying.md`. Produce `{ARTIFACT_DIR}/01-clarification.md`. Update manifest. Wait for human approval.
   - **Step 2 (Design):** Load `agents/architect.md` + `skills/design-workflow.md`. Input: `{ARTIFACT_DIR}/01-clarification.md`. Produce `{ARTIFACT_DIR}/02-design.md`. Update manifest. Wait for human approval.
   - **Step 3 (Generate YAML):** Load generator + `skills/generate-yaml.md`. Produce `{ARTIFACT_DIR}/03-workflow.yaml`. Register in manifest.
   - **Step 4 (Generate Agents):** Load generator + `skills/generate-agent.md`. Produce `{ARTIFACT_DIR}/04-agents/`. Register in manifest.
   - **Step 5 (Generate Skills):** Load generator + `skills/generate-skill.md`. Produce `{ARTIFACT_DIR}/05-skills/`. Register in manifest.
   - **Step 6 (Generate Scripts):** Load generator + `skills/generate-dual-scripts.md`. Produce `{ARTIFACT_DIR}/06-scripts/`. Register in manifest.
   - **Step 7 (Review):** Load `agents/reviewer.md` + `skills/review-workflow.md`. Produce `{ARTIFACT_DIR}/07-review.md`. Set manifest `status: validated`. Wait for human approval.
   - **Step 8 (Promote):** Run `bash workflows/workflow-creator/scripts/ide/register.sh {ARTIFACT_DIR}` (Unix) or `pwsh ... {ARTIFACT_DIR}` (Windows). Promotes to `workflows/{name}/`, archives to `outputs/{name}/{run_id}/build/`. No API key needed.

**Never** create a `.md` file directly in `workflows/`. **Never** skip steps. **Never** run `scripts/cli/` scripts.

### `/agentfile:list`
Scan `workflows/*/workflow.yaml`. For each, read `name` and `description`. Return a formatted list. No LLM call needed.

---

## Hard Rules

- **Never create files directly in `workflows/`** — new workflows are always created via the `workflow-creator` pipeline
- **Never run `scripts/cli/` scripts in IDE mode** — they require `ANTHROPIC_API_KEY` and will fail
- **Always read `scripts/ide/instructions.md`** before executing any workflow
- **Always wait at `gate: human-approval` steps** — do not proceed without confirmation
- **Generation artifacts go in `artifacts/<workflow-name>/<run-id>/`** — never directly in `workflows/` or `outputs/`
