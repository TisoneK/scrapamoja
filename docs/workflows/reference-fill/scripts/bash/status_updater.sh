#!/bin/bash

# Status updater script for reference fill workflow - updates workflow status
# Usage: ./status_updater.sh <mode> [status_file] [results_file]

set -e

# Default values
MODE="$1"
STATUS_FILE="${2:-./status.json}"
RESULTS_FILE="$3"

# Validate input parameters
if [[ -z "$MODE" ]]; then
    echo "Error: Mode is required"
    echo "Usage: $0 <mode> [status_file] [results_file]"
    echo "Modes: discovery, fill, validate, status"
    exit 1
fi

echo "Updating workflow status for mode: $MODE"

# Create default status if file doesn't exist
if [[ ! -f "$STATUS_FILE" ]]; then
    cat > "$STATUS_FILE" << EOF
{
    "workflow": "reference-fill",
    "version": "1.0.0",
    "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "ready",
    "llm_guidance_system": true,
    "steps_completed": [],
    "current_mode": null,
    "current_step": null,
    "progress": {
        "total_files": 0,
        "completed": 0,
        "in_progress": 0,
        "need_attention": 0,
        "completion_percentage": 0
    },
    "by_category": {
        "scheduled": {"total": 0, "completed": 0, "in_progress": 0, "need_attention": 0},
        "live": {"total": 0, "completed": 0, "in_progress": 0, "need_attention": 0},
        "finished": {"total": 0, "completed": 0, "in_progress": 0, "need_attention": 0}
    },
    "by_tab_level": {
        "primary": {"total": 0, "completed": 0, "need_attention": 0},
        "secondary": {"total": 0, "completed": 0, "need_attention": 0},
        "tertiary": {"total": 0, "completed": 0, "need_attention": 0}
    },
    "last_run": {
        "date": null,
        "mode": null,
        "script": null,
        "scan_id": null,
        "files_processed": 0,
        "issues_found": 0,
        "output_file": null
    },
    "quality_metrics": {
        "template_compliance": 0,
        "html_quality": 0,
        "documentation_quality": 0,
        "validation_pass_rate": 0
    },
    "configuration": {
        "target_directory": "docs/references/flashscore/html_samples/",
        "template_reference": "docs/references/flashscore/html_samples/README.md",
        "validation_level": "standard",
        "output_structure": {
            "scans": "outputs/scans/",
            "validation": "outputs/validation/",
            "reports": "outputs/reports/"
        },
        "llm_settings": {
            "auto_fix_simple_issues": true,
            "guided_html_collection": true,
            "template_validation": true,
            "progress_tracking": true
        }
    },
    "workflow_modes": {
        "discovery": {"available": true, "template": "templates/reference-fill.discovery.md", "script": "scripts/pwsh/scanner.ps1"},
        "fill": {"available": true, "template": "templates/reference-fill.fill.md", "script": null},
        "validate": {"available": true, "template": "templates/reference-fill.validate.md", "script": "scripts/pwsh/validator.ps1"},
        "status": {"available": true, "template": "templates/reference-fill.status.md", "script": "scripts/pwsh/status_updater.ps1"}
    },
    "health": {
        "status": "healthy",
        "blockers": [],
        "warnings": [],
        "recommendations": []
    }
}
EOF
fi

# Update basic status using jq (or fallback to sed)
if command -v jq >/dev/null 2>&1; then
    # Use jq for JSON manipulation
    jq --arg mode "$MODE" --arg updated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
        .last_updated = $updated |
        .current_mode = $mode
    ' "$STATUS_FILE" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
    
    # Update based on mode and results file
    if [[ -n "$RESULTS_FILE" && -f "$RESULTS_FILE" ]]; then
        case "$MODE" in
            "discovery")
                jq --arg results_file "$RESULTS_FILE" '
                    .last_run = {
                        "date": (.scan_metadata.scan_date // (now | strftime("%Y-%m-%dT%H:%M:%SZ"))),
                        "mode": "discovery",
                        "script": "scanner.ps1",
                        "scan_id": (.scan_metadata.scan_id // null),
                        "files_processed": (.summary.total_files_scanned // 0),
                        "issues_found": (.summary.files_by_status.incomplete // 0),
                        "output_file": $results_file
                    } |
                    .progress.total_files = (.summary.total_files_scanned // 0) |
                    .progress.need_attention = (.summary.files_by_status.incomplete // 0) |
                    .progress.completion_percentage = (
                        if (.summary.total_files_scanned // 0) > 0 then
                            ((.summary.files_by_status.complete // 0) / .summary.total_files_scanned * 100 | floor * 100 / 100)
                        else 0 end
                    ) |
                    .by_category = .summary.files_by_category |
                    .by_tab_level = .summary.files_by_tab_level |
                    if (.steps_completed | index("discovery_run")) | not then
                        .steps_completed += ["discovery_run"]
                    else . end
                ' "$RESULTS_FILE" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
                ;;
                
            "validate")
                jq --arg results_file "$RESULTS_FILE" '
                    .last_run = {
                        "date": (.validation_metadata.validation_date // (now | strftime("%Y-%m-%dT%H:%M:%SZ"))),
                        "mode": "validate",
                        "script": "validator.ps1",
                        "validation_id": (.validation_metadata.validation_id // null),
                        "files_processed": (.summary.total_files_validated // 0),
                        "issues_found": ((.summary.files_by_status.failed // 0) + (.summary.files_by_status.warning // 0)),
                        "output_file": $results_file
                    } |
                    .quality_metrics.template_compliance = (.quality_metrics.template_compliance // 0) |
                    .quality_metrics.html_quality = (.quality_metrics.html_quality // 0) |
                    .quality_metrics.documentation_quality = (.quality_metrics.metadata_completeness // 0) |
                    .quality_metrics.validation_pass_rate = (.quality_metrics.template_compliance // 0) |
                    if (.steps_completed | index("validation_run")) | not then
                        .steps_completed += ["validation_run"]
                    else . end
                ' "$RESULTS_FILE" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
                ;;
                
            "fill")
                jq --arg results_file "$RESULTS_FILE" '
                    .last_run = {
                        "date": (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
                        "mode": "fill",
                        "script": "generator.ps1",
                        "files_processed": 1,
                        "output_file": $results_file
                    } |
                    if (.steps_completed | index("fill_session")) | not then
                        .steps_completed += ["fill_session"]
                    else . end
                ' "$STATUS_FILE" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
                ;;
        esac
    fi
    
    # Update health status
    jq '
        .health.warnings = [] |
        .health.recommendations = [] |
        .health.warnings += (
            if (.progress.need_attention == 0) then [] 
            else ["Missing validator.ps1 script", "Missing status_updater.ps1 script"] end
        ) |
        .health.status = (
            if (.progress.need_attention == 0) then "completed"
            elif (.progress.completion_percentage > 50) then "progressing"
            else "ready" end
        ) |
        .health.recommendations += (
            if (.progress.need_attention == 0) then ["All reference files completed successfully"]
            elif (.progress.completion_percentage > 50) then ["Continue with fill mode for remaining files"]
            else ["Start with discovery mode to identify files needing attention"] end
        ) |
        if (.quality_metrics.template_compliance < 80) then
            .health.recommendations += ["Improve template compliance through validation"]
        else . end |
        if (.progress.completion_percentage == 0) then
            .health.recommendations += ["Run first fill mode session to begin populating reference files"]
        else . end
    ' "$STATUS_FILE" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
    
    # Get updated values for output
    health_status=$(jq -r '.health.status' "$STATUS_FILE")
    completion_percentage=$(jq -r '.progress.completion_percentage' "$STATUS_FILE")
    
else
    # Fallback to sed if jq not available
    echo "Warning: jq not found, using sed for basic updates"
    sed -i.tmp "s/\"current_mode\": null/\"current_mode\": \"$MODE\"/" "$STATUS_FILE"
    sed -i.tmp "s/\"last_updated\": \".*\"/\"last_updated\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"/" "$STATUS_FILE"
    rm -f "$STATUS_FILE.tmp"
    
    health_status="updated"
    completion_percentage="unknown"
fi

echo "Status updated successfully!"
echo "Mode: $MODE"
echo "Health: $health_status"
echo "Completion: $completion_percentage%"
echo "Status file: $STATUS_FILE"

# Return success
echo "{\"success\": true, \"mode\": \"$MODE\", \"health_status\": \"$health_status\", \"completion_percentage\": $completion_percentage, \"status_file\": \"$STATUS_FILE\"}"
