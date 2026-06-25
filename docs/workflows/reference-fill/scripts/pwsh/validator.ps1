<#
.SYNOPSIS
    Validator script for reference fill workflow - validates completed files

.DESCRIPTION
    Validates reference files against template standards and generates quality reports.

.PARAMETER InputPath
    Path to validate reference files

.PARAMETER OutputPath
    Path where validation results will be saved

.PARAMETER ReferenceType
    Type of reference files (flashscore, other, etc.)

.EXAMPLE
    .\validator.ps1 -InputPath ".\docs\references\flashscore" -OutputPath ".\validation.json" -ReferenceType "flashscore"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\outputs\validation\validation_results.json",
    
    [Parameter(Mandatory=$false)]
    [string]$ReferenceType = "flashscore"
)

try {
    Write-Host "Validating reference files in: $InputPath" -ForegroundColor Green
    
    # Get reference files
    $files = Get-ChildItem -Path $InputPath -Recurse -File | Where-Object { 
        $_.Extension -eq ".md" -or $_.Extension -eq ".html" 
    }
    
    # Generate validation ID
    $validationId = "validation_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    
    # Build validation results
    $validationResults = @{
        "validation_metadata" = @{
            "validation_id" = $validationId
            "validation_date" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "script_version" = "1.0.0"
            "validator_settings" = @{
                "input_path" = $InputPath
                "reference_type" = $ReferenceType
                "output_path" = $OutputPath
            }
        }
        "summary" = @{
            "total_files_validated" = $files.Count
            "files_by_status" = @{
                "passed" = 0
                "failed" = 0
                "warning" = 0
            }
            "files_by_category" = @{
                "scheduled" = @{"total" = 0; "passed" = 0; "failed" = 0}
                "live" = @{"total" = 0; "passed" = 0; "failed" = 0}
                "finished" = @{"total" = 0; "passed" = 0; "failed" = 0}
            }
        }
        "quality_metrics" = @{
            "template_compliance" = 0
            "html_quality" = 0
            "metadata_completeness" = 0
            "selector_documentation" = 0
        }
        "files" = @()
    }
    
    # Process each file
    foreach ($file in $files) {
        $fileValidation = @{
            "path" = $file.FullName
            "name" = $file.Name
            "extension" = $file.Extension
            "size" = $file.Length
            "last_modified" = $file.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
            "relative_path" = $file.FullName.Replace($InputPath, "").TrimStart('\', '/')
            "validation_status" = "unknown"
            "completeness_score" = 0
            "issues" = @()
            "warnings" = @()
        }
        
        # Validate file content
        if ($file.Extension -eq ".md") {
            $content = Get-Content $file.FullName -Raw
            
            # Check template structure
            $templateIssues = @()
            $templateWarnings = @()
            
            # Required sections
            $requiredSections = @("## Summary", "## HTML", "## Notes")
            foreach ($section in $requiredSections) {
                if ($content -notmatch $section) {
                    $templateIssues += "Missing required section: $section"
                }
            }
            
            # Check for HTML block
            if ($content -notmatch "```html") {
                $templateIssues += "Missing HTML code block"
            }
            
            # Check metadata
            if ($content -match "\*\*Source URL:\*\*") {
                $fileValidation.completeness_score += 20
            } else {
                $templateWarnings += "Missing source URL metadata"
            }
            
            if ($content -match "\*\*Date Collected:\*\*") {
                $fileValidation.completeness_score += 20
            } else {
                $templateWarnings += "Missing date collected metadata"
            }
            
            # Check selector documentation
            if ($content -match "### Selector Patterns") {
                $fileValidation.completeness_score += 20
            } else {
                $templateWarnings += "Missing selector patterns documentation"
            }
            
            # Check active state indicators
            if ($content -match "### Active State Indicators") {
                $fileValidation.completeness_score += 20
            } else {
                $templateWarnings += "Missing active state indicators"
            }
            
            # Check match state differences
            if ($content -match "### Match State Differences") {
                $fileValidation.completeness_score += 20
            } else {
                $templateWarnings += "Missing match state differences"
            }
            
            # Determine validation status
            if ($templateIssues.Count -gt 0) {
                $fileValidation.validation_status = "failed"
                $fileValidation.issues = $templateIssues
            } elseif ($templateWarnings.Count -gt 0) {
                $fileValidation.validation_status = "warning"
                $fileValidation.warnings = $templateWarnings
            } else {
                $fileValidation.validation_status = "passed"
            }
            
            # Update summary statistics
            $validationResults.summary.files_by_status[$fileValidation.validation_status] += 1
            
            # Extract category for summary
            $relativePath = $fileValidation.relative_path.ToLower()
            if ($relativePath -match "scheduled") {
                $validationResults.summary.files_by_category.scheduled.total += 1
                if ($fileValidation.validation_status -eq "passed") {
                    $validationResults.summary.files_by_category.scheduled.passed += 1
                } elseif ($fileValidation.validation_status -eq "failed") {
                    $validationResults.summary.files_by_category.scheduled.failed += 1
                }
            } elseif ($relativePath -match "live") {
                $validationResults.summary.files_by_category.live.total += 1
                if ($fileValidation.validation_status -eq "passed") {
                    $validationResults.summary.files_by_category.live.passed += 1
                } elseif ($fileValidation.validation_status -eq "failed") {
                    $validationResults.summary.files_by_category.live.failed += 1
                }
            } elseif ($relativePath -match "finished") {
                $validationResults.summary.files_by_category.finished.total += 1
                if ($fileValidation.validation_status -eq "passed") {
                    $validationResults.summary.files_by_category.finished.passed += 1
                } elseif ($fileValidation.validation_status -eq "failed") {
                    $validationResults.summary.files_by_category.finished.failed += 1
                }
            }
        }
        elseif ($file.Extension -eq ".html") {
            # Basic HTML validation
            $content = Get-Content $file.FullName -Raw
            
            if ($content -match "<html" -and $content -match "</html>") {
                $fileValidation.validation_status = "passed"
                $fileValidation.completeness_score = 100
            } else {
                $fileValidation.validation_status = "failed"
                $fileValidation.issues += "Invalid HTML structure"
            }
            
            $validationResults.summary.files_by_status[$fileValidation.validation_status] += 1
        }
        
        $validationResults.files += $fileValidation
    }
    
    # Calculate quality metrics
    $totalFiles = $validationResults.summary.total_files_validated
    if ($totalFiles -gt 0) {
        $validationResults.quality_metrics.template_compliance = [math]::Round(($validationResults.summary.files_by_status.passed / $totalFiles) * 100, 2)
        $validationResults.quality_metrics.html_quality = [math]::Round(($validationResults.files | Where-Object { $_.extension -eq ".html" -and $_.validation_status -eq "passed" }).Count / [math]::Max(($validationResults.files | Where-Object { $_.extension -eq ".html" }).Count, 1) * 100, 2)
        $validationResults.quality_metrics.metadata_completeness = [math]::Round(($validationResults.files | Where-Object { $_.extension -eq ".md" } | ForEach-Object { $_.completeness_score } | Measure-Object -Average).Average, 2)
    }
    
    # Save results
    $validationResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputPath -Encoding UTF8
    
    $passedCount = $validationResults.summary.files_by_status.passed
    $failedCount = $validationResults.summary.files_by_status.failed
    $warningCount = $validationResults.summary.files_by_status.warning
    
    Write-Host "Validation complete!" -ForegroundColor Green
    Write-Host "Validation ID: $($validationResults.validation_metadata.validation_id)" -ForegroundColor Cyan
    Write-Host "Total files: $($validationResults.summary.total_files_validated)" -ForegroundColor Cyan
    Write-Host "Passed: $passedCount" -ForegroundColor Green
    Write-Host "Failed: $failedCount" -ForegroundColor Red
    Write-Host "Warnings: $warningCount" -ForegroundColor Yellow
    Write-Host "Results saved to: $OutputPath" -ForegroundColor Yellow
    
    return @{
        "success" = $true
        "validation_id" = $validationResults.validation_metadata.validation_id
        "total_files" = $validationResults.summary.total_files_validated
        "passed" = $passedCount
        "failed" = $failedCount
        "warnings" = $warningCount
        "output_file" = $OutputPath
    }
}
catch {
    Write-Error "Validation failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
