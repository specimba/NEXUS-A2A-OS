# Fix lane Chrome so title-bar maximize / drag works (prefs + HWND normal, not fake-maximized).
param([int]$Port = 9224)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"

& "$Repo\scripts\ensure_lane_cdp.ps1" -Port $Port | Out-Null
& "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir -Interactive
& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure -Interactive

Write-Host (ConvertTo-Json @{
    status = "LANE_CHROME_INTERACTIVE_WINDOW"
    port = $Port
    hint = "Window should be restored normal ~1280x900; use mouse maximize now"
} -Compress)