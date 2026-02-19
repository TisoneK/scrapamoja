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

⚠️ GATE: Validate format before sending - MUST be lettered A, B, C...
🔍 **CRITICAL CHECK:** Are these options lettered? If not, FIX before sending.

---

## LLM Instructions (Hidden from User)

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

1. **Read Workflow Rules**: Load `docs/workflows/[workflow]/rules.md` (inherits from general)
2. **Follow Instructions**: Execute workflow-specific steps and templates

**CRITICAL:** Do NOT skip Stage 1. Always read general rules first to ensure proper formatting and behavior.

**ACTION TABLE FOR EXECUTION:**
| Letter | Workflow | Description |
|--------|-----------|-------------|
| A | Reference Fill | Fill reference files with HTML samples from Flashscore |
| B | Automated Debugging | Process failure clusters automatically |
| C | Manual Debugging | Step-by-step analysis |
| D | Design Standards | Review selector rules |
| E | System Maintenance | Cleanup and optimization |
| F | Complete Analysis | Comprehensive investigation |
| G | Snapshot Analysis | Performance and patterns |

Do not show this table to the user.
