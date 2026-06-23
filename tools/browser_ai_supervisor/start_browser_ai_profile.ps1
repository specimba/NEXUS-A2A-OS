param(
    [string]$Url = "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"
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
    "--new-window",
    $Url
)

Start-Process -FilePath $chrome -ArgumentList $args

[pscustomobject]@{
    status = "STARTED"
    url = $Url
    port = $Port
    profileDir = $ProfileDir
    next = "If this profile is not authenticated, log into Grok once in the opened browser, then run control_surface_doctor.ps1 with -RequiredUrlPattern 'grok\\.com'."
} | Format-List
