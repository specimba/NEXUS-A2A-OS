# Controlled 7356-only deployment helper.  It never touches Brain (7352),
# ModelRelay (7350/7355), MCP (7354), or any user CLI configuration.
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [string]$NexusRoot = 'C:\Users\speci.000\Documents\NEXUS',
    [int]$HealthRetries = 20,
    [int]$HealthDelayMs = 500
)

$ErrorActionPreference = 'Stop'
$port = 7356
$dashboardScript = Join-Path $NexusRoot 'scripts\serve_dashboard_7356.js'
$stdout = Join-Path $NexusRoot 'logs\dashboard_7356.out.log'
$stderr = Join-Path $NexusRoot 'logs\dashboard_7356.err.log'

if (-not (Test-Path -LiteralPath $dashboardScript -PathType Leaf)) {
    throw "Dashboard entrypoint missing: $dashboardScript"
}
$node = (Get-Command node -ErrorAction Stop).Source

function Get-DashboardListenerPid {
    $match = netstat -ano -p tcp |
        Select-String -Pattern '^\s*TCP\s+127\.0\.0\.1:7356\s+0\.0\.0\.0:0\s+LISTENING\s+(\d+)\s*$' |
        Select-Object -First 1
    if (-not $match) { return $null }
    if ($match.Matches.Count -lt 1) { return $null }
    return [int]$match.Matches[0].Groups[1].Value
}

function Test-DashboardContract {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7356/health' -TimeoutSec 3 -ErrorAction Stop
        $payload = $response.Content | ConvertFrom-Json -ErrorAction Stop
        return $response.StatusCode -eq 200 -and $payload.service -eq 'static_dashboard' -and $payload.plane_owner -eq 'static_dashboard'
    } catch {
        return $false
    }
}

$currentPid = Get-DashboardListenerPid
if ($currentPid) {
    if (-not (Test-DashboardContract)) {
        throw 'Port 7356 is occupied by a process that fails the static_dashboard ownership contract.'
    }
    if ($PSCmdlet.ShouldProcess("PID $currentPid on 7356", 'stop the verified static dashboard for source reload')) {
        Stop-Process -Id $currentPid -Force -ErrorAction Stop
        Start-Sleep -Milliseconds $HealthDelayMs
    }
}

if ($PSCmdlet.ShouldProcess('NEXUS static dashboard 7356', 'start the repository dashboard entrypoint')) {
    New-Item -ItemType Directory -Path (Join-Path $NexusRoot 'logs') -Force | Out-Null
    Start-Process -WindowStyle Hidden -FilePath $node -ArgumentList @($dashboardScript) -WorkingDirectory $NexusRoot `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
}

if ($WhatIfPreference) {
    [ordered]@{ status = 'would_restart'; port = $port; source = $dashboardScript } | ConvertTo-Json
    return
}

for ($attempt = 1; $attempt -le $HealthRetries; $attempt += 1) {
    Start-Sleep -Milliseconds $HealthDelayMs
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7356/api/client-manifest' -TimeoutSec 3 -ErrorAction Stop
        $manifest = $response.Content | ConvertFrom-Json -ErrorAction Stop
        $frontierResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7356/api/frontier-intelligence' -TimeoutSec 3 -ErrorAction Stop
        $frontier = $frontierResponse.Content | ConvertFrom-Json -ErrorAction Stop
        if (
            $response.StatusCode -eq 200 -and
            $manifest.schema_version -eq 1 -and
            $manifest.contract.source -eq 'nexus-model-arena-live-projection' -and
            $frontierResponse.StatusCode -eq 200 -and
            $frontier.schema_version -eq 1 -and
            $frontier.policy.candidate_only -eq $true -and
            $frontier.policy.automatic_registration -eq $false -and
            $frontier.policy.automatic_routing -eq $false
        ) {
            [ordered]@{
                status = 'restarted'
                port = $port
                old_pid = $currentPid
                canonical_cli_routes = $manifest.summary.canonical_cli_routes
                observed_healthy_routes = $manifest.summary.observed_healthy_routes
                frontier_intelligence_state = $frontier.state
            } | ConvertTo-Json
            return
        }
    } catch {}
}
throw '7356 restart completed but the manifest or candidate-only frontier-intelligence contract did not satisfy the live contract.'
