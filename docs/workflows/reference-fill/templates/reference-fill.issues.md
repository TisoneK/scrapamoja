---
description: Issue logging template for tracking LLM failures and ambiguities
---

# Issue Logging Template

This template guides the LLM on how to log issues when failures, ambiguities, or corrections occur during workflow execution.

## When to Log an Issue

Log an issue when ANY of the following occur:

| Trigger | Description | Example |
|---------|-------------|---------|
| `user_correction` | User explicitly corrects LLM behavior | "No, ask for HTML one tab at a time" |
| `multiple_clarifications` | LLM asks 2+ clarifying questions on same step | Asking "Which file?" then "Which tab?" then "Which URL?" |
| `incomplete_response` | Response requires manual intervention | LLM skips a step that user must complete manually |
| `incorrect_response` | Factually incorrect response | LLM says "no tertiary tabs" when they exist |

---

## Issue Entry Format

When logging an issue, create an entry with this structure:

```json
{
  "id": "issue_YYYYMMDD_XXX",
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "type": "ambiguity|failure|correction|clarification",
  "severity": "low|medium|high",
  "trigger": "user_correction|multiple_clarifications|incomplete_response|incorrect_response",
  "context": {
    "mode": "fill|discovery|validate|status",
    "step": "step_name",
    "target_file": "path/to/file.md",
    "source_url": "https://..."
  },
  "description": "What went wrong",
  "user_action": "What the user did to resolve",
  "llm_behavior": "What the LLM did incorrectly",
  "resolution": "How the issue was resolved",
  "suggested_improvement": "Potential workflow improvement"
}
```

---

## Step-by-Step Logging Process

### Step 1: Detect Issue

⚠️ **CHECK after each user response:**

Did the user:
- Correct your behavior? → Log as `correction`
- Redirect you to a different approach? → Log as `correction`
- Provide information you should have asked for? → Log as `incomplete_response`
- Point out something you missed? → Log as `ambiguity`

### Step 2: Determine Type and Severity

**Type Selection:**

| Type | When to Use |
|------|-------------|
| `ambiguity` | You made an assumption that was wrong |
| `failure` | You couldn't complete a task |
| `correction` | User had to correct/redirect you |
| `clarification` | You needed multiple clarifications |

**Severity Selection:**

| Severity | Criteria |
|----------|----------|
| `low` | Minor inconvenience, small adjustment needed |
| `medium` | Significant intervention, workflow slowed |
| `high` | Blocked progress, restart or major correction |

### Step 3: Generate Issue ID

Format: `issue_YYYYMMDD_XXX`

- `YYYYMMDD` = Current date
- `XXX` = Sequential number (001, 002, etc.)

Check existing issues in `issues.json` to determine next number.

### Step 4: Document the Issue

Fill in all required fields:

1. **context** - Where in the workflow did this occur?
2. **description** - What went wrong?
3. **user_action** - What did the user do/say?
4. **llm_behavior** - What did you do incorrectly?
5. **resolution** - How was it resolved?
6. **suggested_improvement** - How can this be prevented?

### Step 5: Update issues.json

1. Read current `docs/workflows/reference-fill/issues.json`
2. Append new issue to `issues` array
3. Update `statistics`:
   - Increment `total_issues`
   - Increment appropriate `by_type` counter
   - Increment appropriate `by_severity` counter
4. Update `last_updated` timestamp

---

## Example Issue Entry

```json
{
  "id": "issue_20260219_001",
  "timestamp": "2026-02-19T07:00:00Z",
  "type": "correction",
  "severity": "medium",
  "trigger": "user_correction",
  "context": {
    "mode": "fill",
    "step": "html_collection",
    "target_file": "finished/basketball/odds/tertiary.md",
    "source_url": "https://www.flashscore.com/match/..."
  },
  "description": "LLM requested HTML content without specifying which specific tab to provide",
  "user_action": "Instructed LLM to request HTML content one tab at a time with clear identification",
  "llm_behavior": "Asked for HTML content for multiple tabs at once without enumeration",
  "resolution": "LLM corrected to enumerate tabs and request HTML individually",
  "suggested_improvement": "Workflow should enumerate available tertiary tabs and request HTML for each individually"
}
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    ISSUE LOGGING CHECKLIST                   │
├─────────────────────────────────────────────────────────────┤
│  □ Did user correct me?           → Log as "correction"     │
│  □ Did I assume wrong?            → Log as "ambiguity"      │
│  □ Did I fail to complete?        → Log as "failure"        │
│  □ Did I ask too many times?      → Log as "clarification"  │
├─────────────────────────────────────────────────────────────┤
│  SEVERITY:                                                   │
│  □ Low    = Small adjustment, workflow continued            │
│  □ Medium = Significant intervention, slowed down           │
│  □ High   = Blocked progress, needed restart                │
├─────────────────────────────────────────────────────────────┤
│  AFTER LOGGING:                                              │
│  □ Update issues.json                                        │
│  □ Update statistics                                         │
│  □ Continue with corrected behavior                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with Workflow

This template is referenced by:
- [`rules.md`](rules.md) - LLM behavior rules
- [`reference-fill.fill.md`](reference-fill.fill.md) - Fill mode template

The issue logging step should be added after each user interaction checkpoint in the workflow templates.
