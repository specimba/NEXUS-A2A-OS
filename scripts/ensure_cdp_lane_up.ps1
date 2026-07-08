# Ensure NEXUS collab Chrome CDP is listening on :9224 (start if down).
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

function Test-CdpUp {
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (Test-CdpUp) {
    & "$Repo\scripts\open_collab_tabs_if_missing.ps1" -Port $Port
    Write-Host (ConvertTo-Json @{ status = "CDP_ALREADY_UP"; port = $Port } -Compress)
    exit 0
}

Write-Host "CDP port $Port is DOWN - starting visible lane Chrome..."
& "$Repo\scripts\start_grok_cdp_9224.ps1" -Port $Port -ProfileDir $ProfileDir

$deadline = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $deadline) {
    if (Test-CdpUp) {
        Write-Host (ConvertTo-Json @{ status = "CDP_STARTED"; port = $Port } -Compress)
        exit 0
    }
    Start-Sleep -Seconds 1
}

Write-Error "CDP still down after start. Try: .\scripts\grok_zo_cdp_lane.ps1 -Action RestartChrome"
exit 2