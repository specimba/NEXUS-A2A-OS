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

# No --restore-last-session by default: after freezes it revives blank/ghost tabs + dual windows.
$baseArgs = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-media-suspend"
)
# Optional software GPU only if env set (SwiftShader caused shutter/phased for operator)
if ($env:NEXUS_CDP_SOFTWARE_GPU -eq "1") {
    $baseArgs += @("--disable-gpu", "--disable-gpu-compositing")
    Write-Warning "NEXUS_CDP_SOFTWARE_GPU=1"
}
if ($env:NEXUS_CDP_RESTORE_SESSION -eq "1") {
    $baseArgs += "--restore-last-session"
    Write-Warning "NEXUS_CDP_RESTORE_SESSION=1 - restoring last session (may reintroduce blanks)."
}

if ($ForceOpenGrokUrl) {
    $baseArgs += $StartUrl
}

if ($SilentBackground) {
    # HARD REFUSE - -32000 dual-window glitch freezes UI and breaks Alt-Tab
    Write-Error "SilentBackground is DISABLED. It parks at -32000 and creates frozen ghost windows."
    Write-Host "Use instead: .\scripts\start_cdp_clean_visible.ps1 -Port $Port"
    exit 2
}
Write-Host "Grok-lane Chrome CDP :$Port VISIBLE (1280x900). Policy: NEVER auto-hide / NEVER -32000."
# Kill any existing profile chrome on this port first (prevents dual windows)
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -EA SilentlyContinue | ForEach-Object {
    if ($_.CommandLine -and ($_.CommandLine -match [regex]::Escape($ProfileDir) -or $_.CommandLine -match "remote-debugging-port=$Port")) {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2
$chromeArgs = $baseArgs + @(
    "--window-position=80,50",
    "--window-size=1280,900",
    "--hide-crash-restore-bubble"
)
Start-Process -FilePath $chrome -ArgumentList $chromeArgs

Start-Sleep -Seconds 2
try {
    Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 3 | Out-Null
    Write-Host "[ok] CDP port $Port is up"
} catch {
    Write-Warning "CDP port $Port not ready yet. Run: nexusctl grok-lane doctor"
    exit 1
}

# Default: do NOT open all 17 lanes (duplicates + blanks + freeze). Opt-in via env.
if ($env:NEXUS_OPEN_ALL_LANES -eq "1") {
    Write-Warning "NEXUS_OPEN_ALL_LANES=1 - opening full lane set (heavy)."
    & "$Repo\scripts\open_all_browser_lanes.ps1" -Port $Port -SkipEnsure
} else {
    Write-Host "Skipped open_all_browser_lanes (set NEXUS_OPEN_ALL_LANES=1 to enable)."
}

# Force visible restore after start
& "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure -ForceShow -Interactive
