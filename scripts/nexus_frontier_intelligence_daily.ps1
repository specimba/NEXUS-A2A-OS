# NEXUS daily frontier intelligence refresh.
#
# This is deliberately a bounded evidence job, not an auto-promotion job:
#   * OpenRouter + NVIDIA are catalog-listing-only discovery sources.
#   * Newly seen models stay candidate-only; this script never registers,
#     probes, routes, or edits client defaults for them.
#   * The automated benchmark leg uses only LMArena's official public
#     leaderboard dataset: it makes no credentialed benchmark or
#     provider-ranking request.  Its runtime sidecar is consumed by 7356 only
#     when it contains fresh Tier-1/Tier-2 capability evidence.
#
# Register manually after reviewing the first normal run:
# schtasks /Create /TN "NexusFrontierIntelligenceDaily" /SC DAILY /ST 03:17 ^
#   /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\speci.000\Documents\NEXUS\scripts\nexus_frontier_intelligence_daily.ps1" /F
#
# Dry run (no profile/runtime writes, no network):
# powershell -NoProfile -File .\scripts\nexus_frontier_intelligence_daily.ps1 -WhatIf

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [switch]$Offline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = 'C:\Users\speci.000\Documents\NEXUS'
# Mutable evidence belongs in the ignored repository runtime area by default.
# Some managed Windows profiles deny writes below $HOME/.nexus; using the same
# default as 7356 keeps the scheduled job and dashboard on one writable,
# non-versioned operational state root.  An operator may still point both
# processes at an explicitly managed external location.
$runtimeRoot = if ([string]::IsNullOrWhiteSpace($env:NEXUS_RUNTIME_STATE_ROOT)) {
    Join-Path $repo 'logs\runtime-state'
} else {
    $env:NEXUS_RUNTIME_STATE_ROOT
}
$scannerState = Join-Path $runtimeRoot 'frontier_scanner'
$arenaRoot = Join-Path $runtimeRoot 'arena'
$scoresOut = Join-Path $arenaRoot 'scores.json'
$statusOut = Join-Path $arenaRoot 'frontier_intelligence_status.json'
$candidateOut = Join-Path $scannerState 'latest_candidates.json'
$logRoot = Join-Path $repo 'logs'
$log = Join-Path $logRoot 'frontier_intelligence_daily.log'

function Write-RunLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    # Keep log text off the success-value output stream.  This function is
    # called by Invoke-PythonLogged, whose callers need an unambiguous boolean
    # to decide whether a bounded refresh really succeeded.
    Write-Host $line
    Add-Content -LiteralPath $log -Value $line
}

function Invoke-PythonLogged {
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    Write-RunLog "$Label starting"
    # PowerShell 7 can promote native stderr (including an import-time
    # warning) into a terminating NativeCommandError under the script-wide
    # Stop policy.  Preserve the warning in the bounded log, but make the
    # operation decision from Python's actual exit code.
    $lines = @()
    $exitCode = 1
    $priorErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $lines = @(& python @Arguments 2>&1)
        if ($null -ne $LASTEXITCODE) { $exitCode = $LASTEXITCODE }
    } finally {
        $ErrorActionPreference = $priorErrorActionPreference
    }
    foreach ($line in ($lines | Select-Object -Last 12)) {
        Write-RunLog "  $line"
    }
    if ($exitCode -ne 0) {
        Write-RunLog "$Label failed (exit=$exitCode)"
        return [bool]$false
    }
    Write-RunLog "$Label finished"
    return [bool]$true
}

function Write-RefreshStatus {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('succeeded', 'failed')][string]$State,
        [Parameter(Mandatory = $true)][ValidateSet('succeeded', 'failed', 'skipped')][string]$CatalogState,
        [Parameter(Mandatory = $true)][ValidateSet('succeeded', 'failed')][string]$EvidenceState,
        [Parameter(Mandatory = $true)][ValidateSet('succeeded', 'failed', 'skipped')][string]$SyncState
    )
    # This compact sidecar is deliberately safe for 7356 to expose.  It does
    # not include provider URLs, raw errors, credentials, or model payloads.
    $payload = [ordered]@{
        version = 1
        generated_at = [DateTime]::UtcNow.ToString('o')
        state = $State
        offline = [bool]$Offline
        stages = [ordered]@{
            catalog = $CatalogState
            evidence_ingest = $EvidenceState
            client_manifest_sync = $SyncState
        }
        evidence_sidecar_accepted = ($EvidenceState -eq 'succeeded')
        candidate_delta_available = (Test-Path -LiteralPath $candidateOut -PathType Leaf)
    }
    $temporary = "$statusOut.tmp"
    $json = $payload | ConvertTo-Json -Depth 4
    # Windows PowerShell's `-Encoding utf8` emits a BOM, while the 7356 Node
    # reader intentionally treats malformed status input as invalid.  Use an
    # explicit BOM-free UTF-8 write so a valid result is never discarded.
    [System.IO.File]::WriteAllText(
        $temporary,
        $json,
        [System.Text.UTF8Encoding]::new($false)
    )
    Move-Item -LiteralPath $temporary -Destination $statusOut -Force
}

if (-not $PSCmdlet.ShouldProcess($runtimeRoot, 'run daily bounded frontier discovery and benchmark evidence refresh')) {
    Write-Output "Would create $scannerState and $arenaRoot; would write candidate-only delta and runtime scores; no provider inference, model registration, or client-default changes."
    exit 0
}

New-Item -ItemType Directory -Force -Path $scannerState, $arenaRoot, $logRoot | Out-Null
Set-Location $repo
Write-RunLog 'frontier intelligence daily run starting (candidate-only discovery; no auto-promotion)'

$ok = $true
$catalogOk = $true
$catalogState = if ($Offline) { 'skipped' } else { 'failed' }
if ($Offline) {
    Write-RunLog 'catalog discovery skipped: Offline requested'
} else {
    # Exactly two catalog listings.  `delta` establishes/updates a local
    # baseline; without --add-to-watchlist it cannot cause probes or routing.
    $catalogOk = Invoke-PythonLogged -Label 'catalog delta (OpenRouter + NVIDIA)' -Arguments @(
        '-m', 'tools.frontier_scanner.orchestrator',
        '--state-dir', $scannerState,
        'delta', '--providers', 'openrouter', 'nvidia',
        '--emit-json', $candidateOut
    )
    $catalogState = if ($catalogOk) { 'succeeded' } else { 'failed' }
    if (-not $catalogOk) { $ok = $false }
}

$ingestArgs = @(
    '-m', 'nexus_os.relay.arena_ingest',
    # Artificial Analysis is credentialed and OpenRouter is usage-only, so
    # neither belongs in this unattended public-capability refresh.
    '--source', 'lmarena',
    '--out', $scoresOut,
    # Keep raw snapshots beside the consumed sidecar.  This avoids profile
    # ACL failures and allows a bounded, freshness-gated cache replay when a
    # public board is temporarily unreachable.
    '--cache-dir', (Join-Path $arenaRoot 'raw'),
    '--include-no-data',
    # A board outage must not replace the last valid evidence sidecar with an
    # all-no-data snapshot.
    '--require-capability-evidence'
)
if ($Offline) { $ingestArgs += '--offline' }
$arenaOk = Invoke-PythonLogged -Label 'public LMArena evidence ingest' -Arguments $ingestArgs
if (-not $arenaOk -and -not $Offline) {
    # One offline replay only.  arena_ingest still rejects evidence older than
    # its source horizon, so this cannot resurrect an obsolete board score.
    $cacheReplayArgs = @($ingestArgs)
    $cacheReplayArgs += '--offline'
    $arenaOk = Invoke-PythonLogged -Label 'cached LMArena evidence replay' -Arguments $cacheReplayArgs
    if ($arenaOk) { Write-RunLog 'public LMArena fetch failed; accepted a still-fresh cached evidence snapshot' }
}
$evidenceState = if ($arenaOk) { 'succeeded' } else { 'failed' }
if (-not $arenaOk) { $ok = $false }

# The 7356 dashboard projects the live relay manifest itself.  Do not couple
# this public evidence/discovery job to client-config writes (especially WSL
# Hermes) or let an unrelated client access blocker erase a valid score
# refresh.  Client synchronization remains a separate, explicit operation.
$syncState = 'skipped'
if ($arenaOk) {
    Write-RunLog 'client manifest sync skipped: this evidence job never mutates CLI configuration; 7356 reads live relay routes'
} else {
    Write-RunLog 'client manifest sync skipped: no fresh public capability sidecar was written'
}

try {
    Write-RefreshStatus -State $(if ($ok) { 'succeeded' } else { 'failed' }) `
        -CatalogState $catalogState -EvidenceState $evidenceState -SyncState $syncState
} catch {
    $ok = $false
    Write-RunLog "frontier intelligence status sidecar failed to write: $($_.Exception.Message)"
}

if ($ok) {
    Write-RunLog 'frontier intelligence daily run finished: evidence sidecar + candidate delta refreshed'
    exit 0
}

Write-RunLog 'frontier intelligence daily run finished with failures; prior valid sidecars/configs retained'
exit 1
