# Start dedicated Chrome for NEXUS Grok lane (CDP). Default: VISIBLE window.
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:USERPROFILE\.nexus_chrome_grok",
    [string]$StartUrl = $(if ($env:NEXUS_GROK_PROJECT_CHAT_URL) { $env:NEXUS_GROK_PROJECT_CHAT_URL } elseif ($env:NEXUS_GROK_PROJECT_URL) { $env:NEXUS_GROK_PROJECT_URL } else { "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba" }),
    [switch]$SilentBackground = $false
)

$ErrorActionPreference = "Stop"

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $chrome) { throw "Google Chrome not found." }
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$baseArgs = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts",
    $StartUrl
)

if ($SilentBackground) {
    Write-Host "Grok-lane Chrome CDP :$Port SILENT (not for passkey/login)."
    $chromeArgs = $baseArgs + @("--window-position=-32000,-32000", "--window-size=1,1", "--hide-crash-restore-bubble")
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Hidden
} else {
    Write-Host "Grok-lane Chrome CDP :$Port VISIBLE (passkey + Grok collab)."
    Start-Process -FilePath $chrome -ArgumentList $baseArgs
}

Start-Sleep -Seconds 2
try {
    Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 3 | Out-Null
    Write-Host "[ok] CDP port $Port is up"
} catch {
    Write-Warning "CDP port $Port not ready yet. Run: nexusctl grok-lane doctor"
}