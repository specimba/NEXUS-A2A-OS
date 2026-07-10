param(
    [string]$Url = "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
    # DEFAULT VISIBLE. Offscreen park is opt-in only and not recommended for collab.
    [switch]$ShowWindow,
    [switch]$SilentBackground
)

$ErrorActionPreference = "Stop"

# Invert old default: visible unless -SilentBackground explicitly requested.
$visible = $true
if ($SilentBackground) { $visible = $false }
if ($PSBoundParameters.ContainsKey('ShowWindow') -and -not $ShowWindow) {
    # Legacy callers that pass -ShowWindow:$false
    if (-not $SilentBackground) { $visible = $false }
}
if ($ShowWindow) { $visible = $true }

$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    $chrome = "chrome.exe"
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$chromeArgs = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts",
    "--hide-crash-restore-bubble",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-media-suspend",
    $Url
)

if (-not $visible) {
    Write-Warning "SilentBackground launches offscreen (-32000). Corrupts window_placement. Prefer default visible."
    $chromeArgs = @(
        "--remote-debugging-port=$Port",
        "--user-data-dir=$ProfileDir",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,InterestCohorts",
        "--hide-crash-restore-bubble",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-background-media-suspend",
        "--window-position=-32000,-32000",
        "--window-size=1,1",
        $Url
    )
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Hidden
    Write-Host "Chrome launched SILENT BACKGROUND (opt-in). Restore with: .\scripts\watch_lane_stack.ps1 -NoObserve"
} else {
    $chromeArgs = @(
        "--remote-debugging-port=$Port",
        "--user-data-dir=$ProfileDir",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,InterestCohorts",
        "--hide-crash-restore-bubble",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-background-media-suspend",
        "--window-position=80,50",
        "--window-size=1280,900",
        $Url
    )
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs
    Write-Host "Chrome launched VISIBLE (default) — CDP :$Port"
}

[pscustomobject]@{
    status = "STARTED"
    url = $Url
    port = $Port
    profileDir = $ProfileDir
    mode = if ($visible) { "visible" } else { "silent-background-opt-in" }
    policy = "KEEP_VISIBLE_DEFAULT"
    next = if ($visible) {
        "Window stays on-screen. Do not run hide_chrome_window without NEXUS_FORCE_HIDE=1."
    } else {
        "You opted into SilentBackground. Run restore_chrome_cdp_window.ps1 -ForceShow when done."
    }
} | Format-List
