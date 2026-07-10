# keep_visible_daemon.ps1
# Gentle CDP lane visibility guard.
# ONLY repairs offscreen / 1x1 / minimized windows. Does NOT:
#   - hide Chrome
#   - maximize every tick
#   - steal focus when window is already fine
#   - tab-travel across lanes
#
#   .\scripts\keep_visible_daemon.ps1
#   .\scripts\keep_visible_daemon.ps1 -OnlyIfBroken   # default behavior
# Stop: Ctrl+C

param(
    [int]$Port = 9224,
    [int]$PollSeconds = 15,
    [switch]$OnlyIfBroken,
    [switch]$NoForceShow
)

# Default: only-if-broken (param default via $true logic)
if (-not $PSBoundParameters.ContainsKey("OnlyIfBroken")) {
    $OnlyIfBroken = $true
}

$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

$env:VISIBLE_LANES = "1"
$env:NEXUS_CONTINUITY_LEDGER = "C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl"
$env:NEXUS_ALLOW_FOREGROUND_LANE_REPAIR = "1"
$env:NEXUS_KEEP_VISIBLE = "1"
$env:NEXUS_FORCE_HIDE = "0"

$protectPaths = @(
    "$Repo\NEXUSlogs\a2a_experiment\WINDOW_PROTECT.json",
    "C:\Users\speci.000\Downloads\cdp_agent_scratch\WINDOW_PROTECT.json"
)
$protectBody = @{
    protected = $true
    keep_visible = $true
    permanent = $true
    at = (Get-Date).ToUniversalTime().ToString("o")
    reason = "operator_observation_daemon"
    port = $Port
    poll_seconds = $PollSeconds
    only_if_broken = [bool]$OnlyIfBroken
    policy = "NEVER_OFFSCREEN_PARK"
} | ConvertTo-Json

foreach ($protectPath in $protectPaths) {
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path $protectPath -Parent) | Out-Null
        Set-Content -LiteralPath $protectPath -Value $protectBody -Encoding UTF8
    } catch { }
}

Write-Host "=== NEXUS keep_visible_daemon (gentle) ==="
Write-Host "Port=$Port PollSeconds=$PollSeconds OnlyIfBroken=$OnlyIfBroken"
Write-Host "VISIBLE_LANES=1  NEXUS_KEEP_VISIBLE=1  NEXUS_FORCE_HIDE=0"
Write-Host "Protect: $($protectPaths -join '; ')"
Write-Host "Leaves healthy windows alone. Ctrl+C to stop."

$restoreJs = Join-Path $Repo "tools\browser_ai_supervisor\chrome_cdp_browser_restore.mjs"
$force = Join-Path $Repo "scripts\restore_chrome_cdp_window.ps1"

function Invoke-KeepVisibleOnce {
    # CDP restore with only-if-broken — no maximize spam
    if (Test-Path $restoreJs) {
        try {
            $null = & node $restoreJs --port $Port --mode normal --only-if-broken 2>&1
        } catch { }
    }
    if ((Test-Path $force) -and (-not $NoForceShow)) {
        try {
            & $force -Port $Port -SkipEnsure -ForceShow -OnlyIfBroken -NoStealFocus -NoMaximize 2>&1 | Out-Null
        } catch { }
    }
}

$tick = 0
while ($true) {
    $tick++
    $t0 = Get-Date
    Invoke-KeepVisibleOnce
    $ms = [int]((Get-Date) - $t0).TotalMilliseconds
    if (($tick % 4) -eq 1) {
        Write-Host ("[{0:HH:mm:ss}] keep-visible tick={1} took={2}ms (only_if_broken)" -f (Get-Date), $tick, $ms)
    }
    Start-Sleep -Seconds $PollSeconds
}
