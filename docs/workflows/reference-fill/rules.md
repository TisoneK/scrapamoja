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

---

*These rules ensure consistent, high-quality reference documentation that serves developer needs effectively.*
