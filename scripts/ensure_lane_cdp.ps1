# Ensure lane Chrome CDP is up (start visible + reset prefs if down).
param([int]$Port = 9224)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"

function Test-CdpUp {
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch { return $false }
}

if (Test-CdpUp) {
    Write-Host (ConvertTo-Json @{ status = "CDP_ALREADY_UP"; port = $Port })
    exit 0
}

& "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir
& "$Repo\scripts\start_grok_cdp_9224.ps1" -ProfileDir $ProfileDir -Port $Port
Start-Sleep -Seconds 4

if (-not (Test-CdpUp)) {
    throw "CDP port $Port still down after start"
}

& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure
Write-Host (ConvertTo-Json @{ status = "CDP_STARTED"; port = $Port })