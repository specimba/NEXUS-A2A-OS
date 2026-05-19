[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('status', 'core', 'observability', 'supabase-dev', 'ai-tools', 'all', 'none')]
    [string]$Mode = 'status'
)

$profileMap = [ordered]@{
    core = @(
        'redis-nexus',
        'nexus-kafka-bridge',
        'nexus-kafka-consumer',
        'supabase_db_NEO_agent'
    )
    observability = @(
        'redis-exporter',
        'grafana-monitoring',
        'cadvisor',
        'prometheus',
        'node-exporter',
        'autoops-otel-agent'
    )
    'supabase-dev' = @(
        'supabase_studio_NEO_agent',
        'supabase_pg_meta_NEO_agent',
        'supabase_edge_runtime_NEO_agent',
        'supabase_storage_NEO_agent',
        'supabase_rest_NEO_agent',
        'supabase_realtime_NEO_agent',
        'supabase_inbucket_NEO_agent',
        'supabase_auth_NEO_agent',
        'supabase_kong_NEO_agent',
        'supabase_analytics_NEO_agent'
    )
    'ai-tools' = @(
        'openwebui-extension-service',
        'openwebui-extension-mcp-gateway',
        'mindsdb_service',
        'pgvector_service'
    )
}

$managedContainers = $profileMap.Values | ForEach-Object { $_ } | Sort-Object -Unique

function Get-ContainerStatusMap {
    $rows = @(& docker ps -a --format '{{.Names}}|{{.State}}|{{.Status}}' 2>$null)
    $map = @{}
    foreach ($row in $rows) {
        $parts = $row -split '\|', 3
        if ($parts.Count -eq 3) {
            $map[$parts[0]] = [pscustomobject]@{
                Name = $parts[0]
                State = $parts[1]
                Status = $parts[2]
            }
        }
    }
    return $map
}

function Resolve-DesiredSet {
    param([string]$RequestedMode)

    switch ($RequestedMode) {
        'status' { return @() }
        'none' { return @() }
        'all' { return $managedContainers }
        'core' { return $profileMap.core }
        'observability' { return $profileMap.core + $profileMap.observability }
        'supabase-dev' { return $profileMap.core + $profileMap.'supabase-dev' }
        'ai-tools' { return $profileMap.core + $profileMap.'ai-tools' }
        default { throw "Unsupported mode: $RequestedMode" }
    }
}

$statusMap = Get-ContainerStatusMap

if ($Mode -eq 'status') {
    foreach ($profile in $profileMap.Keys) {
        Write-Output "[$profile]"
        foreach ($name in $profileMap[$profile]) {
            if ($statusMap.ContainsKey($name)) {
                $item = $statusMap[$name]
                Write-Output ("{0}`t{1}`t{2}" -f $item.Name, $item.State, $item.Status)
            } else {
                Write-Output ("{0}`tmissing`tmissing" -f $name)
            }
        }
        Write-Output ""
    }
    exit 0
}

$desired = Resolve-DesiredSet -RequestedMode $Mode | Sort-Object -Unique
$toStart = @()
$toStop = @()

foreach ($name in $desired) {
    if ($statusMap.ContainsKey($name) -and $statusMap[$name].State -ne 'running') {
        $toStart += $name
    }
}

foreach ($name in $managedContainers) {
    if ($desired -notcontains $name -and $statusMap.ContainsKey($name) -and $statusMap[$name].State -eq 'running') {
        $toStop += $name
    }
}

if (-not $toStart -and -not $toStop) {
    Write-Output "Mode '$Mode' already satisfied."
    exit 0
}

foreach ($name in $toStop) {
    if ($PSCmdlet.ShouldProcess($name, 'docker stop')) {
        docker stop $name | Out-Null
        Write-Output "stopped`t$name"
    }
}

foreach ($name in $toStart) {
    if ($PSCmdlet.ShouldProcess($name, 'docker start')) {
        docker start $name | Out-Null
        Write-Output "started`t$name"
    }
}
