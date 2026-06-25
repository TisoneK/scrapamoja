---
description: Discovery mode for reference file filling workflow
---

# Discovery Mode - Find Incomplete Reference Files

This mode scans the reference directories to identify files that need filling or updates.

## LLM Instructions

When a user selects Discovery Mode, follow these steps:

### 1. Run Scanner Script
Execute the appropriate scanner script based on your system:

**PowerShell (Windows):**
```powershell
cd "c:\Users\tison\Dev\scorewise\scrapamoja"
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\scanner.ps1" -InputPath "docs\references\flashscore\html_samples" -OutputPath "docs\workflows\reference-fill\outputs\scans\scan_results.json" -ReferenceType "flashscore"
```

**Bash (Linux/Mac):**
```bash
cd "c:\Users\tison\Dev\scorewise\scrapamoja"
./docs/workflows/reference-fill/scripts/bash/scanner.sh "docs/references/flashscore/html_samples" "docs/workflows/reference-fill/outputs/scans/scan_results.json" "flashscore"
```

### 2. Analyze Scan Results
Read the scan results file and extract key information:

**File to read:** `docs/workflows/reference-fill/outputs/scans/scan_results.json`

**JSON Structure (for reference):**
```json
{
  "scan_metadata": {
    "scan_id": "scan_YYYYMMDD_HHMMSS",
    "scan_date": "YYYY-MM-DDTHH:MM:SSZ"
  },
  "summary": {
    "total_files_scanned": number,
    "files_by_status": { "complete": number, "incomplete": number },
    "files_by_category": { "scheduled": {...}, "live": {...}, "finished": {...} },
    "files_by_tab_level": { "primary": {...}, "secondary": {...}, "tertiary": {...} }
  },
  "files": [ { "path": "...", "status": "...", ... } ]
}
```

⚠️ **NOTE:** This is the expected JSON structure. Do NOT execute Python code. Use the `read_file` tool to read the JSON file directly.

### 3. Present Findings to User
Present the scan results in this format:

**📊 Discovery Results:**
- **Scan ID:** {scan_id}
- **Scan Date:** {scan_date}
- **Total files scanned:** {summary.total_files_scanned}
- **Files needing attention:** {summary.files_by_status.incomplete}
- **Already complete:** {summary.files_by_status.complete}

**🏀 By Match State:**
- **Scheduled:** {summary.files_by_category.scheduled.need_attention}/{summary.files_by_category.scheduled.total} need attention
- **Live:** {summary.files_by_category.live.need_attention}/{summary.files_by_category.live.total} need attention  
- **Finished:** {summary.files_by_category.finished.need_attention}/{summary.files_by_category.finished.total} need attention

**📑 By Tab Level:**
- **Primary tabs:** {summary.files_by_tab_level.primary.need_attention}/{summary.files_by_tab_level.primary.total} need attention
- **Secondary tabs:** {summary.files_by_tab_level.secondary.need_attention}/{summary.files_by_tab_level.secondary.total} need attention
- **Tertiary tabs:** {summary.files_by_tab_level.tertiary.need_attention}/{summary.files_by_tab_level.tertiary.total} need attention

**🎯 Priority Queue:**
1. **High Priority:** Primary tabs for scheduled matches
2. **Medium Priority:** Secondary tabs for scheduled matches
3. **Low Priority:** Live/Finished match files

**📋 Detailed File Status:**
| File | Status | Issues | Completeness |
|------|--------|--------|--------------|
| {file path} | {status} | {issues} | {percentage}% |

### 4. Recommend Next Steps
Based on the scan results, recommend:
- Which files to start with
- Which mode to use next (Fill Mode)
- Any patterns or issues noticed

## User Prompts to Use

**Initial prompt:**
```
I'll scan the reference files to identify what needs filling. Let me run the scanner and analyze the results.
```

**After scanning:**
```
I found {number} files that need attention. Here's what I recommend we work on first:

[Present prioritized list]

Would you like me to start with Fill Mode for the highest priority files?
```
⚠️ GATE: Validate format before sending - This should be a single question, not numbered options
🔍 **CRITICAL CHECK:** Is this a single question? If you added numbered options, REMOVE them.

## Integration Notes

- This mode feeds into Fill Mode
- Results are saved to `outputs/scans/scan_results.json`
- Status is tracked in `status.json`
- Use the scanner scripts for automated analysis
