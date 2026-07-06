param(
    [string]$Url = "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
    [switch]$ShowWindow = $false
)

$ErrorActionPreference = "Stop"

$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    $chrome = "chrome.exe"
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$args = @(
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

if (-not $ShowWindow) {
    $args += @("--window-position=-32000,-32000", "--window-size=1,1")
    Start-Process -FilePath $chrome -ArgumentList $args -WindowStyle Hidden
    Write-Host "Chrome launched SILENT BACKGROUND MODE (offscreen, hidden)."
} else {
    Start-Process -FilePath $chrome -ArgumentList $args
    Write-Host "Chrome launched VISIBLE — log in to Grok once, then close."
}

[pscustomobject]@{
    status = "STARTED"
    url = $Url
    port = $Port
    profileDir = $ProfileDir
    mode = if ($ShowWindow) { "visible" } else { "silent-background" }
    next = if ($ShowWindow) {
        "Log into Grok in the opened browser, then run control_surface_doctor.ps1 -RequiredUrlPattern 'grok\\.com'. Future starts will be silent."
    } else {
        "Running in background. To re-auth: start_browser_ai_profile.ps1 -ShowWindow"
    }
} | Format-List
