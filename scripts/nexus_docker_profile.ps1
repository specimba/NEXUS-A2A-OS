<# 
NEXUS Docker runtime profile controller.

Usage examples:
  powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_profile.ps1 -Mode status
  powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_profile.ps1 -Mode core
  powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_profile.ps1 -Mode supabase-dev -WhatIf

Modes:
  status        Report all known containers.
  core          Run only the NEXUS core Redis/Kafka/Postgres containers.
  supabase-dev  Run core plus local Supabase NEO_agent.
  observability Run core plus Prometheus/Grafana/cAdvisor/exporters.
  ai-tools      Run core plus OpenWebUI/MindsDB/pgVector tools.
  lab           Run core plus supabase-dev, observability, and ai-tools.

Docker Desktop marketplace extension containers stay off unless -IncludeExtensions
is used with -Mode lab.

Docker Desktop can restart marketplace extension containers after a Desktop/WSL
restart. Run -Mode core again after Docker Desktop restarts unless the active
mission intentionally needs a heavier profile.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("status", "core", "supabase-dev", "observability", "ai-tools", "lab")]
    [string]$Mode = "status",

    [switch]$IncludeExtensions
)

$profiles = [ordered]@{
    core = @(
        "nexus-kafka-bridge",
        "nexus-kafka-consumer",
        "redis-nexus",
        "supabase_db_NEO_agent"
    )
    supabase_dev = @(
        "supabase_studio_NEO_agent",
        "supabase_pg_meta_NEO_agent",
        "supabase_edge_runtime_NEO_agent",
        "supabase_storage_NEO_agent",
        "supabase_rest_NEO_agent",
        "supabase_realtime_NEO_agent",
        "supabase_inbucket_NEO_agent",
        "supabase_auth_NEO_agent",
        "supabase_kong_NEO_agent",
        "supabase_analytics_NEO_agent",
        "supabase_db_NEO_agent"
    )
    observability = @(
        "redis-exporter",
        "grafana-monitoring",
        "cadvisor",
        "prometheus",
        "node-exporter",
        "autoops-otel-agent"
    )
    ai_tools = @(
        "openwebui-extension-service",
        "openwebui-extension-mcp-gateway",
        "rw4lll_openwebui-docker-extension-desktop-extension-service",
        "mindsdb_service",
        "pgvector_service"
    )
    extension_tools = @(
        "signalonefrontend",
        "signaloneagent",
        "virag_redis-enterprise-docker-extension-desktop-extension-setup-1",
        "virag_redis-enterprise-docker-extension-desktop-extension-service",
        "kong_konnect-docker-extension-desktop-extension-service",
        "coder_embedded_dd_vm",
        "mochoa_coder-docker-extension-desktop-extension-coder-docker-extension-1",
        "grafana-docker-desktop-extension-alloy",
        "grafana_docker-desktop-extension-desktop-extension-grafana-docker-desktop-extension-1",
        "tailscale_docker-extension-desktop-extension-service",
        "saniewski_mongo-express-docker-extension-desktop-extension-service",
        "drewsk_docker-sql-extension-desktop-extension-service",
        "pgadmin4_embedded_dd_vm",
        "mochoa_pgadmin4-docker-extension-desktop-extension-pgadmin4-docker-extension-1",
        "portainer_portainer-docker-extension-desktop-extension-service",
        "ngrok_ngrok-docker-extension-desktop-extension-service",
        "ambassador_telepresence-docker-extension-desktop-extension-service"
    )
}

function Get-DockerNames {
    param([switch]$All)

    if ($All) {
        return @(docker ps -a --format "{{.Names}}")
    }

    return @(docker ps --format "{{.Names}}")
}

function Select-Known {
    param(
        [string[]]$Names,
        [string[]]$Available
    )

    return @($Names | Where-Object { $Available -contains $_ } | Select-Object -Unique)
}

function Show-Status {
    Write-Host "Known NEXUS Docker containers:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"
}

if ($Mode -eq "status") {
    Show-Status
    exit 0
}

$allKnownOptional = @(
    $profiles.supabase_dev +
    $profiles.observability +
    $profiles.ai_tools +
    $profiles.extension_tools
) | Select-Object -Unique

$target = @($profiles.core)
$stopSet = @()

switch ($Mode) {
    "core" {
        $stopSet = $allKnownOptional
    }
    "supabase-dev" {
        $target += $profiles.supabase_dev
        $stopSet = @($profiles.observability + $profiles.ai_tools + $profiles.extension_tools) | Select-Object -Unique
    }
    "observability" {
        $target += $profiles.observability
        $stopSet = @($profiles.supabase_dev + $profiles.ai_tools + $profiles.extension_tools) | Select-Object -Unique
    }
    "ai-tools" {
        $target += $profiles.ai_tools
        $stopSet = @($profiles.supabase_dev + $profiles.observability + $profiles.extension_tools) | Select-Object -Unique
    }
    "lab" {
        $target += $profiles.supabase_dev + $profiles.observability + $profiles.ai_tools
        if ($IncludeExtensions) {
            $target += $profiles.extension_tools
            $stopSet = @()
        } else {
            $stopSet = $profiles.extension_tools
        }
    }
}

$target = @($target | Select-Object -Unique)
$stopSet = @($stopSet | Where-Object { $target -notcontains $_ } | Select-Object -Unique)
$allContainers = Get-DockerNames -All
$runningContainers = Get-DockerNames

$toStop = Select-Known -Names $stopSet -Available $runningContainers
$toStart = @(Select-Known -Names $target -Available $allContainers | Where-Object { $runningContainers -notcontains $_ })

if ($toStop.Count -gt 0) {
    if ($PSCmdlet.ShouldProcess(($toStop -join ", "), "docker stop")) {
        docker stop @toStop
    }
} else {
    Write-Host "No optional containers to stop for mode '$Mode'."
}

if ($toStart.Count -gt 0) {
    if ($PSCmdlet.ShouldProcess(($toStart -join ", "), "docker start")) {
        docker start @toStart
    }
} else {
    Write-Host "No stopped target containers to start for mode '$Mode'."
}

Show-Status
