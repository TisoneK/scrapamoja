---
description: Validation mode for reference file filling workflow
---

# Validation Mode - Validate Completed Reference Files

This mode checks completed reference files against template standards and validates HTML quality.

## LLM Instructions

When a user selects Validation Mode, follow this structured validation process:

### 1. Select Validation Scope
Determine what to validate:

**Prompt Template:**
```
What would you like to validate?

**Options:**
1. **Single File** - Validate a specific reference file
2. **All Completed Files** - Validate all files marked as complete
3. **Specific Directory** - Validate all files in a directory
4. **Recent Changes** - Validate files modified recently

Please choose your validation scope.
```

### 2. Run Validation Script
Execute the appropriate validation script:

**PowerShell:**
```powershell
cd "c:\Users\tison\Dev\scorewise\scrapamoja"
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\validator.ps1" -InputPath "{target_path}" -OutputPath "docs\workflows\reference-fill\outputs\validation\validation_results.json"
```

**Bash:**
```bash
cd "c:\Users\tison\Dev\scorewise\scrapamoja"
./docs/workflows/reference-fill/scripts/bash/validator.sh "{target_path}" "docs/workflows/reference-fill/outputs/validation/validation_results.json"
```

### 3. Analyze Validation Results
Review the validation output and present findings:

**Results Format:**
```
📊 Validation Results:

**Files Validated:** {number}
**Passed:** {number}
**Failed:** {number}
**Warnings:** {number}

**🔍 Issues Found:**
| File | Issue Type | Severity | Description |
|------|------------|----------|-------------|
| {file} | {type} | {high/medium/low} | {description} |
```

### 4. Detailed File Validation
For each file with issues, provide specific guidance:

**File Validation Prompt:**
```
**File:** {file_path}
**Status:** {status}

**Issues Found:**
{list of specific issues}

**Recommended Actions:**
1. {specific action 1}
2. {specific action 2}
3. {specific action 3}

Would you like me to:
1. Auto-fix the simple issues?
2. Guide you through manual fixes?
3. Skip this file for now?
```
⚠️ GATE: Validate format before sending - MUST be numbered 1, 2, 3...
🔍 **CRITICAL CHECK:** Are these options numbered? If not, FIX before sending.

## Validation Criteria

### Template Compliance
- [ ] Required metadata fields present
- [ ] Proper markdown structure
- [ ] Correct section headers
- [ ] Template format consistency

### HTML Quality
- [ ] Valid HTML syntax
- [ ] Proper indentation (2 spaces)
- [ ] All tags properly closed
- [ ] No unnecessary attributes

### Selector Documentation
- [ ] Container selectors documented
- [ ] Tab selectors identified
- [ ] Active state patterns explained
- [ ] Data attributes captured

### Match State Accuracy
- [ ] Correct match state identified
- [ ] Appropriate tabs documented
- [ ] State differences explained
- [ ] Contextual information accurate

## Auto-Fix Capabilities

The LLM can automatically fix:

**Simple Issues:**
- Missing section headers
- Incorrect indentation
- Malformed markdown
- Missing metadata fields

**Complex Issues (requires guidance):**
- HTML structure problems
- Selector pattern gaps
- Template inconsistencies
- Content accuracy issues

## User Prompts for Validation

**Initial Validation:**
```
I'll validate the reference files against our template standards. Let me run the validation script and analyze the results.
```

**After Validation:**
```
Validation complete! Here are the results:

{present validation summary}

I found {number} issues that need attention. Should I:
1. Auto-fix the simple issues now?
2. Review each file manually?
3. Focus on high-priority issues first?
```

**For Individual File Issues:**
```
Let me examine {file}:

**Issue:** {specific problem}
**Impact:** {how it affects usage}
**Fix:** {step-by-step solution}

Would you like me to implement this fix?
```

## Quality Metrics

Track these validation metrics:

**Completeness Metrics:**
- Metadata completeness: 100%
- HTML sample presence: 100%
- Selector documentation: 100%

**Quality Metrics:**
- Template compliance: {percentage}%
- HTML validity: {percentage}%
- Documentation quality: {percentage}%

**Progress Tracking:**
- Files validated: {number}/{total}
- Issues resolved: {number}/{total}
- Quality score: {percentage}%

## Integration with Workflow

- **Before Fill Mode:** Validate templates are ready
- **After Fill Mode:** Validate newly created files
- **Before Archive:** Ensure all files meet standards
- **Quality Gates:** Prevent low-quality files from progressing

## Validation Scripts

The validation scripts check:
1. **File Structure** - Template compliance
2. **HTML Quality** - Syntax and formatting
3. **Metadata** - Required fields presence
4. **Selectors** - Pattern documentation
5. **Consistency** - Cross-file standards

Results are saved to `outputs/validation/validation_results.json` for tracking and reporting.
