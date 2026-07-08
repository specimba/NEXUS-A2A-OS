# Stabilize lane Chrome: align lanes; optional geometry restore (manual only).
param(
    [int]$Port = 9224,
    [switch]$ForceShow
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"

& "$Repo\scripts\ensure_lane_cdp.ps1" -Port $Port

if ($ForceShow) {
    $bounds = node "$Repo\tools\browser_ai_supervisor\chrome_cdp_browser_restore.mjs" --port $Port 2>&1 | Out-String
    if ($bounds -match '"needsFix"\s*:\s*true' -or $bounds -match '-26214') {
        & "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir
    }
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure -ForceShow
}

node "$Repo\tools\browser_ai_supervisor\prune_disposable_cdp_tabs.mjs" --port $Port | Out-Null
& "$Repo\scripts\align_browser_lanes.ps1" -Port $Port -SkipEnsure

Write-Host (ConvertTo-Json @{ status = "LANE_CHROME_STABILIZED"; port = $Port; forceShow = [bool]$ForceShow })