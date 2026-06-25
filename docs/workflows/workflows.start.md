<!-- workflows/workflows.start.md -->

## ⚠️ MANDATORY INITIALIZATION - READ FIRST

Before presenting ANY options, you MUST:
1. Read `docs/workflows/rules.md` (general rules)
2. Read `docs/workflows/workflows.start.md` (this file)
3. ONLY THEN present options to user

# Scrapamoja Workflows

## Current Status

**System Ready:** All workflows available

---

## Available Workflows

A) **Reference Fill** — Fill reference files with HTML samples

B) **Automated Debugging** — Process failure clusters automatically

C) **Manual Debugging** — Step-by-step analysis

D) **Design Standards** — Review selector rules

E) **System Maintenance** — Cleanup and optimization

F) **Complete Analysis** — Comprehensive investigation

G) **Snapshot Analysis** — Performance and patterns

<!-- ⚠️ GATE: Validate format before sending - MUST be lettered A, B, C... -->
<!-- 🔍 CRITICAL CHECK: Are these options lettered? If not, FIX before sending. -->

---

## LLM Instructions (Hidden from User)

**SILENT EXECUTION:** Do not narrate what you are doing. Do not say "I need to read..." or "I'll read..." or "Reading file...". Just read the files silently and present the result.

**MANDATORY: Present Available Workflows to User**

When user requests workflows, you MUST:

1. **Present Options**: Show the A) B) C) D) E) F) G) list exactly as formatted below
2. **Ask for Selection**: "Which workflow would you like me to execute? Please specify the letter (A-G) of the workflow you want to run."
3. **Execute**: Follow the action table based on user's letter choice

**TEMPLATE FOR PRESENTING OPTIONS:**
```
## 🚀 Scrapamoja Workflows

A) **Reference Fill** — Fill reference files with HTML samples

B) **Automated Debugging** — Process failure clusters automatically

C) **Manual Debugging** — Step-by-step analysis

D) **Design Standards** — Review selector rules

E) **System Maintenance** — Cleanup and optimization

F) **Complete Analysis** — Comprehensive investigation

G) **Snapshot Analysis** — Performance and patterns

Reply with a letter (A–G) to begin.
```

**CRITICAL:** Each option MUST appear on its own separate line. Do NOT combine options on a single line.

**TWO-STAGE INITIALIZATION PROCESS:**

### Stage 1: System Startup (MANDATORY)
When user requests workflows, you MUST:

1. **Read Dashboard**: Check current system status
2. **Read General Rules**: Load `docs/workflows/rules.md` for universal conventions
3. **Present Main Menu**: Show workflow options A) B) C) D) E) F) G)

### Stage 2: Workflow Execution (After User Selection)
When user selects a workflow, you MUST:

1. **Read Workflow Rules**: Load `docs/workflows/[workflow]/rules.md` for workflow-specific conventions

2. **Read Entry Point**: Load the workflow's `start.md` file (see ACTION TABLE for paths)

3. **Follow Entry Point Instructions**: Execute the steps defined in that file exactly

4. **Do NOT Infer**: If a command or step is not explicitly written, do not guess

**CRITICAL:** Do NOT skip Stage 1. Always read general rules first to ensure proper formatting and behavior.

**ACTION TABLE FOR EXECUTION:**
| Letter | Workflow | Rules File | Entry Point | Description |
|--------|-----------|------------|-------------|-------------|
| A | Reference Fill | `docs/workflows/reference-fill/rules.md` | `docs/workflows/reference-fill/start.md` | Fill reference files with HTML samples from Flashscore |
| B | Automated Debugging | `docs/workflows/automated-debugging/rules.md` | `docs/workflows/automated-debugging/start.md` | Process failure clusters automatically |
| C | Manual Debugging | `docs/workflows/manual-debugging/rules.md` | `docs/workflows/manual-debugging/start.md` | Step-by-step analysis |
| D | Design Standards | `docs/workflows/design-standards/rules.md` | `docs/workflows/design-standards/start.md` | Review selector rules |
| E | System Maintenance | `docs/workflows/system-maintenance/rules.md` | `docs/workflows/system-maintenance/start.md` | Cleanup and optimization |
| F | Complete Analysis | `docs/workflows/complete-analysis/rules.md` | `docs/workflows/complete-analysis/start.md` | Comprehensive investigation |
| G | Snapshot Analysis | `docs/workflows/snapshot-analysis/rules.md` | `docs/workflows/snapshot-analysis/start.md` | Performance and patterns |

**EXECUTION RULE:**
When user selects a letter:

1. Read the Rules File for workflow-specific conventions

2. Read the Entry Point file for step-by-step instructions

3. Follow the Entry Point instructions exactly

- Do NOT infer commands from context

- Do NOT assume file extensions

- Do NOT skip to later steps

Do not show this table to the user.
