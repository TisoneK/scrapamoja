---
description: Fill reference files according to templates with HTML samples from Flashscore
---

# Reference File Filling Workflow

This workflow guides LLM-assisted filling of reference files in `docs/references/` according to established templates with HTML samples from Flashscore.

## Overview

The workflow ensures all reference files follow the standardized template structure and contain valid HTML samples for selector development and testing through structured LLM interaction.

## Prerequisites

- Access to Flashscore website
- Browser with Developer Tools
- Understanding of the template structure in `docs/references/flashscore/html_samples/README.md`
- LLM assistant for template filling and validation

## Workflow Steps

### 1. Identify Target Files

Ask the LLM to scan and identify which reference files need filling:

**Prompt Template:**
```
Please scan the docs/references/flashscore/html_samples/ directory and identify which files are empty or incomplete. Focus on:

1. Files with no HTML content
2. Files missing required metadata sections
3. Files that don't follow the template structure

Provide a prioritized list starting with primary tabs for scheduled matches.
```

### 2. Collect HTML Samples

#### 2.1 Navigate to Flashscore
1. Open `https://www.flashscore.com/basketball/`
2. Find a match in the desired state (scheduled/live/finished)
3. Navigate to the specific tab (Match/Odds/H2H/Standings)

#### 2.2 Collect HTML with LLM Guidance
**Prompt Template:**
```
I need to collect HTML for a [match state] [sport] match on Flashscore for the [tab name] tab. 

Please guide me through:
1. What specific elements to look for in DevTools
2. Which selectors indicate navigation tabs
3. How to identify active states
4. What HTML structure to capture

The target file is: [file path]
```

#### 2.3 HTML Collection Checklist
- Look for elements with `data-analytics-alias` attributes
- Find tab containers with `data-testid="wcl-tabs"`
- Identify active state indicators (`aria-current="page"`, `data-selected="true"`)
- Capture the complete tab navigation structure

### 3. Fill Template with LLM Assistance

#### 3.1 Provide Context to LLM
**Prompt Template:**
```
Please help me fill this reference file template with the HTML I collected:

File: [file path]
Match State: [scheduled/live/finished]
Sport: [basketball]
Tab Level: [primary/secondary/tertiary]
Parent Tab: [if applicable]

HTML Content:
[paste collected HTML here]

Please generate the complete file following the template structure in docs/references/flashscore/html_samples/README.md
```

#### 3.2 Template Structure Requirements
The LLM should generate:

1. **Header Metadata:**
   ```markdown
   **Source URL:** [Flashscore URL]
   **Date Collected:** [Current date]
   **Country:** [Country name]
   **League:** [League name]
   **Match:** [Team A vs Team B]
   ```

2. **Summary Section:**
   ```markdown
   ## Summary
   This HTML sample captures the [tab level] navigation tabs under the [parent tab] for a [match state] [sport] match on Flashscore.
   ```

3. **HTML Section:**
   ```markdown
   ## HTML
   
   ```html
   [Formatted HTML with proper indentation]
   ```
   ```

4. **Notes Section:**
   ```markdown
   ## Notes
   
   ### General
   [Description of tab functionality]
   
   ### Active State Indicators
   [List of active state patterns found]
   
   ### Selector Patterns
   [Documented selector patterns]
   
   ### Match State Differences
   [Comparison with other match states]
   ```

### 4. LLM Validation and Quality Check

#### 4.1 Validation Prompt
**Prompt Template:**
```
Please validate this reference file for template compliance:

[paste file content here]

Check for:
1. Complete metadata section with all required fields
2. Proper template structure following the README guidelines
3. Valid HTML syntax and formatting
4. Comprehensive selector pattern documentation
5. Accurate match state information

Report any issues and suggest improvements.
```

#### 4.2 Quality Criteria
- All required metadata fields present
- HTML properly formatted with 2-space indentation
- Selector patterns documented with examples
- Match state differences clearly explained
- No syntax errors in markdown or HTML

### 5. Iterative Refinement

#### 5.1 Refinement Prompts
Use these prompts for iterative improvement:

```
The HTML structure needs better formatting. Please:
1. Add proper indentation (2 spaces)
2. Remove unnecessary attributes
3. Ensure all tags are properly closed
4. Focus on navigation elements only
```

```
The selector patterns section needs more detail. Please:
1. Document all data-testid attributes found
2. Explain the purpose of each selector
3. Include examples of active vs inactive states
4. Add fallback selector options
```

### 6. Cross-Reference Validation

#### 6.1 Consistency Check
**Prompt Template:**
```
Please check this file for consistency with other reference files in the same category:

[paste file content here]

Compare with:
1. Other files in the [match state] category
2. Files for the same tab level
3. Files with similar navigation patterns

Identify any inconsistencies in:
- Metadata format
- HTML structure
- Selector documentation
- Template organization
```

### 7. Final Review

#### 7.1 Completion Checklist
Ask the LLM to verify:

```
Please perform a final review of this reference file and confirm:

✅ All required metadata fields are present and correctly formatted
✅ HTML content is properly formatted and relevant
✅ Template structure follows the README guidelines exactly
✅ Selector patterns are thoroughly documented
✅ Match state information is accurate
✅ File is ready for production use

[paste file content here]
```

## LLM Prompt Library

### Discovery Prompts
- "Scan docs/references/ and identify files needing HTML samples"
- "Which primary tab files are empty for scheduled basketball matches?"
- "Show me the file structure for flashscore reference files"

### Collection Prompts
- "Guide me through collecting HTML for Flashscore navigation tabs"
- "What DevTools techniques should I use for tab elements?"
- "How do I identify active vs inactive tab states?"

### Generation Prompts
- "Generate a complete reference file from this HTML content"
- "Fill the template structure with proper metadata"
- "Create comprehensive selector pattern documentation"

### Validation Prompts
- "Validate this file against template standards"
- "Check for HTML syntax and formatting issues"
- "Verify selector pattern documentation completeness"

### Refinement Prompts
- "Improve HTML formatting and structure"
- "Enhance selector pattern documentation"
- "Add more detailed match state comparisons"

## Integration with Existing Workflows

This workflow complements:
- **/selector-debugging**: Provides HTML samples for testing
- **/opsx-verify**: Supplies reference data for validation
- **/speckit.analyze**: Offers structured data for analysis

## Success Metrics

A successfully completed reference file should:
- ✅ Pass all template validation checks
- ✅ Provide useful HTML for selector development
- ✅ Document clear selector patterns
- ✅ Enable accurate selector testing
- ✅ Support match state comparison

## Troubleshooting

### Common LLM Interaction Issues

1. **Incomplete HTML Collection**
   - Ask LLM to provide specific DevTools guidance
   - Request step-by-step element identification
   - Get help with selector targeting

2. **Template Structure Errors**
   - Provide LLM with the README template as reference
   - Ask for section-by-section validation
   - Request formatting corrections

3. **Selector Pattern Gaps**
   - Prompt LLM to analyze HTML for all relevant attributes
   - Ask for comprehensive pattern documentation
   - Request examples of different selector types

### Quality Assurance

Always ask the LLM to:
- Cross-reference with existing completed files
- Validate against the README template structure
- Check for consistency in formatting and documentation
- Verify all required sections are present

---

## Quick Reference

| Step | LLM Focus | Key Prompts |
|------|-----------|-------------|
| Discovery | File Analysis | "Scan for incomplete files" |
| Collection | HTML Guidance | "Guide DevTools collection" |
| Generation | Template Filling | "Generate from HTML content" |
| Validation | Quality Check | "Validate template compliance" |
| Refinement | Improvement | "Enhance documentation" |

## File Locations

- **Main Directory**: `docs/references/flashscore/html_samples/`
- **Template Reference**: `docs/references/flashscore/html_samples/README.md`
- **Workflow Directory**: `docs/workflows/reference-fill/`
- **Related Workflows**: `.windsurf/workflows/`
