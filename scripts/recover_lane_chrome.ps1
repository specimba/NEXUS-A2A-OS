# One-shot lane Chrome recovery: kill profile Chrome, reset placement, visible start, force show.
param([int]$Port = 9224)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"

Write-Host "Stopping lane Chrome (profile only)..."
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | ForEach-Object {
    if ($_.CommandLine -match [regex]::Escape($ProfileDir)) {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

& "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir -Interactive
& "$Repo\scripts\start_grok_cdp_9224.ps1" -Port $Port
Start-Sleep -Seconds 4
& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure -Interactive
& "$Repo\scripts\align_browser_lanes.ps1" -Port $Port -SkipEnsure

Write-Host (ConvertTo-Json @{ status = "LANE_CHROME_RECOVERED"; port = $Port; profile = $ProfileDir })