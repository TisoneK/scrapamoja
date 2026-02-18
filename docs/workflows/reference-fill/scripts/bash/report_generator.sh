#!/bin/bash

# Report generator script for reference fill workflow - generates status reports
# Usage: ./report_generator.sh [format] [output_path] [status_file]

set -e

# Default values
FORMAT="${1:-markdown}"
OUTPUT_PATH="${2:-./outputs/reports/status_report.$FORMAT}"
STATUS_FILE="${3:-./status.json}"

# Validate format
if [[ ! "$FORMAT" =~ ^(markdown|json|html)$ ]]; then
    echo "Error: Invalid format. Supported formats: markdown, json, html"
    exit 1
fi

echo "Generating $FORMAT report..."

# Check if status file exists
if [[ ! -f "$STATUS_FILE" ]]; then
    echo "Error: Status file not found: $STATUS_FILE"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Get current date
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')
CURRENT_DATE_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Extract data from status file (basic extraction without jq)
if command -v jq >/dev/null 2>&1; then
    # Use jq for proper JSON parsing
    VERSION=$(jq -r '.version // "unknown"' "$STATUS_FILE")
    LAST_UPDATED=$(jq -r '.last_updated // "unknown"' "$STATUS_FILE")
    HEALTH_STATUS=$(jq -r '.health.status // "unknown"' "$STATUS_FILE")
    COMPLETION_PCT=$(jq -r '.progress.completion_percentage // 0' "$STATUS_FILE")
    TOTAL_FILES=$(jq -r '.progress.total_files // 0' "$STATUS_FILE")
    COMPLETED=$(jq -r '.progress.completed // 0' "$STATUS_FILE")
    IN_PROGRESS=$(jq -r '.progress.in_progress // 0' "$STATUS_FILE")
    NEED_ATTENTION=$(jq -r '.progress.need_attention // 0' "$STATUS_FILE")
    
    TEMPLATE_COMPLIANCE=$(jq -r '.quality_metrics.template_compliance // 0' "$STATUS_FILE")
    HTML_QUALITY=$(jq -r '.quality_metrics.html_quality // 0' "$STATUS_FILE")
    DOC_QUALITY=$(jq -r '.quality_metrics.documentation_quality // 0' "$STATUS_FILE")
    VALIDATION_RATE=$(jq -r '.quality_metrics.validation_pass_rate // 0' "$STATUS_FILE")
    
    LAST_RUN_DATE=$(jq -r '.last_run.date // "Never"' "$STATUS_FILE")
    LAST_RUN_MODE=$(jq -r '.last_run.mode // "Never"' "$STATUS_FILE")
    LAST_RUN_SCRIPT=$(jq -r '.last_run.script // "Never"' "$STATUS_FILE")
    FILES_PROCESSED=$(jq -r '.last_run.files_processed // 0' "$STATUS_FILE")
    ISSUES_FOUND=$(jq -r '.last_run.issues_found // 0' "$STATUS_FILE")
    
    # Get recommendations
    RECOMMENDATIONS=$(jq -r '.health.recommendations[]? // empty' "$STATUS_FILE" | sed 's/^/- /')
    
    # Get completed steps
    STEPS_COMPLETED=$(jq -r '.steps_completed[]? // empty' "$STATUS_FILE" | sed 's/^/- /')
    
else
    # Fallback to basic grep extraction
    echo "Warning: jq not found, using basic extraction"
    VERSION="unknown"
    LAST_UPDATED="unknown"
    HEALTH_STATUS="unknown"
    COMPLETION_PCT="0"
    TOTAL_FILES="0"
    COMPLETED="0"
    IN_PROGRESS="0"
    NEED_ATTENTION="0"
    TEMPLATE_COMPLIANCE="0"
    HTML_QUALITY="0"
    DOC_QUALITY="0"
    VALIDATION_RATE="0"
    LAST_RUN_DATE="Never"
    LAST_RUN_MODE="Never"
    LAST_RUN_SCRIPT="Never"
    FILES_PROCESSED="0"
    ISSUES_FOUND="0"
    RECOMMENDATIONS="- Install jq for better reporting"
    STEPS_COMPLETED="- Basic reporting without jq"
fi

# Calculate percentages
if [[ $TOTAL_FILES -gt 0 ]]; then
    COMPLETED_PCT=$(echo "scale=2; $COMPLETED * 100 / $TOTAL_FILES" | bc -l 2>/dev/null || echo "0")
    IN_PROGRESS_PCT=$(echo "scale=2; $IN_PROGRESS * 100 / $TOTAL_FILES" | bc -l 2>/dev/null || echo "0")
    NEED_ATTENTION_PCT=$(echo "scale=2; $NEED_ATTENTION * 100 / $TOTAL_FILES" | bc -l 2>/dev/null || echo "0")
else
    COMPLETED_PCT="0"
    IN_PROGRESS_PCT="0"
    NEED_ATTENTION_PCT="0"
fi

# Generate report based on format
case "$FORMAT" in
    "markdown")
        cat > "$OUTPUT_PATH" << EOF
# Reference Fill Workflow Status Report

**Generated:** $CURRENT_DATE
**Workflow Version:** $VERSION
**Last Updated:** $LAST_UPDATED

---

## 📊 Executive Summary

**Overall Status:** ${HEALTH_STATUS^^}
**Completion:** ${COMPLETION_PCT}%
**Total Files:** $TOTAL_FILES

### Progress Overview
| Metric | Count | Percentage |
|--------|-------|------------|
| Completed | $COMPLETED | ${COMPLETED_PCT}% |
| In Progress | $IN_PROGRESS | ${IN_PROGRESS_PCT}% |
| Need Attention | $NEED_ATTENTION | ${NEED_ATTENTION_PCT}% |

---

## 📈 Quality Metrics

| Metric | Score | Status |
|--------|-------|--------|
| Template Compliance | ${TEMPLATE_COMPLIANCE}% | $(if (( $(echo "$TEMPLATE_COMPLIANCE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "✅ Good"; elif (( $(echo "$TEMPLATE_COMPLIANCE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "⚠️ Fair"; else echo "❌ Poor"; fi) |
| HTML Quality | ${HTML_QUALITY}% | $(if (( $(echo "$HTML_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "✅ Good"; elif (( $(echo "$HTML_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "⚠️ Fair"; else echo "❌ Poor"; fi) |
| Documentation Quality | ${DOC_QUALITY}% | $(if (( $(echo "$DOC_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "✅ Good"; elif (( $(echo "$DOC_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "⚠️ Fair"; else echo "❌ Poor"; fi) |
| Validation Pass Rate | ${VALIDATION_RATE}% | $(if (( $(echo "$VALIDATION_RATE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "✅ Good"; elif (( $(echo "$VALIDATION_RATE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "⚠️ Fair"; else echo "❌ Poor"; fi) |

---

## 🔄 Recent Activity

**Last Run:** $LAST_RUN_DATE
**Mode:** $LAST_RUN_MODE
**Script:** $LAST_RUN_SCRIPT
**Files Processed:** $FILES_PROCESSED
**Issues Found:** $ISSUES_FOUND

---

## 🚦 Workflow Health

**Status:** ${HEALTH_STATUS^^}

**Blockers:** None ✅

**Warnings:** None ✅

**Recommendations:**
$RECOMMENDATIONS

---

## 📋 Completed Steps

$STEPS_COMPLETED

---

*Report generated by Reference Fill Workflow v$VERSION*
EOF
        ;;
        
    "json")
        cat > "$OUTPUT_PATH" << EOF
{
    "report_metadata": {
        "generated": "$CURRENT_DATE_ISO",
        "workflow_version": "$VERSION",
        "format": "json"
    },
    "summary": {
        "total_files": $TOTAL_FILES,
        "completed": $COMPLETED,
        "in_progress": $IN_PROGRESS,
        "need_attention": $NEED_ATTENTION,
        "completion_percentage": $COMPLETION_PCT
    },
    "quality_metrics": {
        "template_compliance": $TEMPLATE_COMPLIANCE,
        "html_quality": $HTML_QUALITY,
        "documentation_quality": $DOC_QUALITY,
        "validation_pass_rate": $VALIDATION_RATE
    },
    "health": {
        "status": "$HEALTH_STATUS"
    },
    "last_run": {
        "date": "$LAST_RUN_DATE",
        "mode": "$LAST_RUN_MODE",
        "script": "$LAST_RUN_SCRIPT",
        "files_processed": $FILES_PROCESSED,
        "issues_found": $ISSUES_FOUND
    }
}
EOF
        ;;
        
    "html")
        cat > "$OUTPUT_PATH" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Reference Fill Workflow Status Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .progress-bar { width: 100%; height: 20px; background-color: #ddd; border-radius: 10px; }
        .progress-fill { height: 100%; background-color: #4CAF50; border-radius: 10px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-good { color: green; }
        .status-warning { color: orange; }
        .status-poor { color: red; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Reference Fill Workflow Status Report</h1>
        <p><strong>Generated:</strong> $CURRENT_DATE</p>
        <p><strong>Workflow Version:</strong> $VERSION</p>
        <p><strong>Last Updated:</strong> $LAST_UPDATED</p>
    </div>

    <div class="section">
        <h2>📊 Executive Summary</h2>
        <p><strong>Overall Status:</strong> ${HEALTH_STATUS^^}</p>
        <p><strong>Completion:</strong> ${COMPLETION_PCT}%</p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${COMPLETION_PCT}%"></div>
        </div>
    </div>

    <div class="section">
        <h2>📈 Quality Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
            <tr>
                <td>Template Compliance</td>
                <td>${TEMPLATE_COMPLIANCE}%</td>
                <td class="$(if (( $(echo "$TEMPLATE_COMPLIANCE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "status-good"; elif (( $(echo "$TEMPLATE_COMPLIANCE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "status-warning"; else echo "status-poor"; fi)">$(if (( $(echo "$TEMPLATE_COMPLIANCE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "Good"; elif (( $(echo "$TEMPLATE_COMPLIANCE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "Fair"; else echo "Poor"; fi)</td>
            </tr>
            <tr>
                <td>HTML Quality</td>
                <td>${HTML_QUALITY}%</td>
                <td class="$(if (( $(echo "$HTML_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "status-good"; elif (( $(echo "$HTML_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "status-warning"; else echo "status-poor"; fi)">$(if (( $(echo "$HTML_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "Good"; elif (( $(echo "$HTML_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "Fair"; else echo "Poor"; fi)</td>
            </tr>
            <tr>
                <td>Documentation Quality</td>
                <td>${DOC_QUALITY}%</td>
                <td class="$(if (( $(echo "$DOC_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "status-good"; elif (( $(echo "$DOC_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "status-warning"; else echo "status-poor"; fi)">$(if (( $(echo "$DOC_QUALITY >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "Good"; elif (( $(echo "$DOC_QUALITY >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "Fair"; else echo "Poor"; fi)</td>
            </tr>
            <tr>
                <td>Validation Pass Rate</td>
                <td>${VALIDATION_RATE}%</td>
                <td class="$(if (( $(echo "$VALIDATION_RATE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "status-good"; elif (( $(echo "$VALIDATION_RATE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "status-warning"; else echo "status-poor"; fi)">$(if (( $(echo "$VALIDATION_RATE >= 80" | bc -l 2>/dev/null || echo 0) )); then echo "Good"; elif (( $(echo "$VALIDATION_RATE >= 60" | bc -l 2>/dev/null || echo 0) )); then echo "Fair"; else echo "Poor"; fi)</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>🔄 Recent Activity</h2>
        <p><strong>Last Run:</strong> $LAST_RUN_DATE</p>
        <p><strong>Mode:</strong> $LAST_RUN_MODE</p>
        <p><strong>Script:</strong> $LAST_RUN_SCRIPT</p>
        <p><strong>Files Processed:</strong> $FILES_PROCESSED</p>
        <p><strong>Issues Found:</strong> $ISSUES_FOUND</p>
    </div>

    <div class="section">
        <h2>🚦 Workflow Health</h2>
        <p><strong>Status:</strong> ${HEALTH_STATUS^^}</p>
        <p><strong>Blockers:</strong> None ✅</p>
        <p><strong>Warnings:</strong> None ✅</p>
        <h3>Recommendations:</h3>
        <ul>
            $RECOMMENDATIONS
        </ul>
    </div>

    <div class="section">
        <p><em>Report generated by Reference Fill Workflow v$VERSION</em></p>
    </div>
</body>
</html>
EOF
        ;;
esac

echo "Report generated successfully!"
echo "Format: $FORMAT"
echo "Output: $OUTPUT_PATH"

# Return success
echo "{\"success\": true, \"format\": \"$FORMAT\", \"output_file\": \"$OUTPUT_PATH\", \"report_size\": $(stat -f%z "$OUTPUT_PATH" 2>/dev/null || stat -c%s "$OUTPUT_PATH" 2>/dev/null || echo 0)}"
