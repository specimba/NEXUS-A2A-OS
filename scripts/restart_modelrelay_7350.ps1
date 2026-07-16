# Controlled deployment helper for the repo-owned ModelRelay primary.
#
# It only stops a listener after proving that 7350 is the expected governed
# ModelRelay surface.  It preserves the existing non-loopback bind needed by
# WSL clients, never edits provider configuration or secrets, and proves the
# restarted process exposes the entitlement-aware health sampler contract.
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [string]$NexusRoot = 'C:\Users\speci.000\Documents\NEXUS',
    [string]$ConfigPath = "$env:USERPROFILE\.modelrelay.json",
    [ValidateSet('0.0.0.0', '127.0.0.1', '::1', 'localhost')]
    [string]$Bind = '0.0.0.0',
    [int]$HealthRetries = 30,
    [int]$HealthDelayMs = 750
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$port = 7350
$runtime = Join-Path $NexusRoot 'scripts\modelrelay_runtime.ps1'
$stdout = Join-Path $NexusRoot 'logs\modelrelay_7350.out.log'
$stderr = Join-Path $NexusRoot 'logs\modelrelay_7350.err.log'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

if (-not (Test-Path -LiteralPath $runtime -PathType Leaf)) {
    throw "Repo-owned ModelRelay runtime launcher missing: $runtime"
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "ModelRelay config missing: $ConfigPath"
}

function Get-RelayListenerPid {
    $match = netstat -ano -p tcp |
        Select-String -Pattern '^\s*TCP\s+(?:0\.0\.0\.0|127\.0\.0\.1|\[::\]|\[::1\]):7350\s+0\.0\.0\.0:0\s+LISTENING\s+(\d+)\s*$' |
        Select-Object -First 1
    if (-not $match -or $match.Matches.Count -lt 1) { return $null }
    return [int]$match.Matches[0].Groups[1].Value
}

function Get-RelayEstablishedConnections {
    param([int]$OwnerPid)

    # A forced process stop cuts active client requests.  Count only connections
    # owned by the already-verified listener; the caller treats any such
    # connection as a drain gate rather than guessing that a request is idle.
    return @(
        netstat -ano -p tcp |
            Select-String -Pattern '^\s*TCP\s+\S+:7350\s+\S+\s+ESTABLISHED\s+(\d+)\s*$' |
            Where-Object {
                $_.Matches.Count -gt 0 -and
                [int]$_.Matches[0].Groups[1].Value -eq $OwnerPid
            }
    )
}

function Test-GovernedRelayContract {
    try {
        $metaResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7350/api/meta' -TimeoutSec 3 -ErrorAction Stop
        $samplerResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7350/api/health-sampler' -TimeoutSec 3 -ErrorAction Stop
        $meta = $metaResponse.Content | ConvertFrom-Json -ErrorAction Stop
        $sampler = $samplerResponse.Content | ConvertFrom-Json -ErrorAction Stop
        return (
            $metaResponse.StatusCode -eq 200 -and
            $meta.version -eq '1.18.0' -and
            $samplerResponse.StatusCode -eq 200 -and
            $sampler.policy -eq 'bounded_provider_aware_canary_v1'
        )
    } catch {
        return $false
    }
}

$currentPid = Get-RelayListenerPid
$activeConnections = @()
if ($currentPid) {
    if (-not (Test-GovernedRelayContract)) {
        throw 'Port 7350 is occupied by a process that fails the governed ModelRelay ownership contract.'
    }
    $activeConnections = @(Get-RelayEstablishedConnections -OwnerPid $currentPid)
    if ($activeConnections.Count -gt 0) {
        $message = "Refusing 7350 restart while $($activeConnections.Count) active ModelRelay connection(s) are owned by PID $currentPid. Wait for requests to drain and rerun this helper."
        if ($WhatIfPreference) {
            [ordered]@{
                status = 'would_block_active_connections'
                port = $port
                current_pid = $currentPid
                active_connections = $activeConnections.Count
                reason = 'wait_for_requests_to_drain'
            } | ConvertTo-Json
            return
        }
        throw $message
    }
    if ($PSCmdlet.ShouldProcess("PID $currentPid on 7350", 'stop the verified governed ModelRelay for source reload')) {
        Stop-Process -Id $currentPid -Force -ErrorAction Stop
        Start-Sleep -Milliseconds $HealthDelayMs
    }
}

if ($PSCmdlet.ShouldProcess('NEXUS governed ModelRelay 7350', 'start the repository runtime launcher')) {
    New-Item -ItemType Directory -Path (Join-Path $NexusRoot 'logs') -Force | Out-Null
    Start-Process -WindowStyle Hidden -FilePath $pwsh -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $runtime,
        '-Port', [string]$port, '-ConfigPath', $ConfigPath, '-Bind', $Bind
    ) -WorkingDirectory $NexusRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr
}

if ($WhatIfPreference) {
    [ordered]@{
        status = 'would_restart'
        port = $port
        source = $runtime
        bind = $Bind
        active_connections = $activeConnections.Count
        preserves = @('provider_config', 'provider_credentials', 'bearer_token_path', 'health_sampler_state')
    } | ConvertTo-Json
    return
}

for ($attempt = 1; $attempt -le $HealthRetries; $attempt += 1) {
    Start-Sleep -Milliseconds $HealthDelayMs
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7350/api/health-sampler' -TimeoutSec 3 -ErrorAction Stop
        $modelsResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7350/v1/models' -TimeoutSec 3 -ErrorAction Stop
        $sampler = $response.Content | ConvertFrom-Json -ErrorAction Stop
        $models = $modelsResponse.Content | ConvertFrom-Json -ErrorAction Stop
        $hasTerminalCanaryExclusions = (
            $null -ne $sampler.PSObject.Properties['terminalCanaryExclusions'] -and
            $null -ne $sampler.terminalCanaryExclusions
        )
        $hasResilientAlias = @(
            $models.data | Where-Object { $_.id -eq 'nexus-resilient' }
        ).Count -eq 1
        $hasExpandedCanaryCadence = (
            [int]$sampler.globalLimitPerWindow -ge 24 -and
            [int]$sampler.minimumSpacingSeconds -le 150
        )
        if (
            $response.StatusCode -eq 200 -and
            $modelsResponse.StatusCode -eq 200 -and
            $sampler.policy -eq 'bounded_provider_aware_canary_v1' -and
            $null -ne $sampler.activePersistedAccessBlocks -and
            $hasTerminalCanaryExclusions -and
            $hasResilientAlias -and
            $hasExpandedCanaryCadence
        ) {
            [ordered]@{
                status = 'restarted'
                port = $port
                old_pid = $currentPid
                bind = $Bind
                sampler_window_remaining = $sampler.remainingInWindow
                active_access_blocks = $sampler.activePersistedAccessBlocks
                terminal_canary_exclusions = $sampler.terminalCanaryExclusions
                canary_hourly_budget = $sampler.globalLimitPerWindow
                canary_minimum_spacing_seconds = $sampler.minimumSpacingSeconds
                resilient_alias = 'nexus-resilient'
            } | ConvertTo-Json
            return
        }
    } catch {}
}

throw '7350 restart completed but the entitlement-aware governed health-sampler contract did not become ready.'
