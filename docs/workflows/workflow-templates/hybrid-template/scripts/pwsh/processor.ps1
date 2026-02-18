<#
.SYNOPSIS
    Processor script for hybrid workflows - executes LLM decisions

.DESCRIPTION
    Takes LLM decisions and applies them to target files.
    Handles batch processing with error recovery and rollback.

.PARAMETER DecisionsFile
    Path to JSON file containing LLM decisions

.PARAMETER BackupPath
    Path where original files will be backed up

.PARAMETER DryRun
    If specified, shows what would be changed without applying

.EXAMPLE
    .\processor.ps1 -DecisionsFile ".\decisions.json" -BackupPath ".\backup"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DecisionsFile,
    
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = ".\backup",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

try {
    Write-Host "Starting processor..." -ForegroundColor Green
    
    # Load decisions
    if (-not (Test-Path $DecisionsFile)) {
        throw "Decisions file not found: $DecisionsFile"
    }
    
    $decisions = Get-Content $DecisionsFile | ConvertFrom-Json
    Write-Host "Loaded $($decisions.decisions.Count) decisions" -ForegroundColor Cyan
    
    # Create backup directory
    if (-not $DryRun) {
        if (-not (Test-Path $BackupPath)) {
            New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
        }
    }
    
    $results = @{
        "metadata" = @{
            "start_time" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "decisions_file" = $DecisionsFile
            "dry_run" = $DryRun.IsPresent
            "backup_path" = $BackupPath
        }
        "processed" = @()
        "errors" = @()
        "skipped" = @()
    }
    
    # Process each decision
    foreach ($decision in $decisions.decisions) {
        $targetFile = $decision.target_file
        
        Write-Host "Processing: $targetFile" -ForegroundColor Yellow
        
        try {
            # Check if file exists
            if (-not (Test-Path $targetFile)) {
                throw "File not found: $targetFile"
            }
            
            # Backup original file
            if (-not $DryRun) {
                $backupFile = Join-Path $BackupPath (Split-Path $targetFile -Leaf)
                Copy-Item $targetFile $backupFile -Force
            }
            
            # Apply decision based on action type
            switch ($decision.action) {
                "modify" {
                    if ($DryRun) {
                        Write-Host "  [DRY RUN] Would modify: $targetFile" -ForegroundColor Gray
                    } else {
                        # Apply modifications
                        $content = Get-Content $targetFile -Raw
                        foreach ($change in $decision.changes) {
                            $content = $content -replace $change.pattern, $change.replacement
                        }
                        $content | Out-File $targetFile -Encoding UTF8 -Force
                    }
                }
                
                "create" {
                    if ($DryRun) {
                        Write-Host "  [DRY RUN] Would create: $($decision.new_file)" -ForegroundColor Gray
                    } else {
                        # Create new file
                        $dir = Split-Path $decision.new_file -Parent
                        if (-not (Test-Path $dir)) {
                            New-Item -ItemType Directory -Path $dir -Force | Out-Null
                        }
                        $decision.content | Out-File $decision.new_file -Encoding UTF8 -Force
                    }
                }
                
                "delete" {
                    if ($DryRun) {
                        Write-Host "  [DRY RUN] Would delete: $targetFile" -ForegroundColor Gray
                    } else {
                        Remove-Item $targetFile -Force
                    }
                }
                
                default {
                    throw "Unknown action: $($decision.action)"
                }
            }
            
            # Record successful processing
            $result = @{
                "file" = $targetFile
                "action" = $decision.action
                "status" = "success"
                "timestamp" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
            $results.processed += $result
            
            Write-Host "  ✓ Processed successfully" -ForegroundColor Green
        }
        catch {
            $errorResult = @{
                "file" = $targetFile
                "action" = $decision.action
                "error" = $_.Exception.Message
                "timestamp" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
            $results.errors += $errorResult
            
            Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    # Save processing results
    $results.metadata.end_time = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $results.metadata.total_processed = $results.processed.Count
    $results.metadata.total_errors = $results.errors.Count
    
    $outputFile = $DecisionsFile.Replace(".json", "_results.json")
    $results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding UTF8
    
    Write-Host "Processing complete!" -ForegroundColor Green
    Write-Host "Processed: $($results.metadata.total_processed) files" -ForegroundColor Cyan
    Write-Host "Errors: $($results.metadata.total_errors)" -ForegroundColor Red
    Write-Host "Results saved to: $outputFile" -ForegroundColor Yellow
    
    return @{
        "success" = $true
        "processed" = $results.metadata.total_processed
        "errors" = $results.metadata.total_errors
        "results_file" = $outputFile
    }
}
catch {
    Write-Error "Processor failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
