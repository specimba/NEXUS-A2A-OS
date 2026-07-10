# watch_lane_stack.ps1
# ONE file you run — no multi-statement paste.
#
# Usage (from repo root):
#   .\scripts\watch_lane_stack.ps1              # fast: restore once if broken + silent preflight
#   .\scripts\watch_lane_stack.ps1 -Observe     # optional: dwell each lane tab (slow tab carousel)
#   .\scripts\watch_lane_stack.ps1 -NoObserve   # same as default (explicit)
#
# Policy 2026-07-10: never hide Chrome; default does NOT tab-travel for a minute.

param(
    [int]$Port = 9224,
    [switch]$Observe,
    [switch]$NoObserve
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

$env:VISIBLE_LANES = "1"
$env:NEXUS_KEEP_VISIBLE = "1"
$env:NEXUS_FORCE_HIDE = "0"
$env:NEXUS_CONTINUITY_LEDGER = "C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl"

# Permanent protect lock (survives supervisor restarts)
$protectDirs = @(
    "$Repo\NEXUSlogs\a2a_experiment",
    "C:\Users\speci.000\Downloads\cdp_agent_scratch"
)
$protectBody = @{
    protected = $true
    keep_visible = $true
    permanent = $true
    at = (Get-Date).ToUniversalTime().ToString("o")
    reason = "watch_lane_stack_keep_visible"
    port = $Port
    policy = "NEVER_OFFSCREEN_PARK"
} | ConvertTo-Json
foreach ($d in $protectDirs) {
    try {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        Set-Content -LiteralPath (Join-Path $d "WINDOW_PROTECT.json") -Value $protectBody -Encoding UTF8
    } catch { }
}

Write-Host "VISIBLE_LANES=1 NEXUS_KEEP_VISIBLE=1 NEXUS_FORCE_HIDE=0"
Write-Host "Running lane_stack_preflight on port $Port ..."

# One-shot restore only if window is offscreen/minimized — does not thrash focus every run path in daemon
$force = ".\scripts\restore_chrome_cdp_window.ps1"
if (Test-Path $force) {
    try {
        & $force -Port $Port -SkipEnsure -ForceShow -OnlyIfBroken -NoStealFocus 2>&1 | Out-Null
    } catch {
        try { & $force -Port $Port -SkipEnsure -ForceShow 2>&1 | Out-Null } catch { }
    }
}

$nodeArgs = @(".\tools\browser_ai_supervisor\lane_stack_preflight.mjs", "--port", "$Port")
# DEFAULT: silent (no --observe). Tab carousel only if -Observe explicitly set.
if ($Observe -and -not $NoObserve) {
    Write-Host "Observe mode: will dwell each lane tab (slow). Prefer default for daily work."
    $nodeArgs += "--observe"
    $nodeArgs += @("--dwellMs", "400")
} else {
    # Skip per-lane restore/bringToFront — window already fixed above once.
    $nodeArgs += "--no-restore"
}

& node @nodeArgs
$code = $LASTEXITCODE

Write-Host ""
Write-Host "Policy: Chrome stays visible. Hide path requires NEXUS_FORCE_HIDE=1 (do not set)."
Write-Host "If geometry ever breaks (1x1/-32000), optional gentle guard:"
Write-Host "  .\scripts\keep_visible_daemon.ps1 -OnlyIfBroken"
Write-Host "You should NOT need watch_lane_stack every few minutes anymore."

exit $code
