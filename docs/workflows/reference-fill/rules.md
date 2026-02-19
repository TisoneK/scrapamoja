# LLM Behavior Rules for Reference Fill Workflow

## Purpose

This document defines how LLM should behave when assisting with filling reference files according to templates and conventions.

## Core Principles

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
- **Must avoid**: Incomplete information, placeholder content, assumptions
- **Preferred structure**:
  1. Metadata section (complete)
  2. HTML sample (well-formatted)
  3. Summary/description
  4. Usage examples
  5. Notes and considerations

### Response Format Rules

**CRITICAL:** Always use numbered lists for user options, never bullet points.

**Correct:**
1. Option one
2. Option two
3. Option three

**Incorrect:**
- Option one
- Option two
- Option three

**Rationale:** Numbered options allow users to respond with just the number, speeding up interaction.

## Decision Making

### When to Ask for Clarification
- **Missing context**: When reference type or purpose is unclear
- **Conflicting templates**: When multiple templates could apply
- **Ambiguous requirements**: When specific formatting is unclear
- **Edge cases**: When encountering unusual HTML structures

### When to Make Assumptions
- **Standard patterns**: Safe to assume common HTML structures
- **Naming conventions**: Safe to follow established naming patterns
- **Documentation style**: Safe to match existing reference documentation

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

### Severity Levels

| Severity | When to Use |
|----------|-------------|
| `low` | Minor inconvenience, workflow continued with small adjustment |
| `medium` | Required significant user intervention, slowed workflow |
| `high` | Blocked workflow progress, required restart or major correction |

### Issue Logging Process

1. **Detect**: Recognize when user has corrected or redirected you
2. **Pause**: Stop current action before continuing
3. **Log**: Create issue entry in `issues.json`
4. **Update**: Increment statistics in `issues.json`
5. **Continue**: Resume workflow with corrected behavior

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

### Quick Check After Each User Response

```
□ Did user correct me?      → Log issue → Continue corrected
□ Did user redirect me?     → Log issue → Continue redirected  
□ Did I assume wrong?       → Log issue → Ask for clarification
□ Did I miss something?     → Log issue → Address the gap
```

---

*These rules ensure consistent, high-quality reference documentation that serves developer needs effectively.*
