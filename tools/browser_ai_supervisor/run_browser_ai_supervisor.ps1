param(
    [int]$CdpPort = 9224,
    [string]$RequiredUrlPattern = 'grok\.com',
    [string]$GroundingRoot = "$env:LOCALAPPDATA\NEXUS\grounding"
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$profile = Join-Path $env:LOCALAPPDATA 'NEXUS\BrowserAI\ChromeProfile'
$versionUrl = "http://127.0.0.1:$CdpPort/json/version"
$runtime = Join-Path $env:LOCALAPPDATA 'NEXUS\BrowserAI\runtime'

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
        Write-Warning "CDP hide returned: $($parsed.error)"
    } catch {
        Write-Warning "CDP hide failed: $_"
    }
}

function Maybe-HideChrome {
    if ($env:VISIBLE_LANES -eq "1") {
        Write-Host "VISIBLE_LANES=1: skipping hide for observation"
        return
    }
    Hide-ChromeWindow
}

if (-not (Test-Cdp)) {
    Maybe-HideChrome
    $null = & (Join-Path $PSScriptRoot 'start_browser_ai_profile.ps1') -Port $CdpPort -ProfileDir $profile
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-Cdp)) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Cdp)) {
        Maybe-HideChrome
        exit 2
    }
} else {
    Maybe-HideChrome
}

$env:NEXUS_GROUNDING_ROOT = $GroundingRoot
$env:NEXUS_CONTINUITY_LEDGER = Join-Path $GroundingRoot "continuity_runs.jsonl"
Push-Location $repo
try {
    & (Join-Path $PSScriptRoot 'run_external_director.ps1') `
        -Source grok `
        -CdpPort $CdpPort `
        -RuntimeDir $runtime `
        -RequiredUrlPattern $RequiredUrlPattern `
        -RequiresBridge
    $directorExit = $LASTEXITCODE
} finally {
    Pop-Location
    Maybe-HideChrome
}
exit $directorExit



