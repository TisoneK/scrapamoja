# LLM Behavior Rules for Reference Fill Workflow

## Purpose

This document defines how LLM should behave when assisting with filling reference files according to templates and conventions.

## Inheritance

**INHERITS GENERAL RULES FROM:** `docs/workflows/rules.md`

## Core Principles (Inherited)

### 1. Template Adherence
- **Rule**: Always follow the established reference file templates exactly
- **Rationale**: Consistency is critical for reference documentation
- **Example**: Use the exact metadata structure from `docs/references/flashscore/html_samples/README.md`

### 2. Context Awareness
- **Rule**: Generate content that matches the specific reference type and purpose
- **Rationale**: Different reference types serve different documentation needs
- **Example**: Flashscore references focus on HTML structure and selectors

### 3. Quality Standards
- **Rule**: Ensure all generated content meets project quality standards
- **Rationale**: Reference files are used as authoritative documentation
- **Example**: Include proper descriptions, examples, and usage notes

## Response Guidelines

### Tone and Style
- **Tone**: Technical, precise, and informative
- **Language**: Clear, unambiguous, following project conventions
- **Formatting**: Use markdown with proper code blocks and structure

### Content Requirements
- **Must include**: Complete metadata, HTML samples, descriptions, examples
- **Must avoid**: Incomplete information, placeholder content
- **Preferred structure**:
  1. Metadata section (complete)
  2. HTML sample (well-formatted)
  3. Summary/description
  4. Usage examples
  5. Notes and considerations

### Response Format Rules

**🚨 CRITICAL: USE LETTERS FOR OPTIONS, NUMBERS FOR STEPS 🚨**

**TWO-TIER RULE STRUCTURE:**

**Tier 1: General Rules** (`docs/workflows/rules.md`)
- Apply globally: Letter/number formatting, gates, issue logging
- Cover: All workflows, universal conventions

**Tier 2: Workflow-Specific Rules** (`docs/workflows/[workflow]/rules.md`)
- Inherit general rules
- Add: Workflow-specific behaviors, templates, quality standards
- No duplication of general rules

**EXAMPLE:**
```
docs/workflows/
├── rules.md          ← Tier 1: General (letter/number formatting, gates)
├── workflows.start.md  ← Tier 1 selection: A) B) C) + gate
└── reference-fill/
    ├── rules.md      ← Tier 2: Inherits Tier 1 + adds reference-fill specifics
    └── templates/     ← Tier 2: Specific HTML collection, validation, etc.
```

This prevents duplication and ensures consistent enforcement across all workflows.

**USER OPTIONS (Always use letters):**
A) Fill files - Add HTML samples to 13 files that need filling

B) Validate - Check 2 unknown status files  

C) Status - View detailed progress information

**PROCEDURES/STEPS (Always use numbers):**
1. First, scan the directory
2. Second, analyze results
3. Third, present findings

**NEVER USE:**
- Numbers for user options: 1. Option, 2. Option
- Letters for steps: a) First step, b) Second step

**WHY THIS MATTERS:**
- Users can respond with just "A", "B", "C" (faster than typing)
- Numbers clearly indicate procedural steps/sequences
- Letters clearly indicate user choices/selections
- Reduces confusion between actions and choices

**VALIDATION CHECK:**
Before sending any response with options, ask yourself:
- Are these user options?
- Are they lettered A, B, C...?
- Are procedural steps numbered 1, 2, 3...?
- Would a user be able to respond with just a letter?

If answer to any question is "No", FIX IT before sending.

**⚡ QUICK CHECK - After Each User Response:**
```
□ Did user correct me?      → Log issue → Continue corrected
□ Did user redirect me?     → Log issue → Continue redirected  
□ Did I assume wrong?       → Log issue → Ask for clarification
□ Did I miss something?     → Log issue → Address the gap
□ Did I use wrong format? → Log issue → Fix immediately
```

**GATE REQUIREMENT:**
All workflow templates must include ⚠️ GATE markers before any user options:
```
⚠️ GATE: Validate format before sending - MUST be lettered A, B, C...
🔍 **CRITICAL CHECK:** Are these options lettered? If not, FIX before sending.
```

This ensures LLM self-validates before presenting options to users.

## Error Handling

### Types of Errors
- **Template errors**: Missing or incomplete template sections
- **Content errors**: Inaccurate or insufficient information
- **Format errors**: Improper markdown or HTML formatting

### Recovery Strategies
- **Strategy 1**: Reference existing successful examples
- **Strategy 2**: Ask for specific template requirements
- **Strategy 3**: Provide multiple options for human selection

## Quality Standards

### Validation Criteria
- **Completeness**: All required sections must be present
- **Accuracy**: Information must be correct and verifiable
- **Consistency**: Format and style must match existing references
- **Usability**: Content must be helpful for developers

### Quality Checks
- [ ] Metadata section is complete and accurate
- [ ] HTML sample is properly formatted and relevant
- [ ] Description explains the reference purpose
- [ ] Examples demonstrate actual usage
- [ ] Notes cover important considerations
- [ ] File follows naming conventions

## Constraints and Limitations

### Technical Constraints
- **File size**: Keep HTML samples reasonable for documentation
- **Complexity**: Focus on clear, understandable examples
- **Scope**: Stay within the specific reference type boundaries

### Content Constraints
- **Templates**: Must use provided templates exactly
- **Conventions**: Follow established project conventions
- **Purpose**: Focus on developer documentation needs

## Integration Rules

### Input Requirements
- **Format**: Structured data about target reference files
- **Validation**: Verify file paths and template availability
- **Context**: Include reference type and purpose information

### Output Requirements
- **Format**: Complete reference file content
- **Validation**: Ensure all template sections are filled
- **Quality**: Meet project documentation standards

## Examples

### Good Response Example
```markdown
---
title: "Live Tennis Score - In Progress"
match_state: "in_progress"
primary_tab: "live_score"
tab_level: "main"
description: "Live tennis match score display during active play"
---

## HTML Sample

```html
<div class="live-score">
  <div class="score-container">
    <div class="player-score player1">6</div>
    <div class="score-separator">-</div>
    <div class="player-score player2">4</div>
  </div>
  <div class="match-status">2nd Set - 30-15</div>
</div>
```

## Summary

This HTML structure displays live tennis scores during an active match. Shows current set scores and game progress.

## Usage

Used for displaying real-time score updates during live tennis matches. Updates dynamically as points are scored.

## Notes

- Score values update frequently during live matches
- Match status indicates current set and game progress
- Player classes (player1/player2) correspond to match participants
```

### Bad Response Example
```
Here's some HTML for a tennis score:

<div class="score">6-4</div>

This shows the score.
```

## Feedback Loop

### How to Improve
- **Success metrics**: Reference files are complete and usable
- **Failure indicators**: Missing sections, incorrect formatting
- **Improvement process**: Update rules based on validation results

## Issue Tracking

### Purpose
Track LLM failures, ambiguities, and user corrections to identify patterns and improve the workflow over time.

### Issue Tracking Integration

**🚨 SCRIPT FAILURE LOGGING:**
When scanner script returns `success: false`, LLM MUST:
1. **STOP workflow immediately** - Do not attempt manual workarounds
2. **Log script failure** to `issues.json` before any other action
3. **Write HIGH severity issue** for script failure
4. **Report exact error** from scanner output to user
5. **Do not continue** until scanner is fixed

**🚨 LLM RESPONSIBILITY:**
- Script failure = Automatic HIGH severity issue
- Manual workarounds = Additional HIGH severity issues
- Both must be logged before any workflow continuation

This ensures script failures are properly tracked and not bypassed.

### Issue Tracking File
- **Location**: `docs/workflows/reference-fill/issues.json`
- **Template**: `docs/workflows/reference-fill/templates/reference-fill.issues.md`

### When to Log an Issue

⚠️ **MANDATORY**: Log an issue when ANY of the following occur:

| Trigger | Type | Description |
|---------|------|-------------|
| User corrects your behavior | `correction` | User says "No, do it this way..." |
| User redirects your approach | `correction` | User says "Ask for HTML one tab at a time" |
| You made a wrong assumption | `ambiguity` | You assumed something that wasn't true |
| You failed to complete a task | `failure` | You couldn't finish what was asked |
| You needed 2+ clarifications | `clarification` | Multiple questions on same step |
| You used wrong format for options | `failure` | Used numbers, bullets, or wrong format instead of letters A, B, C for user options |

### Severity Levels

| Severity | When to Use | Concrete Examples |
|----------|-------------|-------------------|
| `low` | Minor inconvenience, workflow continued with small adjustment | User corrected minor formatting, LLM self-corrected quickly |
| `medium` | Required significant user intervention, slowed workflow | User had to redirect LLM approach, multiple clarifications needed |
| `high` | Blocked workflow progress, required restart or major correction | LLM generated wrong content type, user had to restart entire step |

### Issue Logging Process

1. **Detect**: Recognize when user has corrected or redirected you
2. **Pause**: Stop current action before continuing
3. **Log**: Create issue entry in `issues.json`
4. **Update**: Increment statistics in `issues.json`
5. **Continue**: Resume workflow with corrected behavior

**⚠️ FALLBACK IF FILE WRITE UNAVAILABLE:**
If unable to write to `issues.json` (no file access), immediately surface the issue inline:

```
🚨 **ISSUE DETECTED** - Unable to log to file
Type: {issue_type} | Severity: {severity}
Description: {what went wrong}
User Action: {how user resolved it}
```

Then continue workflow. This ensures transparency even without logging capability.

### Issue Entry Format

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

### Example

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
    "target_file": "finished/basketball/odds/tertiary.md"
  },
  "description": "Requested HTML content without specifying which tab",
  "user_action": "Instructed to request HTML one tab at a time",
  "llm_behavior": "Asked for HTML for multiple tabs at once",
  "resolution": "Corrected to enumerate tabs and request individually",
  "suggested_improvement": "Workflow should enumerate tabs before requesting HTML"
}
```

---

*These rules ensure consistent, high-quality reference documentation that serves developer needs effectively.*
