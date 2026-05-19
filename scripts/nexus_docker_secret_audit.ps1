[CmdletBinding()]
param(
    [string]$BridgeContainer = 'nexus-kafka-bridge',
    [string]$RedisContainer = 'redis-nexus',
    [string]$SupabaseDbContainer = 'supabase_db_NEO_agent'
)

$dockerErrors = New-Object 'System.Collections.Generic.List[string]'

function Get-DockerJson {
    param(
        [string[]]$Arguments
    )

    $errorText = $null
    $raw = & docker @Arguments 2>&1
    if (-not $raw) {
        return $null
    }
    $rawText = ($raw | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        $dockerErrors.Add($rawText) | Out-Null
        return $null
    }
    return $rawText | ConvertFrom-Json
}

function Get-DockerInspect {
    param(
        [string]$ContainerName
    )

    $items = Get-DockerJson -Arguments @('inspect', $ContainerName)
    if (-not $items) {
        return $null
    }
    if ($items -is [array]) {
        return $items[0]
    }
    return $items
}

function Test-ComposeInlineSecret {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    $pattern = '^\s+(KAFKA_API_KEY|KAFKA_API_SECRET|POSTGRES_PASSWORD)\s*:\s*.+$'
    return [bool](Select-String -LiteralPath $Path -Pattern $pattern)
}

function Test-ComposeLocalhostBind {
    param(
        [string]$Path,
        [string]$Port
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    $pattern = "127\.0\.0\.1:${Port}:${Port}"
    return [bool](Select-String -LiteralPath $Path -Pattern $pattern)
}

$bridgeInspect = Get-DockerInspect -ContainerName $BridgeContainer
$supabaseInspect = Get-DockerInspect -ContainerName $SupabaseDbContainer
$redisInspect = Get-DockerInspect -ContainerName $RedisContainer

$bridgeLabels = if ($bridgeInspect) { $bridgeInspect.Config.Labels } else { $null }
$bridgeEnv = if ($bridgeInspect) { $bridgeInspect.Config.Env } else { @() }
$supabaseLabels = if ($supabaseInspect) { $supabaseInspect.Config.Labels } else { $null }
$supabasePorts = if ($supabaseInspect) { $supabaseInspect.HostConfig.PortBindings } else { $null }
$redisPorts = if ($redisInspect) { $redisInspect.HostConfig.PortBindings } else { $null }

$bridgeComposePath = $bridgeLabels.'com.docker.compose.project.config_files'
$bridgeWorkingDir = $bridgeLabels.'com.docker.compose.project.working_dir'
$redisComposePath = if ($bridgeWorkingDir) { Join-Path $bridgeWorkingDir 'docker-compose-redis.yml' } else { $null }

$bridgeSecretKeysPresent = @(
    'KAFKA_API_KEY',
    'KAFKA_API_SECRET',
    'POSTGRES_PASSWORD'
) | Where-Object { $bridgeEnv -match "^$_=" }

$result = [pscustomobject]@{
    BridgeComposePath = $bridgeComposePath
    BridgeInlineSecretKeysPresent = $bridgeSecretKeysPresent
    BridgeComposeUsesInlineSecrets = if ($bridgeComposePath) { Test-ComposeInlineSecret -Path $bridgeComposePath } else { $false }
    RedisComposePath = $redisComposePath
    RedisLocalhostOnlyConfigured = if ($redisComposePath) { Test-ComposeLocalhostBind -Path $redisComposePath -Port '6379' } else { $false }
    RedisPublishedHostIp = if ($redisPorts.'6379/tcp') { $redisPorts.'6379/tcp'[0].HostIp } else { $null }
    SupabaseProject = $supabaseLabels.'com.supabase.cli.project'
    SupabasePublishedHostIp = if ($supabasePorts.'5432/tcp') { $supabasePorts.'5432/tcp'[0].HostIp } else { $null }
    SupabasePublishedHostPort = if ($supabasePorts.'5432/tcp') { $supabasePorts.'5432/tcp'[0].HostPort } else { $null }
    Tcp2375Listening = [bool](Get-NetTCPConnection -LocalPort 2375 -ErrorAction SilentlyContinue)
    DockerInspectErrors = @($dockerErrors | Select-Object -Unique)
}

$result | ConvertTo-Json -Depth 4
