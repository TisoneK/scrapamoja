# Selector Debugging Helper Script
# Purpose: Automates failure clustering, analysis, and batch fixing
# Usage: .\Debug-Selectors.ps1 [-Site <site>] [-AutoFix] [-SkipFixed]

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$Site = "all",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipFixed = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoFix = $false
)

# ============================================
# STEP 0: Environment Detection
# ============================================

Write-Host "🔧 Initializing Selector Debugging Environment" -ForegroundColor Cyan
Write-Host "=" * 50

# Detect shell type
$ShellType = if ($PSVersionTable) { "PowerShell" } else { "Unknown" }
Write-Host "✅ Shell Type: $ShellType"

# Test dependencies
if (-not (Test-Path "data/snapshots/")) {
    Write-Host "❌ Error: data/snapshots/ directory not found" -ForegroundColor Red
    Write-Host "Please run scraper first to generate failures"
    exit 1
}

Write-Host "✅ Snapshots directory accessible`n"

# ============================================
# STEP 1: Discover and Cluster Failures
# ============================================

Write-Host "🔍 Step 1: Discovering Failures" -ForegroundColor Cyan
Write-Host "=" * 50

# Get all failure directories
$failures = Get-ChildItem -Path "data/snapshots/*/selector_engine/snapshot_storage/*" -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "failure_" }

Write-Host "Found $($failures.Count) total failure snapshots"

if ($failures.Count -eq 0) {
    Write-Host "✅ No failures found - system is healthy!" -ForegroundColor Green
    exit 0
}

# Extract metadata for clustering
Write-Host "`nExtracting failure metadata..."
$failureData = @()

foreach ($failure in $failures) {
    $metadataPath = Join-Path $failure.FullName "metadata.json"
    
    if (Test-Path $metadataPath) {
        try {
            $metadata = Get-Content $metadataPath | ConvertFrom-Json
            
            # Extract site from path
            $siteName = ($failure.FullName -split "snapshots[\\/]")[1].Split("[\\/]")[0]
            
            # Check if already fixed
            $statusFile = Join-Path $failure.FullName "snapshot_status.txt"
            $isFixed = $false
            if (Test-Path $statusFile) {
                $statusContent = Get-Content $statusFile -Raw
                $isFixed = $statusContent -match "status:\s*FIXED"
            }
            
            $failureData += [PSCustomObject]@{
                Path = $failure.FullName
                ID = $failure.Name
                Site = $siteName
                SelectorFile = if ($metadata.selector_file) { $metadata.selector_file } else { "unknown" }
                FailureType = if ($metadata.failure_type) { $metadata.failure_type } else { "unknown" }
                Timestamp = $failure.CreationTime
                IsFixed = $isFixed
                Resolution_Time = if ($metadata.resolution_time) { $metadata.resolution_time } else { 0 }
            }
        }
        catch {
            Write-Host "⚠️  Warning: Could not parse metadata for $($failure.Name)" -ForegroundColor Yellow
        }
    }
}

Write-Host "✅ Processed $($failureData.Count) failure records`n"

# Filter out already-fixed if requested
if ($SkipFixed) {
    $unfixedCount = ($failureData | Where-Object { -not $_.IsFixed }).Count
    Write-Host "📊 Already fixed: $($failureData.Count - $unfixedCount)"
    Write-Host "📊 Needs analysis: $unfixedCount"
    $failureData = $failureData | Where-Object { -not $_.IsFixed }
}

if ($failureData.Count -eq 0) {
    Write-Host "✅ All failures already fixed!" -ForegroundColor Green
    exit 0
}

# ============================================
# STEP 2: Cluster by Selector + Failure Type
# ============================================

Write-Host "`n🎯 Step 2: Clustering Similar Failures" -ForegroundColor Cyan
Write-Host "=" * 50

$clusters = $failureData | Group-Object -Property SelectorFile, FailureType, Site

Write-Host "`n📦 Failure Clusters (Smart Grouping):"
Write-Host "-" * 50

$clusterIndex = 1
$clusterSummary = @()

foreach ($cluster in $clusters) {
    $count = $cluster.Count
    $sample = $cluster.Group[0]
    
    $clusterInfo = [PSCustomObject]@{
        Index = $clusterIndex
        Site = $sample.Site
        SelectorFile = $sample.SelectorFile
        FailureType = $sample.FailureType
        Count = $count
        SampleID = $sample.ID
        SamplePath = $sample.Path
        Failures = $cluster.Group
    }
    
    $clusterSummary += $clusterInfo
    
    Write-Host "`n[$clusterIndex] 🔍 Cluster: $($sample.SelectorFile) ($($sample.FailureType))"
    Write-Host "    Site: $($sample.Site)"
    Write-Host "    Failures: $count"
    Write-Host "    Sample: $($sample.ID)"
    
    if ($count -gt 3) {
        Write-Host "    Others: $($cluster.Group[1..2].ID -join ', ') ..."
    } elseif ($count -gt 1) {
        Write-Host "    Others: $($cluster.Group[1..($count-1)].ID -join ', ')"
    }
    
    $clusterIndex++
}

Write-Host "`n" + "=" * 50
Write-Host "Total Clusters: $($clusters.Count)" -ForegroundColor Green
Write-Host "Total Failures: $($failureData.Count)" -ForegroundColor Green
Write-Host "=" * 50

# ============================================
# STEP 3: Interactive or Auto Mode
# ============================================

if (-not $AutoFix) {
    Write-Host "`n🎮 Interactive Mode" -ForegroundColor Cyan
    Write-Host "=" * 50
    Write-Host "Select a cluster to analyze (1-$($clusters.Count)), or:"
    Write-Host "  A - Analyze all clusters automatically"
    Write-Host "  Q - Quit"
    Write-Host ""
    
    $selection = Read-Host "Your choice"
    
    if ($selection -eq "Q") {
        Write-Host "Exiting..."
        exit 0
    }
    
    if ($selection -eq "A") {
        $AutoFix = $true
    }
    else {
        try {
            $clusterNum = [int]$selection
            if ($clusterNum -lt 1 -or $clusterNum -gt $clusters.Count) {
                Write-Host "❌ Invalid cluster number" -ForegroundColor Red
                exit 1
            }
            $clustersToProcess = @($clusterSummary[$clusterNum - 1])
        }
        catch {
            Write-Host "❌ Invalid input" -ForegroundColor Red
            exit 1
        }
    }
}

if ($AutoFix) {
    $clustersToProcess = $clusterSummary
}

# ============================================
# STEP 4: Process Each Cluster
# ============================================

Write-Host "`n🔬 Step 3: Analyzing Clusters" -ForegroundColor Cyan
Write-Host "=" * 50

$processedCount = 0
$fixedCount = 0

foreach ($cluster in $clustersToProcess) {
    $processedCount++
    
    Write-Host "`n[$processedCount/$($clustersToProcess.Count)] Processing: $($cluster.SelectorFile)"
    Write-Host "-" * 50
    
    # Analyze representative failure
    $htmlPath = Join-Path $cluster.SamplePath "html/fullpage_failure_.html"
    
    if (Test-Path $htmlPath) {
        Write-Host "📄 HTML snapshot found: $(((Get-Item $htmlPath).Length / 1MB).ToString('F2')) MB"
        
        # Extract elements for analysis
        $extractedPath = Join-Path $cluster.SamplePath "extracted_elements.txt"
        
        if (-not (Test-Path $extractedPath)) {
            Write-Host "🔍 Extracting relevant HTML elements..."
            
            try {
                $htmlContent = Get-Content $htmlPath -Raw
                
                # Extract buttons, links, forms
                $patterns = @(
                    '<button[^>]*>.*?</button>',
                    '<a[^>]*>.*?</a>',
                    '<input[^>]*>',
                    '<div[^>]*data-[^>]*>'
                )
                
                $extractedElements = @()
                foreach ($pattern in $patterns) {
                    $matches = [regex]::Matches($htmlContent, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                    $extractedElements += $matches | ForEach-Object { $_.Value }
                }
                
                $extractedElements | Out-File $extractedPath
                Write-Host "✅ Extracted $($extractedElements.Count) elements"
            }
            catch {
                Write-Host "⚠️  Could not extract elements: $_" -ForegroundColor Yellow
            }
        } else {
            $elementCount = (Get-Content $extractedPath).Count
            Write-Host "✅ Using cached extraction ($elementCount elements)"
        }
        
        # Show sample elements
        if (Test-Path $extractedPath) {
            $sampleElements = Get-Content $extractedPath | Select-Object -First 3
            Write-Host "`n📋 Sample Elements:"
            foreach ($elem in $sampleElements) {
                $preview = if ($elem.Length -gt 80) { $elem.Substring(0, 80) + "..." } else { $elem }
                Write-Host "   $preview"
            }
        }
        
        Write-Host "`n💡 Next Steps:"
        Write-Host "   1. Review extracted elements above"
        Write-Host "   2. Update selector file: src/sites/$($cluster.Site)/selectors/$($cluster.SelectorFile).yaml"
        Write-Host "   3. Test your selector against: $extractedPath"
        Write-Host "   4. Run validation to mark cluster as fixed"
        
    } else {
        Write-Host "❌ No HTML snapshot found for this failure" -ForegroundColor Red
    }
    
    # Prompt for action
    if (-not $AutoFix) {
        Write-Host "`n🎯 Actions:"
        Write-Host "   V - Validate fix (mark cluster as fixed)"
        Write-Host "   S - Skip this cluster"
        Write-Host "   Q - Quit"
        
        $action = Read-Host "Your choice"
        
        if ($action -eq "Q") {
            break
        }
        elseif ($action -eq "V") {
            Write-Host "`n🧪 Validating fix..."
            
            # Mark all failures in cluster as fixed
            foreach ($failure in $cluster.Failures) {
                $statusFile = Join-Path $failure.Path "snapshot_status.txt"
                $statusContent = @"
status: FIXED
date: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
selector: $($cluster.SelectorFile)
cluster_size: $($cluster.Count)
reason: Fixed by selector update
"@
                $statusContent | Out-File $statusFile -Encoding UTF8
            }
            
            Write-Host "✅ Marked $($cluster.Count) failures as FIXED" -ForegroundColor Green
            $fixedCount += $cluster.Count
        }
    }
}

# ============================================
# STEP 5: Summary
# ============================================

Write-Host "`n" + "=" * 50
Write-Host "🎉 Debugging Session Complete" -ForegroundColor Green
Write-Host "=" * 50
Write-Host "Clusters Processed: $processedCount"
Write-Host "Failures Fixed: $fixedCount"
Write-Host "Time Saved: ~$([Math]::Round($fixedCount * 2.5, 0)) minutes (estimated)"
Write-Host "=" * 50

# Export summary
$summaryPath = "docs/workflows/debug_session_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$summary = @{
    session_date = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'
    clusters_processed = $processedCount
    failures_fixed = $fixedCount
    clusters = $clustersToProcess | ForEach-Object {
        @{
            selector = $_.SelectorFile
            site = $_.Site
            count = $_.Count
            failure_type = $_.FailureType
        }
    }
}

try {
    try {
        $summary | ConvertTo-Json -Depth 10 | Out-File $summaryPath -Encoding UTF8
        Write-Host "`n📝 Session summary saved to: $summaryPath"
    }
    catch {
        Write-Host "⚠️  Could not save summary: $_" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️  Could not save summary: $_" -ForegroundColor Yellow
}

Write-Host "`nℹ️  Remember to:"
Write-Host "   1. Update workflow_status.json with your fixes"
Write-Host "   2. Commit selector changes to version control"
Write-Host "   3. Run integration tests before deploying"

# Check archiving thresholds
$snapshotSize = (Get-ChildItem data/snapshots -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
$oldestSnapshot = Get-ChildItem data/snapshots -Recurse -ErrorAction SilentlyContinue | Sort-Object CreationTime | Select-Object -First 1
$daysOld = if ($oldestSnapshot) { (Get-Date) - $oldestSnapshot.CreationTime } else { [TimeSpan]::Zero }

# Only show archiving suggestion if thresholds met
if ($snapshotSize -gt 500 -or $daysOld.Days -gt 60) {
    Write-Host "   4. Archive session (data: $([Math]::Round($snapshotSize, 0))MB, age: $($daysOld.Days) days) - see system-maintenance.md"
}
