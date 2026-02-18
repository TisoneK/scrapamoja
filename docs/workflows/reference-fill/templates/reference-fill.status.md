---
description: Status mode for reference file filling workflow
---

# Status Mode - Check Workflow Progress and Metrics

This mode provides comprehensive status reporting for the reference file filling workflow.

## LLM Instructions

When a user selects Status Mode, provide detailed progress information and metrics.

### 1. Load Current Status
Read the latest status information:

**Status Sources:**
- `status.json` - Workflow progress
- `scan_results.json` - File analysis
- `validation_results.json` - Quality metrics
- Recent file modifications

### 2. Present Overall Status
Display comprehensive status overview:

**Status Format:**
```
📊 Reference Fill Workflow Status

**Last Updated:** {timestamp}
**Workflow State:** {ready/running/paused/completed}

## Progress Summary
- **Total Files:** {number}
- **Completed:** {number} ({percentage}%)
- **In Progress:** {number}
- **Need Attention:** {number}

## Quality Metrics
- **Average Completeness:** {percentage}%
- **Template Compliance:** {percentage}%
- **Validation Pass Rate:** {percentage}%

## Recent Activity
{list recent changes and actions}
```

### 3. Detailed File Status
Provide file-by-file breakdown:

**File Status Table:**
```
📋 File Status Details

| File Path | Status | Completeness | Last Modified | Issues |
|-----------|--------|--------------|---------------|---------|
| {path} | {status} | {percentage}% | {date} | {count} |
```

### 4. Progress by Category
Show progress organized by categories:

**By Match State:**
```
🏀 Match State Progress

**Scheduled Matches:**
- Completed: {number}/{total}
- In Progress: {number}
- Need Attention: {number}

**Live Matches:**
- Completed: {number}/{total}
- In Progress: {number}
- Need Attention: {number}

**Finished Matches:**
- Completed: {number}/{total}
- In Progress: {number}
- Need Attention: {number}
```

**By Tab Level:**
```
📑 Tab Level Progress

**Primary Tabs:** {completed}/{total} ({percentage}%)
**Secondary Tabs:** {completed}/{total} ({percentage}%)
**Tertiary Tabs:** {completed}/{total} ({percentage}%)
```

### 5. Workflow Health Check
Assess workflow health and identify blockers:

**Health Indicators:**
```
🏥 Workflow Health

**✅ Healthy Indicators:**
- Files being completed regularly
- Validation pass rate > 90%
- No critical blockers

**⚠️ Warning Indicators:**
- Files stuck in "In Progress" > 24 hours
- Validation failures increasing
- Template compliance dropping

**❌ Critical Issues:**
- Workflow stalled
- High error rates
- Template inconsistencies
```

### 6. Recommendations and Next Steps
Based on status, provide actionable recommendations:

**Recommendations Format:**
```
🎯 Recommendations

**High Priority:**
1. {specific action with impact}
2. {specific action with impact}

**Medium Priority:**
1. {specific action with impact}
2. {specific action with impact}

**Suggested Next Steps:**
- Switch to {mode} for {reason}
- Focus on {file type} files
- Run {script} to {action}
```

## Status Commands and Scripts

### Update Status
```powershell
# Update workflow status
cd "c:\Users\tison\Dev\scorewise\scrapamoja"
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\status_updater.ps1"
```

### Generate Report
```powershell
# Generate detailed status report
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\report_generator.ps1" -Format "markdown" -Output "docs/workflows/reference-fill/outputs/reports/status_report.md"
```

### Quick Status Check
```powershell
# Quick status overview
powershell -ExecutionPolicy Bypass -Command "Get-Content 'docs\workflows\reference-fill\status.json' | ConvertFrom-Json"
```

## User Prompts for Status Mode

**Initial Status Request:**
```
I'll check the current status of the reference fill workflow. Let me gather the latest metrics and progress information.
```

**Status Presentation:**
```
Here's the current status of your reference fill workflow:

{present comprehensive status}

Based on this information, I recommend:
{provide actionable recommendations}

Would you like me to:
1. Dive deeper into any specific area?
2. Help you switch to a different mode?
3. Generate a detailed report?
```

**For Specific Issues:**
```
I notice some potential issues:

{highlight specific problems}

Let me suggest some solutions:
{provide specific fixes}

Shall I help you implement these fixes?
```

## Status Metrics Definitions

**File Status Types:**
- **Complete:** All required sections present, validation passed
- **In Progress:** Partially filled, actively being worked on
- **Incomplete:** Template file with placeholders
- **Invalid:** Structure errors, validation failed

**Completeness Scoring:**
- **100%:** Fully compliant with template
- **75-99%:** Minor issues or missing sections
- **50-74%:** Major sections missing
- **<50%:** Template file or significant gaps

**Quality Indicators:**
- **Template Compliance:** Adherence to standard structure
- **HTML Quality:** Validity and formatting of HTML samples
- **Documentation Quality:** Completeness of selector patterns
- **Validation Pass Rate:** Percentage of files passing validation

## Integration with Other Modes

**From Discovery Mode:**
- Update status after scanning
- Track newly identified files

**From Fill Mode:**
- Update progress after file completion
- Track quality metrics

**From Validation Mode:**
- Update validation results
- Track quality improvements

## Status Automation

The workflow automatically updates status when:
- Scanner runs (discovery mode)
- Files are saved (fill mode)
- Validation completes (validation mode)
- Scripts are executed

Manual status updates can be triggered by:
- User request
- Scheduled checks
- Error recovery
```

---

**Ready for the next step?** Choose a workflow mode or let me know if you need more detailed status information.
