<#
.SYNOPSIS
    Discovery script for hybrid workflows - identifies targets for processing

.DESCRIPTION
    Scans directories and files to identify items that need processing.
    Outputs structured JSON for LLM analysis and decision-making.

.PARAMETER InputPath
    Path to scan for targets

.PARAMETER OutputPath
    Path where discovery results will be saved

.PARAMETER Pattern
    File pattern to match (default: *)

.EXAMPLE
    .\discovery.ps1 -InputPath ".\src" -OutputPath ".\discovery.json" -Pattern "*.js"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\discovery.json",
    
    [Parameter(Mandatory=$false)]
    [string]$Pattern = "*"
)

try {
    Write-Host "Starting discovery in: $InputPath" -ForegroundColor Green
    
    # Get files matching pattern
    $files = Get-ChildItem -Path $InputPath -Filter $Pattern -Recurse -File
    
    # Build discovery results
    $discoveryResults = @{
        "metadata" = @{
            "scan_time" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "input_path" = $InputPath
            "pattern" = $Pattern
            "total_files" = $files.Count
        }
        "targets" = @()
    }
    
    # Process each file
    foreach ($file in $files) {
        $fileInfo = @{
            "path" = $file.FullName
            "name" = $file.Name
            "extension" = $file.Extension
            "size" = $file.Length
            "last_modified" = $file.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
            "relative_path" = $file.FullName.Replace($InputPath, "").TrimStart('\', '/')
        }
        
        # Add file-specific metadata
        if ($file.Extension -eq ".js") {
            $fileInfo["type"] = "javascript"
            $fileInfo["processable"] = $true
        }
        elseif ($file.Extension -eq ".md") {
            $fileInfo["type"] = "markdown"
            $fileInfo["processable"] = $true
        }
        else {
            $fileInfo["type"] = "other"
            $fileInfo["processable"] = $false
        }
        
        $discoveryResults.targets += $fileInfo
    }
    
    # Save results
    $discoveryResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputPath -Encoding UTF8
    
    Write-Host "Discovery complete!" -ForegroundColor Green
    Write-Host "Found $($discoveryResults.metadata.total_files) files" -ForegroundColor Cyan
    Write-Host "Results saved to: $OutputPath" -ForegroundColor Yellow
    
    # Return summary
    return @{
        "success" = $true
        "files_found" = $discoveryResults.metadata.total_files
        "output_file" = $OutputPath
    }
}
catch {
    Write-Error "Discovery failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
