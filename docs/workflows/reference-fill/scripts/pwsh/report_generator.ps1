<#
.SYNOPSIS
    Report generator script for reference fill workflow - generates status reports

.DESCRIPTION
    Generates comprehensive status reports in various formats (markdown, json, html).

.PARAMETER Format
    Output format (markdown, json, html)

.PARAMETER OutputPath
    Path where the report will be saved

.PARAMETER StatusFile
    Path to the status.json file

.EXAMPLE
    .\report_generator.ps1 -Format "markdown" -OutputPath ".\outputs\reports\status_report.md"
#>

# Main script execution
[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("markdown", "json", "html")]
    [string]$Format = "markdown",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\outputs\reports\status_report.$Format",
    
    [Parameter(Mandatory=$false)]
    [string]$StatusFile = ".\status.json"
)

# Define functions first
function GenerateMarkdownReport {
    param($Status)
    
    $report = @"
# Reference Fill Workflow Status Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Workflow Version:** $($Status.version)
**Last Updated:** $($Status.last_updated)

---

## 📊 Executive Summary

**Overall Status:** $($Status.health.status.ToUpper())
**Completion:** $($Status.progress.completion_percentage)%
**Total Files:** $($Status.progress.total_files)

### Progress Overview
| Metric | Count | Percentage |
|--------|-------|------------|
| Completed | $($Status.progress.completed) | $(if ($Status.progress.total_files -gt 0) { [math]::Round(($Status.progress.completed / $Status.progress.total_files) * 100, 2) } else { 0 })% |
| In Progress | $($Status.progress.in_progress) | $(if ($Status.progress.total_files -gt 0) { [math]::Round(($Status.progress.in_progress / $Status.progress.total_files) * 100, 2) } else { 0 })% |
| Need Attention | $($Status.progress.need_attention) | $(if ($Status.progress.total_files -gt 0) { [math]::Round(($Status.progress.need_attention / $Status.progress.total_files) * 100, 2) } else { 0 })% |

---

## 🏀 Progress by Match State

| Match State | Total | Completed | Need Attention |
|-------------|-------|-----------|----------------|
| Scheduled | $($Status.by_category.scheduled.total) | $($Status.by_category.scheduled.completed) | $($Status.by_category.scheduled.need_attention) |
| Live | $($Status.by_category.live.total) | $($Status.by_category.live.completed) | $($Status.by_category.live.need_attention) |
| Finished | $($Status.by_category.finished.total) | $($Status.by_category.finished.completed) | $($Status.by_category.finished.need_attention) |

---

## 📑 Progress by Tab Level

| Tab Level | Total | Completed | Need Attention |
|------------|-------|-----------|----------------|
| Primary | $($Status.by_tab_level.primary.total) | $($Status.by_tab_level.primary.completed) | $($Status.by_tab_level.primary.need_attention) |
| Secondary | $($Status.by_tab_level.secondary.total) | $($Status.by_tab_level.secondary.completed) | $($Status.by_tab_level.secondary.need_attention) |
| Tertiary | $($Status.by_tab_level.tertiary.total) | $($Status.by_tab_level.tertiary.completed) | $($Status.by_tab_level.tertiary.need_attention) |

---

## 📈 Quality Metrics

| Metric | Score | Status |
|--------|-------|--------|
| Template Compliance | $($Status.quality_metrics.template_compliance)% | $(if ($Status.quality_metrics.template_compliance -ge 80) { "✅ Good" } elseif ($Status.quality_metrics.template_compliance -ge 60) { "⚠️ Fair" } else { "❌ Poor" }) |
| HTML Quality | $($Status.quality_metrics.html_quality)% | $(if ($Status.quality_metrics.html_quality -ge 80) { "✅ Good" } elseif ($Status.quality_metrics.html_quality -ge 60) { "⚠️ Fair" } else { "❌ Poor" }) |
| Documentation Quality | $($Status.quality_metrics.documentation_quality)% | $(if ($Status.quality_metrics.documentation_quality -ge 80) { "✅ Good" } elseif ($Status.quality_metrics.documentation_quality -ge 60) { "⚠️ Fair" } else { "❌ Poor" }) |
| Validation Pass Rate | $($Status.quality_metrics.validation_pass_rate)% | $(if ($Status.quality_metrics.validation_pass_rate -ge 80) { "✅ Good" } elseif ($Status.quality_metrics.validation_pass_rate -ge 60) { "⚠️ Fair" } else { "❌ Poor" }) |

---

## 🔄 Recent Activity

**Last Run:** $($Status.last_run.date)
**Mode:** $($Status.last_run.mode)
**Script:** $($Status.last_run.script)
$(if ($Status.last_run.scan_id) { "**Scan ID:** $($Status.last_run.scan_id)" } else { "" })
**Files Processed:** $($Status.last_run.files_processed)
**Issues Found:** $($Status.last_run.issues_found)
**Output File:** $($Status.last_run.output_file)

---

## 🚦 Workflow Health

**Status:** $($Status.health.status.ToUpper())

**Blockers:** $(if ($Status.health.blockers.Count -eq 0) { "None ✅" } else { $Status.health.blockers -join ", " })

**Warnings:** $(if ($Status.health.warnings.Count -eq 0) { "None ✅" } else { $Status.health.warnings -join ", " })

**Recommendations:**
$($Status.health.recommendations | ForEach-Object { "- $_" })

---

## 🛠️ Available Workflow Modes

| Mode | Available | Template | Script |
|------|-----------|----------|--------|
| Discovery | $(if ($Status.workflow_modes.discovery.available) { "✅ Yes" } else { "❌ No" }) | $($Status.workflow_modes.discovery.template) | $($Status.workflow_modes.discovery.script) |
| Fill | $(if ($Status.workflow_modes.fill.available) { "✅ Yes" } else { "❌ No" }) | $($Status.workflow_modes.fill.template) | $($Status.workflow_modes.fill.script) |
| Validate | $(if ($Status.workflow_modes.validate.available) { "✅ Yes" } else { "❌ No" }) | $($Status.workflow_modes.validate.template) | $($Status.workflow_modes.validate.script) |
| Status | $(if ($Status.workflow_modes.status.available) { "✅ Yes" } else { "❌ No" }) | $($Status.workflow_modes.status.template) | $($Status.workflow_modes.status.script) |

---

## 📋 Completed Steps

$($Status.steps_completed | ForEach-Object { "- $_" })

---

## 📁 Configuration

**Target Directory:** $($Status.configuration.target_directory)
**Template Reference:** $($Status.configuration.template_reference)
**Validation Level:** $($Status.configuration.validation_level)

**Output Structure:**
- Scans: $($Status.configuration.output_structure.scans)
- Validation: $($Status.configuration.output_structure.validation)
- Reports: $($Status.configuration.output_structure.reports)

**LLM Settings:**
- Auto-fix Issues: $(if ($Status.configuration.llm_settings.auto_fix_simple_issues) { "✅ Enabled" } else { "❌ Disabled" })
- Guided HTML Collection: $(if ($Status.configuration.llm_settings.guided_html_collection) { "✅ Enabled" } else { "❌ Disabled" })
- Template Validation: $(if ($Status.configuration.llm_settings.template_validation) { "✅ Enabled" } else { "❌ Disabled" })
- Progress Tracking: $(if ($Status.configuration.llm_settings.progress_tracking) { "✅ Enabled" } else { "❌ Disabled" })

---

*Report generated by Reference Fill Workflow v$($Status.version)*
"@
    
    return $report
}

function GenerateJsonReport {
    param($Status)
    
    $report = @{
        "report_metadata" = @{
            "generated" = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
            "workflow_version" = $Status.version
            "format" = "json"
        }
        "summary" = $Status.progress
        "quality_metrics" = $Status.quality_metrics
        "health" = $Status.health
        "last_run" = $Status.last_run
        "configuration" = $Status.configuration
        "workflow_modes" = $Status.workflow_modes
        "steps_completed" = $Status.steps_completed
    }
    
    return ($report | ConvertTo-Json -Depth 10)
}

function GenerateHtmlReport {
    param($Status)
    
    $report = @"
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
        <p><strong>Generated:</strong> $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
        <p><strong>Workflow Version:</strong> $($Status.version)</p>
        <p><strong>Last Updated:</strong> $($Status.last_updated)</p>
    </div>

    <div class="section">
        <h2>📊 Executive Summary</h2>
        <p><strong>Overall Status:</strong> $($Status.health.status.ToUpper())</p>
        <p><strong>Completion:</strong> $($Status.progress.completion_percentage)%</p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: $($Status.progress.completion_percentage)%"></div>
        </div>
    </div>

    <div class="section">
        <h2>📈 Quality Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
            <tr>
                <td>Template Compliance</td>
                <td>$($Status.quality_metrics.template_compliance)%</td>
                <td class="$(if ($Status.quality_metrics.template_compliance -ge 80) { 'status-good' } elseif ($Status.quality_metrics.template_compliance -ge 60) { 'status-warning' } else { 'status-poor' })">$(if ($Status.quality_metrics.template_compliance -ge 80) { 'Good' } elseif ($Status.quality_metrics.template_compliance -ge 60) { 'Fair' } else { 'Poor' })</td>
            </tr>
            <tr>
                <td>HTML Quality</td>
                <td>$($Status.quality_metrics.html_quality)%</td>
                <td class="$(if ($Status.quality_metrics.html_quality -ge 80) { 'status-good' } elseif ($Status.quality_metrics.html_quality -ge 60) { 'status-warning' } else { 'status-poor' })">$(if ($Status.quality_metrics.html_quality -ge 80) { 'Good' } elseif ($Status.quality_metrics.html_quality -ge 60) { 'Fair' } else { 'Poor' })</td>
            </tr>
            <tr>
                <td>Documentation Quality</td>
                <td>$($Status.quality_metrics.documentation_quality)%</td>
                <td class="$(if ($Status.quality_metrics.documentation_quality -ge 80) { 'status-good' } elseif ($Status.quality_metrics.documentation_quality -ge 60) { 'status-warning' } else { 'status-poor' })">$(if ($Status.quality_metrics.documentation_quality -ge 80) { 'Good' } elseif ($Status.quality_metrics.documentation_quality -ge 60) { 'Fair' } else { 'Poor' })</td>
            </tr>
            <tr>
                <td>Validation Pass Rate</td>
                <td>$($Status.quality_metrics.validation_pass_rate)%</td>
                <td class="$(if ($Status.quality_metrics.validation_pass_rate -ge 80) { 'status-good' } elseif ($Status.quality_metrics.validation_pass_rate -ge 60) { 'status-warning' } else { 'status-poor' })">$(if ($Status.quality_metrics.validation_pass_rate -ge 80) { 'Good' } elseif ($Status.quality_metrics.validation_pass_rate -ge 60) { 'Fair' } else { 'Poor' })</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>🔄 Recent Activity</h2>
        <p><strong>Last Run:</strong> $($Status.last_run.date)</p>
        <p><strong>Mode:</strong> $($Status.last_run.mode)</p>
        <p><strong>Script:</strong> $($Status.last_run.script)</p>
        $(if ($Status.last_run.scan_id) { "<p><strong>Scan ID:</strong> $($Status.last_run.scan_id)</p>" } else { "" })
        <p><strong>Files Processed:</strong> $($Status.last_run.files_processed)</p>
        <p><strong>Issues Found:</strong> $($Status.last_run.issues_found)</p>
    </div>

    <div class="section">
        <h2>🚦 Workflow Health</h2>
        <p><strong>Status:</strong> $($Status.health.status.ToUpper())</p>
        <p><strong>Blockers:</strong> $(if ($Status.health.blockers.Count -eq 0) { "None ✅" } else { $Status.health.blockers -join ", " })</p>
        <p><strong>Warnings:</strong> $(if ($Status.health.warnings.Count -eq 0) { "None ✅" } else { $Status.health.warnings -join ", " })</p>
        <h3>Recommendations:</h3>
        <ul>
            $($Status.health.recommendations | ForEach-Object { "<li>$_</li>" })
        </ul>
    </div>

    <div class="section">
        <p><em>Report generated by Reference Fill Workflow v$($Status.version)</em></p>
    </div>
</body>
</html>
"@
    
    return $report
}

try {
    Write-Host "Generating $Format report..." -ForegroundColor Green
    
    # Read status file
    if (-not (Test-Path $StatusFile)) {
        throw "Status file not found: $StatusFile"
    }
    
    $status = Get-Content $StatusFile -Raw | ConvertFrom-Json
    
    # Create output directory if it doesn't exist
    $outputDir = Split-Path $OutputPath -Parent
    if ($outputDir -and -not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Generate report based on format
    switch ($Format.ToLower()) {
        "markdown" {
            $report = GenerateMarkdownReport -Status $status
        }
        "json" {
            $report = GenerateJsonReport -Status $status
        }
        "html" {
            $report = GenerateHtmlReport -Status $status
        }
        default {
            throw "Unsupported format: $Format"
        }
    }
    
    # Save report
    $report | Out-File -FilePath $OutputPath -Encoding UTF8
    
    Write-Host "Report generated successfully!" -ForegroundColor Green
    Write-Host "Format: $Format" -ForegroundColor Cyan
    Write-Host "Output: $OutputPath" -ForegroundColor Yellow
    
    return @{
        "success" = $true
        "format" = $Format
        "output_file" = $OutputPath
        "report_size" = (Get-Item $OutputPath).Length
    }
}
catch {
    Write-Error "Report generation failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
