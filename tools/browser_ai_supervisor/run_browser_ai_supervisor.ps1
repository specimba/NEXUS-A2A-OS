param(
    [int]$CdpPort = 9224,
    [string]$RequiredUrlPattern = 'grok\.com',
    [string]$GroundingRoot = "$env:LOCALAPPDATA\NEXUS\grounding"
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$profile = Join-Path $env:LOCALAPPDATA 'NEXUS\BrowserAI\ChromeProfile'
$versionUrl = "http://127.0.0.1:$CdpPort/json/version"

function Test-Cdp {
    try {
        $null = Invoke-WebRequest -UseBasicParsing $versionUrl -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Hide-ChromeWindow {
    $hideScript = Join-Path $PSScriptRoot 'hide_chrome_window.mjs'
    if (-not (Test-Path $hideScript)) { return }
    try {
        $result = node $hideScript $CdpPort $RequiredUrlPattern 2>&1
        $parsed = $result | ConvertFrom-Json
        if ($parsed.ok) {
            Write-Host "Chrome window moved off-screen via CDP (windowId=$($parsed.windowId))."
            return
        }
        Write-Host "CDP hide returned: $($parsed.error) - trying kill/restart..."
    } catch {
        Write-Host "CDP hide failed: $_ - trying kill/restart..."
    }
    Kill-ChromeAndRestart
}

function Kill-ChromeAndRestart {
    Write-Host "Killing visible Chrome for profile and restarting hidden..."
    $mainProc = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object {
        $_.CommandLine -like "*remote-debugging-port=$CdpPort*" -and $_.CommandLine -notlike "*--type=*"
    } | Select-Object -First 1
    if ($mainProc) {
        Stop-Process -Id $mainProc.ProcessId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
    $null = & (Join-Path $PSScriptRoot 'start_browser_ai_profile.ps1') -Port $CdpPort -ProfileDir $profile
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-Cdp)) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Cdp)) {
        Write-Host "FAILED to restart Chrome after kill."
        exit 3
    }
    Write-Host "Chrome restarted in hidden mode."
}

if (-not (Test-Cdp)) {
    $null = & (Join-Path $PSScriptRoot 'start_browser_ai_profile.ps1') -Port $CdpPort -ProfileDir $profile
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-Cdp)) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Cdp)) {
        exit 2
    }
} else {
    Hide-ChromeWindow
}

$env:NEXUS_GROUNDING_ROOT = $GroundingRoot
Push-Location $repo
try {
    & (Join-Path $PSScriptRoot 'run_external_director.ps1') `
        -Source grok `
        -CdpPort $CdpPort `
        -RequiredUrlPattern $RequiredUrlPattern `
        -RequiresBridge
    $directorExit = $LASTEXITCODE
} finally {
    Pop-Location
    Hide-ChromeWindow
}
exit $directorExit
