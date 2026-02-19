# General Workflow Rules

## Purpose

This document defines universal rules that apply to ALL workflows in the Scrapamoja project. These are inherited by all workflow-specific rule files.

## Universal Formatting Rules

**🚨 ABSOLUTE RULE:** Never narrate tool use or file reads.
- Do NOT write "I'll read..."
- Do NOT write "I need to read..."
- Do NOT write "Reading file..."
- Execute silently, present results directly.

**🚨 CRITICAL: USE LETTERS FOR OPTIONS, NUMBERS FOR STEPS 🚨**

**USER OPTIONS (Always use letters):**
A) Option one - Description
B) Option two - Description  
C) Option three - Description

**PROCEDURES/STEPS (Always use numbers):**
1. First, do this
2. Second, do that
3. Third, do this

**NEVER USE:**
- Numbers for user options: 1. Option, 2. Option
- Letters for steps: a) First step, b) Second step
- Bullets/dashes for user options: - Option, * Option

**WHY THIS MATTERS:**
- Users can respond with just "A", "B", "C" (faster than typing)
- Numbers clearly indicate procedural steps/sequences
- Letters clearly indicate user choices/selections
- Reduces confusion between actions and choices

## Gate Requirements

**MANDATORY GATE MARKERS:**
All workflow templates must include ⚠️ GATE markers before any user options:
```
⚠️ GATE: Validate format before sending - MUST be lettered A, B, C...
🔍 **CRITICAL CHECK:** Are these options lettered? If not, FIX before sending.
```

This ensures LLM self-validates before presenting options to users.

## Issue Logging

**UNIVERSAL ISSUE TRACKING:**
All workflows must log issues using the same format and process:

**When to Log Issues:**
- User corrects your behavior
- User redirects your approach
- You made a wrong assumption
- You failed to complete a task
- You needed 2+ clarifications
- You used wrong format for options

**EXAMPLE:**
```markdown
docs/workflows/
├── rules.md          ← Tier 1: General (letter/number formatting, gates)
├── workflows.start.md  ← Tier 1 selection: A) B) C) + gate
└── reference-fill/
    ├── rules.md      ← Tier 2: Inherits Tier 1 + adds reference-fill specifics
    └── templates/     ← Tier 2: Specific HTML collection, validation, etc.
```

**Fallback if File Write Unavailable:**
If unable to write to `issues.json` (no file access), immediately surface the issue inline:

```
🚨 **ISSUE DETECTED** - Unable to log to file
Type: {issue_type} | Severity: {severity}
Description: {what went wrong}
User Action: {how user resolved it}
```

Then continue workflow. This ensures transparency even without logging capability.

## Variable Usage for LLM Flexibility

**WORKFLOW VARIABLES:**
When executing workflows, LLM can use these variables for consistency:

- `{workflow_name}` - Current workflow being executed
- `{total_files}` - Total files in scope
- `{files_needing_fill}` - Count of files requiring attention
- `{user_selection}` - User's last choice (A, B, C, etc.)
- `{current_step}` - Current workflow step number
- `{target_file}` - File currently being processed

**EXAMPLE USAGE:**
```
📊 **WORKFLOW STATUS:** Reference Fill
- **Files:** {total_files} total, {files_needing_fill} need attention
- **Current Step:** {current_step}/6 - Processing {target_file}
- **Last User Choice:** {user_selection}

What would you like to do next?
A) Continue with current file
B) Select different file
C) Return to main menu
```

This allows LLM to maintain context-aware responses without hardcoding values.

## Assumption Guidelines

**BALANCED APPROACH TO ASSUMPTIONS:**

**When to AVOID Assumptions:**
- ❌ User-specific context (team names, URLs, match details)
- ❌ Unusual HTML structures or edge cases
- ❌ When user has provided specific contradictory information
- ❌ Complex selector patterns that vary significantly

**When SAFE Assumptions are ACCEPTABLE:**
- ✅ Standard patterns (common navigation structures)
- ✅ Established naming conventions from existing files
- ✅ Documentation style matching completed files
- ✅ Common selector attributes (`data-testid`, `class` patterns)

**Decision Process:**
1. **First**: Ask for clarification if uncertain
2. **If no response**: Make safe assumption based on patterns
3. **Document**: Note what was assumed and why
4. **Proceed**: Continue with transparent assumption

## Quick Check After Each User Response

```
□ Did user correct me?      → Log issue → Continue corrected
□ Did user redirect me?     → Log issue → Continue redirected  
□ Did I assume wrong?       → Log issue → Ask for clarification
□ Did I miss something?     → Log issue → Address the gap
□ Did I use wrong format? → Log issue → Fix immediately
```

---

*These general rules apply to ALL workflows. Workflow-specific rules inherit these and add context-specific behaviors.*
