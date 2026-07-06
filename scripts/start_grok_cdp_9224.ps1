# Start dedicated Chrome for NEXUS collab lane (CDP). Default: about:blank + open tabs if missing.
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
    [string]$StartUrl = "about:blank",
    [switch]$ForceOpenGrokUrl,
    [switch]$SilentBackground = $false
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"

if ($ForceOpenGrokUrl) {
    $StartUrl = $(if ($env:NEXUS_GROK_PROJECT_CHAT_URL) { $env:NEXUS_GROK_PROJECT_CHAT_URL } elseif ($env:NEXUS_GROK_PROJECT_URL) { $env:NEXUS_GROK_PROJECT_URL } else { "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba" })
}

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $chrome) { throw "Google Chrome not found." }
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

if (-not $SilentBackground) {
    & "$Repo\scripts\reset_lane_chrome_window_placement.ps1" -ProfileDir $ProfileDir
}

$baseArgs = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts",
    "--restore-last-session",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-media-suspend"
)

if ($ForceOpenGrokUrl) {
    $baseArgs += $StartUrl
}

if ($SilentBackground) {
    Write-Host "Grok-lane Chrome CDP :$Port SILENT - corrupts window_placement; run reset before visible collab."
    $chromeArgs = $baseArgs + @("--window-position=-32000,-32000", "--window-size=1,1", "--hide-crash-restore-bubble")
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Hidden
} else {
    Write-Host "Grok-lane Chrome CDP :$Port VISIBLE (1280x900, normal - mouse maximize OK)."
    $chromeArgs = $baseArgs + @(
        "--window-position=80,50",
        "--window-size=1280,900"
    )
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs
}

Start-Sleep -Seconds 2
try {
    Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 3 | Out-Null
    Write-Host "[ok] CDP port $Port is up"
} catch {
    Write-Warning "CDP port $Port not ready yet. Run: nexusctl grok-lane doctor"
    exit 1
}

if (-not $ForceOpenGrokUrl) {
    & "$Repo\scripts\open_all_browser_lanes.ps1" -Port $Port -SkipEnsure
}

& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure