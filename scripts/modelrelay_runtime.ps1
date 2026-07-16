# Repo-owned, fail-closed launcher for the NEXUS ModelRelay primary.
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7350,
    [string]$ConfigPath = "$env:USERPROFILE\.modelrelay.json",
    [string]$Bind = '0.0.0.0',
    [string]$TokenPath = "$env:USERPROFILE\.nexus\secrets\modelrelay_bearer.token",
    [string]$AllowedOrigins = 'http://127.0.0.1:7356,http://localhost:7356,http://127.0.0.1:3001,http://localhost:3001',
    [string]$HealthSamplerPath = '',
    [ValidateRange(1000, 600000)]
    [int]$FirstByteTimeoutMs = 45000,
    [ValidateRange(1000, 600000)]
    [int]$RouteFirstByteBudgetMs = 25000,
    [ValidateRange(1000, 900000)]
    [int]$TotalTimeoutMs = 180000,
    [ValidateRange(6, 60)]
    [int]$CanaryHourlyBudget = 24,
    [ValidateRange(60000, 900000)]
    [int]$CanaryMinSpacingMs = 150000,
    [ValidateRange(60000, 7200000)]
    [int]$CanaryProviderCooldownMs = 1800000
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$ServiceRoot = Join-Path $Root 'services\modelrelay-nexus'
$Cli = Join-Path $ServiceRoot 'src\cli.mjs'
$Verifier = Join-Path $ServiceRoot 'src\verify-runtime.mjs'
$Node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $HealthSamplerPath) {
    $HealthSamplerPath = Join-Path $Root 'logs\modelrelay_health_sampler.json'
}
$healthSamplerDirectory = Split-Path -Parent $HealthSamplerPath
if ($healthSamplerDirectory) {
    New-Item -ItemType Directory -Path $healthSamplerDirectory -Force | Out-Null
}

if (-not $Node) { throw 'Node.js is not installed or is not on PATH.' }
if (-not (Test-Path -LiteralPath $Cli)) { throw "Repo-owned ModelRelay CLI missing: $Cli" }
if (-not (Test-Path -LiteralPath $Verifier)) { throw "Runtime verifier missing: $Verifier" }
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "ModelRelay config missing: $ConfigPath" }

$loopback = $Bind -in @('127.0.0.1', '::1', 'localhost')
$token = ''
if (Test-Path -LiteralPath $TokenPath) {
    $token = (Get-Content -LiteralPath $TokenPath -Raw).Trim()
}
if (-not $loopback -and $token.Length -lt 32) {
    throw "Non-loopback ModelRelay bind requires a >=32 character token at $TokenPath"
}

$env:MODELRELAY_NEXUS_SAFE_RUNTIME = '1'
$env:MODELRELAY_DISABLE_AUTO_UPDATE = '1'
$env:MODELRELAY_BIND = $Bind
$env:MODELRELAY_CONFIG_PATH = (Resolve-Path -LiteralPath $ConfigPath).Path
$env:MODELRELAY_ALLOWED_ORIGINS = $AllowedOrigins
$env:MODELRELAY_FIRST_BYTE_TIMEOUT_MS = [string]$FirstByteTimeoutMs
$env:MODELRELAY_ROUTE_FIRST_BYTE_BUDGET_MS = [string]$RouteFirstByteBudgetMs
$env:MODELRELAY_TOTAL_TIMEOUT_MS = [string]$TotalTimeoutMs
$env:MODELRELAY_CANARY_HOURLY_BUDGET = [string]$CanaryHourlyBudget
$env:MODELRELAY_CANARY_MIN_SPACING_MS = [string]$CanaryMinSpacingMs
$env:MODELRELAY_CANARY_PROVIDER_COOLDOWN_MS = [string]$CanaryProviderCooldownMs
$env:MODELRELAY_HEALTH_SAMPLER_PATH = [System.IO.Path]::GetFullPath($HealthSamplerPath)
if ($token) { $env:MODELRELAY_BEARER_TOKEN = $token }

& $Node $Verifier
if ($LASTEXITCODE -ne 0) { throw "ModelRelay runtime verification failed with exit code $LASTEXITCODE" }

Write-Host ('Starting governed NEXUS ModelRelay on {0}:{1}' -f $Bind, $Port)
$arguments = @(
    $Cli,
    '--port', [string]$Port,
    '--bind', $Bind,
    '--config', $env:MODELRELAY_CONFIG_PATH,
    '--allowed-origins', $AllowedOrigins,
    '--no-log'
)
& $Node @arguments
exit $LASTEXITCODE
