<#
.SYNOPSIS
    Scanner script for reference fill workflow - identifies incomplete reference files

.DESCRIPTION
    Scans reference directories to identify files that need completion or updates.
    Outputs structured JSON for LLM analysis and content generation.

.PARAMETER InputPath
    Path to scan for reference files

.PARAMETER OutputPath
    Path where scan results will be saved

.PARAMETER ReferenceType
    Type of reference files (flashscore, other, etc.)

.EXAMPLE
    .\scanner.ps1 -InputPath ".\docs\references\flashscore" -OutputPath ".\scan.json" -ReferenceType "flashscore"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$InputPath = "docs/references/flashscore/html_samples",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "docs/workflows/reference-fill/outputs/scans/scan_results.json",
    
    [Parameter(Mandatory=$false)]
    [string]$ReferenceType = "flashscore",
    
    [Parameter(Mandatory=$false)]
    [string]$ShowContent = $null
)

try {
    # Load ignore patterns from status file
    $ignorePatterns = $null
    $statusFile = "docs/workflows/reference-fill/status.json"
    if (Test-Path $statusFile) {
        try {
            $statusContent = Get-Content $statusFile -Raw | ConvertFrom-Json
            if ($statusContent.configuration.ignore_patterns.enabled) {
                $ignorePatterns = $statusContent.configuration.ignore_patterns
                Write-Host "Ignore patterns loaded from status.json" -ForegroundColor Green
                Write-Host "Files to ignore: $($ignorePatterns.files.Count)" -ForegroundColor Cyan
                Write-Host "Patterns to ignore: $($ignorePatterns.patterns.Count)" -ForegroundColor Cyan
            }
        } catch {
            Write-Warning "Could not load ignore patterns from status.json: $_"
        }
    }
    
    # Handle -ShowContent parameter: display specific file content for LLM verification
    if ($ShowContent) {
        $targetFile = $ShowContent
        # Try to find the file - check if it's a full path or relative
        if (-not (Test-Path $targetFile)) {
            $targetFile = Join-Path $InputPath $ShowContent
        }
        if (Test-Path $targetFile) {
            Write-Host "`n=== FILE CONTENT VERIFICATION ===" -ForegroundColor Cyan
            Write-Host "File: $targetFile" -ForegroundColor Yellow
            Write-Host "`n--- CONTENT START ---" -ForegroundColor Gray
            $content = Get-Content $targetFile -Raw
            Write-Host $content
            Write-Host "--- CONTENT END ---" -ForegroundColor Gray
            Write-Host "`n=== DETECTION ANALYSIS ===" -ForegroundColor Cyan
            
            # Run detection logic on this file
            $hasPlaceholders = ($content -match "\*\([^)]+\)\*") -or ($content -match "<!-- (Paste|NEEDS_FILL|Add|Collect|Provide|Enter|Fill|TODO|Add URL|Add HTML|placeholder).+ -->")
            $hasNEEDS_FILL = $content -match "<!-- NEEDS_FILL --->"
            $hasSmallFile = (Get-Item $targetFile).Length -lt 200
            $hasHTMLContent = ($content -match "```html") -and ($content -match "<(div|a|button|span|ul|li|section)")
            
            Write-Host "Placeholder patterns (*() or placeholder comments): $hasPlaceholders" -ForegroundColor $(if($hasPlaceholders){'Red'}else{'Green'})
            Write-Host "NEEDS_FILL marker: $hasNEEDS_FILL" -ForegroundColor $(if($hasNEEDS_FILL){'Red'}else{'Green'})
            Write-Host "Small file (<200 bytes): $hasSmallFile" -ForegroundColor $(if($hasSmallFile){'Red'}else{'Green'})
            Write-Host "Has HTML content (tags like <div, <a, <button): $hasHTMLContent" -ForegroundColor $(if($hasHTMLContent){'Green'}else{'Yellow'})
            
            if ($hasPlaceholders -or $hasNEEDS_FILL -or $hasSmallFile) {
                Write-Host "`nRESULT: NEEDS FILL" -ForegroundColor Red
            } elseif ($hasHTMLContent) {
                Write-Host "`nRESULT: COMPLETE" -ForegroundColor Green
            } else {
                Write-Host "`nRESULT: UNKNOWN - No clear indicators" -ForegroundColor Yellow
            }
            exit 0
        } else {
            Write-Host "ERROR: File not found: $targetFile" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "Scanning reference files in: $InputPath" -ForegroundColor Green
    
    # Get reference files
    $files = Get-ChildItem -Path $InputPath -Recurse -File | Where-Object { 
        $_.Extension -eq ".md" -or $_.Extension -eq ".html" 
    }
    
    # Generate scan ID
    $scanId = "scan_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    
    # Build scan results - LIST ALL FILES, let LLM verify status
    $scanResults = @{
        "scan_metadata" = @{
            "scan_id" = $scanId
            "scan_date" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
            "script_version" = "2.0.0"
            "note" = "This scanner lists all files. LLM must verify each file's status by reading it."
            "scanner_settings" = @{
                "input_path" = $InputPath
                "reference_type" = $ReferenceType
                "output_path" = $OutputPath
            }
        }
        "files" = @()
    }
    
    Write-Host "Listing all reference files..." -ForegroundColor Yellow
    
    # Process each file - detect NEEDS_FILL marker and placeholders
    foreach ($file in $files) {
        # Check if file should be ignored
        $shouldIgnore = $false
        if ($ignorePatterns) {
            # Check exact file matches
            foreach ($ignoreFile in $ignorePatterns.files) {
                if ($file.Name -eq $ignoreFile) {
                    $shouldIgnore = $true
                    Write-Host "Ignoring file (exact match): $($file.Name)" -ForegroundColor Yellow
                    break
                }
            }
            
            # Check pattern matches
            if (-not $shouldIgnore) {
                foreach ($pattern in $ignorePatterns.patterns) {
                    # Convert wildcard pattern to regex
                    $regexPattern = $pattern -replace '\*', '.*' -replace '\?', '.'
                    if ($file.Name -match $regexPattern -or $file.FullName -match $regexPattern) {
                        $shouldIgnore = $true
                        Write-Host "Ignoring file (pattern match): $($file.Name) matches $pattern" -ForegroundColor Yellow
                        break
                    }
                }
            }
        }
        
        if ($shouldIgnore) {
            continue  # Skip this file
        }
        
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        # Resolve InputPath to absolute path for comparison
        $resolvedInputPath = (Resolve-Path $InputPath -ErrorAction SilentlyContinue).Path
        if (-not $resolvedInputPath) {
            $resolvedInputPath = $InputPath
        }
        
        # Calculate relative path properly
        $relativePath = $file.FullName.Replace($resolvedInputPath, "").TrimStart('\', '/')
        
        $fileInfo = @{
            "path" = $file.FullName
            "name" = $file.Name
            "relative_path" = $relativePath
            "size_bytes" = $file.Length
            "last_modified" = $file.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
            "status" = "complete"
        }
        
        # Check for documentation files FIRST - these should be marked as complete
        if ($file.Name.ToLower() -eq "readme.md" -or 
            $relativePath -match "documentation|docs|guide|manual" -or
            $content -match "# Documentation|# Guide|# Manual") {
            $fileInfo.status = "complete"
        }
        # Check for placeholders - any file with placeholders needs filling
        # Specific patterns: *() text OR placeholder comments (Paste/NEEDS_FILL/Add/Collect/Provide/Enter/Fill)
        elseif (($content -match "\*\([^)]+\)\*") -or ($content -match "<!-- (Paste|NEEDS_FILL|Add|Collect|Provide|Enter|Fill|TODO|Add URL|Add HTML|placeholder).+ -->")) {
            $fileInfo.status = "needs_fill"
        }
        # Check for NEEDS_FILL marker
        elseif ($content -match "<!-- NEEDS_FILL -->") {
            $fileInfo.status = "needs_fill"
        }
        # Check if file is empty or very small (but not documentation files)
        elseif ($file.Length -lt 200 -and $file.Name.ToLower() -ne "readme.md") {
            $fileInfo.status = "needs_fill"
        }
        # Check for actual HTML content - must have HTML tags like <div, <a, <button, etc.
        elseif (($content -match "```html") -and ($content -match "<(div|a|button|span|ul|li|section)")) {
            $fileInfo.status = "complete"
        }
        # Documentation files with substantial content are complete
        elseif ($file.Name.ToLower() -eq "readme.md" -and $file.Length -gt 1000) {
            $fileInfo.status = "complete"
        }
        # Files that don't fit other categories and aren't documentation are unknown
        else {
            $fileInfo.status = "unknown"
        }
        
        # Extract path info for categorization
        $relativePath = $fileInfo.relative_path.ToLower()
        $fileInfo.category = "unknown"
        if ($relativePath -match "scheduled") { $fileInfo.category = "scheduled" }
        elseif ($relativePath -match "live") { $fileInfo.category = "live" }
        elseif ($relativePath -match "finished") { $fileInfo.category = "finished" }
        
        # Extract sport from path (e.g., "live\\basketball\\h2h\\secondary.md" -> "basketball")
        $fileInfo.sport = "unknown"
        if ($relativePath -match "(live|scheduled|finished)[\\](.+?)[\\]") {
            $fileInfo.sport = $matches[2]
        }
        
        $fileInfo.tab_level = "unknown"
        if ($relativePath -match "primary") { $fileInfo.tab_level = "primary" }
        elseif ($relativePath -match "secondary") { $fileInfo.tab_level = "secondary" }
        elseif ($relativePath -match "tertiary") { $fileInfo.tab_level = "tertiary" }
        
        # Ensure category is never empty
        if (-not $fileInfo.category) { $fileInfo.category = "unknown" }
        if (-not $fileInfo.sport) { $fileInfo.sport = "unknown" }
        if (-not $fileInfo.tab_level) { $fileInfo.tab_level = "unknown" }
        
        $scanResults.files += $fileInfo
    }
    
    Write-Host "Found $($scanResults.files.Count) files" -ForegroundColor Green
    Write-Host "Scanner output saved to: $OutputPath" -ForegroundColor Cyan
    
    # Save results
    $scanResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputPath -Encoding UTF8
    
    # Count statuses
    $needsFillCount = ($scanResults.files | Where-Object { $_.status -eq "needs_fill" }).Count
    $completeCount = ($scanResults.files | Where-Object { $_.status -eq "complete" }).Count
    
    Write-Host ""
    Write-Host "=== SCAN COMPLETE ===" -ForegroundColor Green
    Write-Host "Total files found: $($scanResults.files.Count)" -ForegroundColor Cyan
    Write-Host "Needs Fill: $needsFillCount" -ForegroundColor Yellow
    Write-Host "Complete: $completeCount" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files by category:" -ForegroundColor Yellow
    
    # Group files by category and display counts
    $categories = $scanResults.files | Group-Object category
    $categories | ForEach-Object {
        $categoryName = if ($_.Name) { $_.Name } else { "UNKNOWN" }
        Write-Host "  $categoryName): $($_.Count) files"
    }
    Write-Host ""
    Write-Host "Results saved to: $OutputPath" -ForegroundColor Cyan
    
    return @{
        "success" = $true
        "scan_id" = $scanResults.scan_metadata.scan_id
        "total_files" = $scanResults.files.Count
        "needs_fill" = $needsFillCount
        "complete" = $completeCount
        "output_file" = $OutputPath
    }
}
catch {
    Write-Error "Scan failed: $_"
    return @{
        "success" = $false
        "error" = $_.Exception.Message
    }
}
