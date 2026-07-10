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

# Permanent operator policy: CDP lane Chrome stays visible.
# Hide-to--32000 is disabled unless NEXUS_FORCE_HIDE=1 (not set here).
$env:NEXUS_KEEP_VISIBLE = '1'
$env:VISIBLE_LANES = '1'
if (-not $env:NEXUS_FORCE_HIDE) { $env:NEXUS_FORCE_HIDE = '0' }

function Test-Cdp {
    try {
        $null = Invoke-WebRequest -UseBasicParsing $versionUrl -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Write-KeepVisibleProtect {
    $paths = @(
        (Join-Path $repo "NEXUSlogs\a2a_experiment\WINDOW_PROTECT.json"),
        "C:\Users\speci.000\Downloads\cdp_agent_scratch\WINDOW_PROTECT.json"
    )
    $body = @{
        protected = $true
        keep_visible = $true
        permanent = $true
        at = (Get-Date).ToUniversalTime().ToString('o')
        reason = 'run_browser_ai_supervisor_default_keep_visible'
        port = $CdpPort
        policy = 'NEVER_OFFSCREEN_PARK'
    } | ConvertTo-Json
    foreach ($p in $paths) {
        try {
            $dir = Split-Path $p -Parent
            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            Set-Content -LiteralPath $p -Value $body -Encoding UTF8
        } catch { }
    }
}

Write-KeepVisibleProtect

if (-not (Test-Cdp)) {
    Write-Host "CDP down — starting VISIBLE lane Chrome (never offscreen default)."
    $startProfile = Join-Path $PSScriptRoot 'start_browser_ai_profile.ps1'
    if (Test-Path $startProfile) {
        # Visible default (ShowWindow). Do not launch SilentBackground.
        $null = & $startProfile -Port $CdpPort -ProfileDir $profile -ShowWindow
    } else {
        & (Join-Path $repo 'scripts\start_grok_cdp_9224.ps1') -Port $CdpPort -ProfileDir $profile
    }
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-Cdp)) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Cdp)) {
        Write-Warning "CDP still down after visible start."
        exit 2
    }
} else {
    Write-Host "CDP already up on :$CdpPort — leave window visible (no hide)."
}

$env:NEXUS_GROUNDING_ROOT = $GroundingRoot
if (-not $env:NEXUS_CONTINUITY_LEDGER) {
    $vaultLedger = 'C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl'
    if (Test-Path (Split-Path $vaultLedger -Parent)) {
        $env:NEXUS_CONTINUITY_LEDGER = $vaultLedger
    } else {
        $env:NEXUS_CONTINUITY_LEDGER = Join-Path $GroundingRoot "NEXUScontinuity_runs.jsonl"
    }
}

# Preflight: silent (no --observe tab carousel). One-shot readiness only.
$preflight = Join-Path $PSScriptRoot 'lane_stack_preflight.mjs'
if (Test-Path $preflight) {
    try {
        Write-Host "lane_stack_preflight (silent, no tab travel) on port $CdpPort ..."
        node $preflight --port $CdpPort --lanes grok,gemini,qwen,chatgpt --no-restore --ledger $env:NEXUS_CONTINUITY_LEDGER
    } catch {
        Write-Warning "lane_stack_preflight failed: $_"
    }
}

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
    # NEVER re-hide after director. Window stays where the operator left it.
    Write-Host "Director finished — Chrome left visible (no post-hide)."
}
exit $directorExit
