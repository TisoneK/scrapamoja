# Scrapamoja Workflows

## Current Status

**System Ready:** All workflows available

---

## Available Workflows

A) **Reference Fill** - Fill reference files with HTML samples from Flashscore
B) **Automated Debugging** - Process failure clusters automatically
C) **Manual Debugging** - Step-by-step analysis
D) **Design Standards** - Review selector rules
E) **System Maintenance** - Cleanup and optimization
F) **Complete Analysis** - Comprehensive investigation
G) **Snapshot Analysis** - Performance and patterns

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
I can help you with the following Scrapamoja workflows:

A) Reference Fill - Fill reference files with HTML samples from Flashscore
B) Automated Debugging - Process failure clusters automatically
C) Manual Debugging - Step-by-step analysis
D) Design Standards - Review selector rules
E) System Maintenance - Cleanup and optimization
F) Complete Analysis - Comprehensive investigation
G) Snapshot Analysis - Performance and patterns

Which workflow would you like me to execute? Please specify the letter (A-G) of the workflow you want to run.
```

**CRITICAL:** Do NOT ask "Which workflow would you like me to execute?" without first showing the options list above.

**ACTION TABLE FOR EXECUTION:**
| Letter | Action |
|--------|--------|
| A | Read `docs/workflows/reference-fill/start.md`, then follow |
| B | Run `powershell -File "docs/scripts/selectors/Debug-Selectors.ps1"` |
| C | Read `docs/workflows/selectors/workflows/selectors.debug.md`, then follow |
| D | Read `docs/workflows/selectors/workflows/selectors.design.standards.md` |
| E | Read `docs/workflows/system-maintenance.md` |
| F | Read `docs/workflows/selectors/workflows/selectors.debug.complete.md` |
| G | Read `docs/workflows/snapshot-analysis.md` |

Do not show this table to the user.
