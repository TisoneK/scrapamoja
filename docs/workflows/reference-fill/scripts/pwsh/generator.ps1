<#
.SYNOPSIS
    Generator script for reference fill workflow - creates content for reference files

.DESCRIPTION
    Takes LLM-generated content and creates or updates reference files.
    Handles template application and file management.

.PARAMETER InputFile
    Path to JSON file containing generated content

.PARAMETER TemplatePath
    Path to reference file templates

.PARAMETER OutputPath
    Path where generated files will be saved

.PARAMETER DryRun
    If specified, shows what would be created without applying

.EXAMPLE
    .\generator.ps1 -InputFile ".\generated.json" -TemplatePath ".\templates" -OutputPath ".\output"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    
    [Parameter(Mandatory=$false)]
    [string]$TemplatePath = ".\templates",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\output",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

try {
    Write-Host "Starting content generator..." -ForegroundColor Green
    
    # Load generated content
    if (-not (Test-Path $InputFile)) {
        throw "Input file not found: $InputFile"
    }
    
    $content = Get-Content $InputFile | ConvertFrom-Json
    Write-Host "Loaded $($content.files.Count) files to generate" -ForegroundColor Cyan
    
    # Create output directory
    if (-not $DryRun) {
        if (-not (Test-Path $OutputPath)) {
            New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
        }
    }
    
    $results = @{
        "metadata" = @{
            "start_time" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "input_file" = $InputFile
            "template_path" = $TemplatePath
            "dry_run" = $DryRun.IsPresent
        }
        "generated" = @()
        "errors" = @()
        "skipped" = @()
    }
    
    # Process each file
    foreach ($file in $content.files) {
        $targetPath = Join-Path $OutputPath $file.filename
        
        Write-Host "Generating: $($file.filename)" -ForegroundColor Yellow
        
        try {
            # Build file content
            $fileContent = @()
            
            # Add frontmatter
            if ($file.metadata) {
                $fileContent += "---"
                foreach ($key in $file.metadata.PSObject.Properties) {
                    $fileContent += "$($key.Name): `"$($key.Value)`""
                }
                $fileContent += "---"
                $fileContent += ""
            }
            
            # Add sections
            if ($file.sections) {
                foreach ($section in $file.sections) {
                    $fileContent += "## $($section.title)"
                    $fileContent += ""
                    $fileContent += $section.content
                    $fileContent += ""
                }
            }
            
            # Add HTML sample if provided
            if ($file.html_sample) {
                $fileContent += "## HTML Sample"
                $fileContent += ""
                $fileContent += "```html"
                $fileContent += $file.html_sample
                $fileContent += "```"
                $fileContent += ""
            }
            
            # Add summary if provided
            if ($file.summary) {
                $fileContent += "## Summary"
                $fileContent += ""
                $fileContent += $file.summary
                $fileContent += ""
            }
            
            # Add usage if provided
            if ($file.usage) {
                $fileContent += "## Usage"
                $fileContent += ""
                $fileContent += $file.usage
                $fileContent += ""
            }
            
            # Add notes if provided
            if ($file.notes) {
                $fileContent += "## Notes"
                $fileContent += ""
                $fileContent += $file.notes
                $fileContent += ""
            }
            
            $finalContent = $fileContent -join "`n"
            
            if ($DryRun) {
                Write-Host "  [DRY RUN] Would create: $targetPath" -ForegroundColor Gray
                Write-Host "  Content length: $($finalContent.Length) characters" -ForegroundColor Gray
            } else {
                # Create directory if needed
                $dir = Split-Path $targetPath -Parent
                if (-not (Test-Path $dir)) {
                    New-Item -ItemType Directory -Path $dir -Force | Out-Null
                }
                
                # Write file
                $finalContent | Out-File -FilePath $targetPath -Encoding UTF8 -Force
                
                Write-Host "  ✓ Generated successfully" -ForegroundColor Green
            }
            
            # Record successful generation
            $result = @{
                "filename" = $file.filename
                "path" = $targetPath
                "status" = "success"
                "size" = $finalContent.Length
                "timestamp" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
            $results.generated += $result
        }
        catch {
            $errorResult = @{
                "filename" = $file.filename
                "error" = $_.Exception.Message
                "timestamp" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
            $results.errors += $errorResult
            
            Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    # Save generation results
    $results.metadata.end_time = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $results.metadata.total_generated = $results.generated.Count
    $results.metadata.total_errors = $results.errors.Count
    
    $outputFile = $InputFile.Replace(".json", "_results.json")
    $results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding UTF8
    
    Write-Host "Generation complete!" -ForegroundColor Green
    Write-Host "Generated: $($results.metadata.total_generated) files" -ForegroundColor Cyan
    Write-Host "Errors: $($results.metadata.total_errors)" -ForegroundColor Red
    Write-Host "Results saved to: $outputFile" -ForegroundColor Yellow
    
    return @{
        "success" = $true
        "generated" = $results.metadata.total_generated
        "errors" = $results.metadata.total_errors
        "results_file" = $outputFile
    }
}
catch {
    Write-Error "Generator failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
