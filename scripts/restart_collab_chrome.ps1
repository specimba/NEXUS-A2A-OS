# Kill lane Chrome (CDP port + profile) and start fresh VISIBLE collab window.
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

Write-Host "Stopping lane Chrome on port $Port ..."
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
    Where-Object {
        $_.CommandLine -match "remote-debugging-port=$Port" -or
        ($ProfileDir -and $_.CommandLine -like "*$ProfileDir*")
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 2

& "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir

$start = Join-Path $Repo "scripts\start_grok_cdp_9224.ps1"
& $start -Port $Port -ProfileDir $ProfileDir

Start-Sleep -Seconds 3
& "$Repo\scripts\open_collab_tabs_if_missing.ps1" -Port $Port

& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -TitleContains "Grok|Zo|ChatGPT|specimba|OpenAI"

Write-Host "RESTART_OK port=$Port profile=$ProfileDir"