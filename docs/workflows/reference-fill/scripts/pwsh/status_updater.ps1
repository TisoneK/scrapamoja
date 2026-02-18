<#
.SYNOPSIS
    Status updater script for reference fill workflow - updates workflow status

.DESCRIPTION
    Updates the workflow status.json file with current progress and metrics.

.PARAMETER StatusFile
    Path to the status.json file

.PARAMETER Mode
    Current workflow mode (discovery, fill, validate, status)

.PARAMETER ResultsFile
    Path to results file from the current operation

.EXAMPLE
    .\status_updater.ps1 -StatusFile ".\status.json" -Mode "discovery" -ResultsFile ".\outputs\scans\scan_results.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$StatusFile = ".\status.json",
    
    [Parameter(Mandatory=$true)]
    [string]$Mode,
    
    [Parameter(Mandatory=$false)]
    [string]$ResultsFile
)

try {
    Write-Host "Updating workflow status for mode: $Mode" -ForegroundColor Green
    
    # Read current status
    if (Test-Path $StatusFile) {
        $status = Get-Content $StatusFile -Raw | ConvertFrom-Json
    } else {
        # Create default status if file doesn't exist
        $status = @{
            "workflow" = "reference-fill"
            "version" = "1.0.0"
            "created" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "status" = "ready"
            "llm_guidance_system" = $true
            "steps_completed" = @()
            "current_mode" = $null
            "current_step" = $null
            "progress" = @{
                "total_files" = 0
                "completed" = 0
                "in_progress" = 0
                "need_attention" = 0
                "completion_percentage" = 0
            }
            "by_category" = @{
                "scheduled" = @{"total" = 0; "completed" = 0; "in_progress" = 0; "need_attention" = 0}
                "live" = @{"total" = 0; "completed" = 0; "in_progress" = 0; "need_attention" = 0}
                "finished" = @{"total" = 0; "completed" = 0; "in_progress" = 0; "need_attention" = 0}
            }
            "by_tab_level" = @{
                "primary" = @{"total" = 0; "completed" = 0; "need_attention" = 0}
                "secondary" = @{"total" = 0; "completed" = 0; "need_attention" = 0}
                "tertiary" = @{"total" = 0; "completed" = 0; "need_attention" = 0}
            }
            "last_run" = @{
                "date" = $null
                "mode" = $null
                "script" = $null
                "scan_id" = $null
                "files_processed" = 0
                "issues_found" = 0
                "output_file" = $null
            }
            "quality_metrics" = @{
                "template_compliance" = 0
                "html_quality" = 0
                "documentation_quality" = 0
                "validation_pass_rate" = 0
            }
            "configuration" = @{
                "target_directory" = "docs/references/flashscore/html_samples/"
                "template_reference" = "docs/references/flashscore/html_samples/README.md"
                "validation_level" = "standard"
                "output_structure" = @{
                    "scans" = "outputs/scans/"
                    "validation" = "outputs/validation/"
                    "reports" = "outputs/reports/"
                }
                "llm_settings" = @{
                    "auto_fix_simple_issues" = $true
                    "guided_html_collection" = $true
                    "template_validation" = $true
                    "progress_tracking" = $true
                }
            }
            "workflow_modes" = @{
                "discovery" = @{"available" = $true; "template" = "templates/reference-fill.discovery.md"; "script" = "scripts/pwsh/scanner.ps1"}
                "fill" = @{"available" = $true; "template" = "templates/reference-fill.fill.md"; "script" = $null}
                "validate" = @{"available" = $true; "template" = "templates/reference-fill.validate.md"; "script" = "scripts/pwsh/validator.ps1"}
                "status" = @{"available" = $true; "template" = "templates/reference-fill.status.md"; "script" = "scripts/pwsh/status_updater.ps1"}
            }
            "health" = @{
                "status" = "healthy"
                "blockers" = @()
                "warnings" = @()
                "recommendations" = @()
            }
        }
    }
    
    # Update basic status
    $status.last_updated = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $status.current_mode = $Mode
    
    # Update based on mode and results file
    if ($ResultsFile -and (Test-Path $ResultsFile)) {
        $results = Get-Content $ResultsFile -Raw | ConvertFrom-Json
        
        switch ($Mode) {
            "discovery" {
                $status.last_run = @{
                    "date" = $results.scan_metadata.scan_date
                    "mode" = $Mode
                    "script" = "scanner.ps1"
                    "scan_id" = $results.scan_metadata.scan_id
                    "files_processed" = $results.summary.total_files_scanned
                    "issues_found" = $results.summary.files_by_status.incomplete
                    "output_file" = $ResultsFile
                }
                
                # Update progress from scan results
                $status.progress.total_files = $results.summary.total_files_scanned
                $status.progress.need_attention = $results.summary.files_by_status.incomplete
                $status.progress.completion_percentage = [math]::Round((($results.summary.files_by_status.complete / $results.summary.total_files_scanned) * 100), 2)
                
                # Update by_category
                $status.by_category.scheduled = $results.summary.files_by_category.scheduled
                $status.by_category.live = $results.summary.files_by_category.live
                $status.by_category.finished = $results.summary.files_by_category.finished
                
                # Update by_tab_level
                $status.by_tab_level.primary = $results.summary.files_by_tab_level.primary
                $status.by_tab_level.secondary = $results.summary.files_by_tab_level.secondary
                $status.by_tab_level.tertiary = $results.summary.files_by_tab_level.tertiary
                
                if (-not $status.steps_completed.Contains("discovery_run")) {
                    $status.steps_completed += "discovery_run"
                }
            }
            
            "validate" {
                $status.last_run = @{
                    "date" = $results.validation_metadata.validation_date
                    "mode" = $Mode
                    "script" = "validator.ps1"
                    "validation_id" = $results.validation_metadata.validation_id
                    "files_processed" = $results.summary.total_files_validated
                    "issues_found" = $results.summary.files_by_status.failed + $results.summary.files_by_status.warning
                    "output_file" = $ResultsFile
                }
                
                # Update quality metrics
                $status.quality_metrics.template_compliance = $results.quality_metrics.template_compliance
                $status.quality_metrics.html_quality = $results.quality_metrics.html_quality
                $status.quality_metrics.documentation_quality = $results.quality_metrics.metadata_completeness
                $status.quality_metrics.validation_pass_rate = $results.quality_metrics.template_compliance
                
                if (-not $status.steps_completed.Contains("validation_run")) {
                    $status.steps_completed += "validation_run"
                }
            }
            
            "fill" {
                # Fill mode would typically update individual file progress
                # This would be called after each file is completed
                $status.last_run = @{
                    "date" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
                    "mode" = $Mode
                    "script" = "generator.ps1"
                    "files_processed" = 1
                    "output_file" = $ResultsFile
                }
                
                if (-not $status.steps_completed.Contains("fill_session")) {
                    $status.steps_completed += "fill_session"
                }
            }
        }
    }
    
    # Update health status
    $status.health.warnings = @()
    $status.health.recommendations = @()
    
    # Check for missing scripts
    $scriptsPath = ".\scripts\pwsh"
    if (-not (Test-Path "$scriptsPath\validator.ps1")) {
        $status.health.warnings += "Missing validator.ps1 script"
    }
    if (-not (Test-Path "$scriptsPath\status_updater.ps1")) {
        $status.health.warnings += "Missing status_updater.ps1 script"
    }
    
    # Check workflow health
    if ($status.progress.need_attention -eq 0) {
        $status.health.status = "completed"
        $status.health.recommendations += "All reference files completed successfully"
    } elseif ($status.progress.completion_percentage -gt 50) {
        $status.health.status = "progressing"
        $status.health.recommendations += "Continue with fill mode for remaining files"
    } else {
        $status.health.status = "ready"
        $status.health.recommendations += "Start with discovery mode to identify files needing attention"
    }
    
    # Add general recommendations
    if ($status.quality_metrics.template_compliance -lt 80) {
        $status.health.recommendations += "Improve template compliance through validation"
    }
    if ($status.progress.completion_percentage -eq 0) {
        $status.health.recommendations += "Run first fill mode session to begin populating reference files"
    }
    
    # Save updated status
    $status | ConvertTo-Json -Depth 10 | Out-File -FilePath $StatusFile -Encoding UTF8
    
    Write-Host "Status updated successfully!" -ForegroundColor Green
    Write-Host "Mode: $Mode" -ForegroundColor Cyan
    Write-Host "Health: $($status.health.status)" -ForegroundColor Cyan
    Write-Host "Completion: $($status.progress.completion_percentage)%" -ForegroundColor Cyan
    Write-Host "Status file: $StatusFile" -ForegroundColor Yellow
    
    return @{
        "success" = $true
        "mode" = $Mode
        "health_status" = $status.health.status
        "completion_percentage" = $status.progress.completion_percentage
        "status_file" = $StatusFile
    }
}
catch {
    Write-Error "Status update failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
