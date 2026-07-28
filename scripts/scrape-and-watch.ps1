param(
    [string]$Skin = "linebet",
    [string]$Action = "prematch",
    [string]$Sport = "basketball",
    [switch]$Subgames,
    [string]$Base = "https://scrapamoja.up.railway.app",
    [string]$ApiKey = $env:BETB2B_API_KEY
)

if (-not $ApiKey) {
    Write-Error "Set BETB2B_API_KEY env var or pass -ApiKey"
    exit 1
}

# Trigger the scrape
$j = Invoke-RestMethod -Method POST -Uri "$Base/api/scraper/runs" `
    -Headers @{ 'x-api-key'=$ApiKey; 'content-type'='application/json' } `
    -Body "{`"skin`":`"$Skin`",`"action`":`"$Action`",`"sport`":`"$Sport`"}"
"job_id=$($j.job_id)  skin=$Skin  action=$Action  sport=$Sport"
""

# Poll with live phase progression
while ($true) {
    $r = Invoke-RestMethod -Uri "$Base/api/scraper/runs/$($j.job_id)" `
        -Headers @{ 'x-api-key'=$ApiKey }
    "{0}  {1,-10}  {2}" -f (Get-Date -f HH:mm:ss), $r.status, $r.phase
    if ($r.status -in 'succeeded','failed') {
        "events=$($r.event_count)  error=$($r.error)"
        break
    }
    Start-Sleep 5
}

""
# Show store counts
Write-Host "--- Counts ---"
Invoke-RestMethod -Uri "$Base/api/scraper/counts" -Headers @{ 'x-api-key'=$ApiKey }
