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
    $stderrFile = [System.IO.Path]::GetTempFileName()
    try {
        $rows = @(& docker ps -a --format '{{.Names}}|{{.State}}|{{.Status}}' 2>$stderrFile)
        if ($LASTEXITCODE -ne 0) {
            $stderr = Get-Content -LiteralPath $stderrFile -Raw -ErrorAction SilentlyContinue
            if ([string]::IsNullOrWhiteSpace($stderr)) {
                $stderr = "docker ps -a exited with code $LASTEXITCODE"
            }
            throw "Failed to inspect Docker containers: $stderr"
        }
    } finally {
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }

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
    foreach ($profileKey in $profileMap.Keys) {
        Write-Output "[$profileKey]"
        foreach ($name in $profileMap[$profileKey]) {
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
    if (-not $statusMap.ContainsKey($name)) {
        Write-Error "Container '$name' is not present in Docker"
        exit 1
    }
    if ($statusMap[$name].State -ne 'running') {
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

$failures = @()

foreach ($name in $toStop) {
    if ($PSCmdlet.ShouldProcess($name, 'docker stop')) {
        docker stop $name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Output "stopped`t$name"
        } else {
            Write-Error "Failed to stop container '$name'"
            $failures += $name
        }
    }
}

foreach ($name in $toStart) {
    if ($PSCmdlet.ShouldProcess($name, 'docker start')) {
        docker start $name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Output "started`t$name"
        } else {
            Write-Error "Failed to start container '$name'"
            $failures += $name
        }
    }
}

if ($failures.Count -gt 0) {
    exit 1
}
