# Read-only diagnosis for the Hermes session that runs in WSL.
#
# This script never starts/stops services, writes configuration, reads a relay
# bearer, or makes a chat-completion request.  It intentionally distinguishes
# the Windows Hermes candidate configuration from the WSL configuration used
# by a prompt such as `speci@specimbaPC:~$ hermes`.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose_hermes_modelrelay.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose_hermes_modelrelay.ps1 -WhatIf
#
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'None')]
param(
    [string]$Distro = 'Ubuntu',
    [string]$RelayBaseUrl = 'http://127.0.0.1:7350',
    [string]$ArenaBaseUrl = 'http://127.0.0.1:7356',
    [ValidateRange(1, 30)]
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = 'Stop'

$requiredModels = @('glm-5.2', 'labs-leanstral-1-5-1')
$managedStart = '# === nexusctl model-sync providers (managed) ==='

function Assert-CanonicalLoopbackBaseUrl {
    param(
        [string]$Value,
        [int]$ExpectedPort,
        [string]$Label
    )

    try {
        $uri = [Uri]$Value
    } catch {
        throw "$Label is not a valid URL."
    }
    if (
        $uri.Scheme -ne 'http' -or
        $uri.Host -notin @('127.0.0.1', 'localhost') -or
        $uri.Port -ne $ExpectedPort -or
        -not [string]::IsNullOrEmpty($uri.Query) -or
        -not [string]::IsNullOrEmpty($uri.Fragment)
    ) {
        throw "$Label must be the canonical loopback HTTP endpoint on port $ExpectedPort."
    }
    return $uri.GetLeftPart([System.UriPartial]::Authority).TrimEnd('/')
}

function Get-PropertyValue {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Get-HermesConfigFootprint {
    param(
        [string]$Instance,
        [string]$Role,
        [string]$DisplayPath,
        [System.IO.FileInfo]$Path
    )

    $result = [ordered]@{
        instance = $Instance
        role = $Role
        config_path = $DisplayPath
        status = 'not_found'
        exists = $false
        readable = $false
        modelrelay_reference = $false
        managed_block_present = $false
        mentions_primary_model = $false
        mentions_fallback_model = $false
    }

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return [pscustomobject]$result
    }
    $result.exists = $true
    try {
        # The content never leaves this process.  Only fixed boolean evidence
        # is emitted so a local key or user setting cannot leak into logs.
        $text = [System.IO.File]::ReadAllText($Path.FullName)
        $result.readable = $true
        $result.status = 'readable_diagnostic_only'
        $result.modelrelay_reference = (
            $text -match '(?im)^\s*(?:provider|default_provider)\s*:\s*modelrelay\s*(?:#.*)?$' -or
            $text -match '(?im)^\s{2,}modelrelay\s*:'
        )
        $result.managed_block_present = $text.Contains($managedStart)
        $result.mentions_primary_model = $text -match '(?i)\bglm-5\.2\b'
        $result.mentions_fallback_model = $text -match '(?i)\blabs-leanstral-1-5-1\b'
    } catch {
        $result.status = "unreadable:$($_.Exception.GetType().Name)"
    }
    return [pscustomobject]$result
}

function Get-WslHermesFootprint {
    param([string]$TargetDistro)

    $result = [ordered]@{
        instance = 'wsl'
        role = 'authoritative_for_a_linux_hermes_session'
        distro = $TargetDistro
        config_path = '~/.hermes/config.yaml'
        status = 'unavailable'
        wsl_reachable = $false
        hermes_binary_present = $false
        config_exists = $false
        config_readable = $false
        modelrelay_reference = $false
        managed_block_present = $false
        mentions_primary_model = $false
        mentions_fallback_model = $false
    }

    if ($TargetDistro -notmatch '^[A-Za-z0-9._-]+$') {
        $result.status = 'invalid_distro_name'
        return [pscustomobject]$result
    }
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        $result.status = 'wsl_command_missing'
        return [pscustomobject]$result
    }

    # No config text is printed or passed to Windows.  The fixed shell program
    # returns only boolean facts, and it performs no writes or relay calls.
    $probe = @'
p="$HOME/.hermes/config.yaml"
yn() { if "$@" >/dev/null 2>&1; then printf 'true\n'; else printf 'false\n'; fi; }
printf 'hermes_binary_present='; yn command -v hermes
printf 'config_exists='; yn test -f "$p"
printf 'config_readable='; yn test -r "$p"
if test -r "$p"; then
  printf 'modelrelay_reference='; yn grep -Eqi '^[[:space:]]*(provider|default_provider)[[:space:]]*:[[:space:]]*modelrelay([[:space:]]|#|$)|^[[:space:]]{2,}modelrelay[[:space:]]*:' "$p"
  printf 'managed_block_present='; yn grep -Fqi '# === nexusctl model-sync providers (managed) ===' "$p"
  printf 'mentions_primary_model='; yn grep -Fqi 'glm-5.2' "$p"
  printf 'mentions_fallback_model='; yn grep -Fqi 'labs-leanstral-1-5-1' "$p"
else
  printf 'modelrelay_reference=false\nmanaged_block_present=false\nmentions_primary_model=false\nmentions_fallback_model=false\n'
fi
'@

    try {
        $raw = @(& wsl.exe -d $TargetDistro --exec sh -lc $probe 2>&1)
        $exitCode = $LASTEXITCODE
    } catch {
        $result.status = 'wsl_command_failed'
        return [pscustomobject]$result
    }
    if ($exitCode -ne 0) {
        $result.status = "wsl_command_failed_exit_$exitCode"
        return [pscustomobject]$result
    }

    $facts = @{}
    foreach ($line in $raw) {
        $parts = [string]$line -split '=', 2
        if ($parts.Count -eq 2 -and $parts[1] -in @('true', 'false')) {
            $facts[$parts[0]] = ($parts[1] -eq 'true')
        }
    }
    if (-not $facts.ContainsKey('config_exists')) {
        $result.status = 'wsl_probe_invalid_response'
        return [pscustomobject]$result
    }

    $result.wsl_reachable = $true
    $result.status = 'reachable'
    foreach ($name in @(
        'hermes_binary_present', 'config_exists', 'config_readable',
        'modelrelay_reference', 'managed_block_present',
        'mentions_primary_model', 'mentions_fallback_model'
    )) {
        if ($facts.ContainsKey($name)) { $result[$name] = [bool]$facts[$name] }
    }
    return [pscustomobject]$result
}

function Get-ModelIdsFromPayload {
    param($Payload)

    $collection = @()
    foreach ($name in @('data', 'models')) {
        $candidate = Get-PropertyValue -Object $Payload -Name $name
        if ($null -ne $candidate) {
            $collection = @($candidate)
            break
        }
    }
    $ids = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $collection) {
        if ($entry -is [string]) {
            $ids.Add($entry)
            continue
        }
        foreach ($name in @('id', 'modelId', 'model_id', 'cli_route_id')) {
            $value = Get-PropertyValue -Object $entry -Name $name
            if ($value -is [string] -and -not [string]::IsNullOrWhiteSpace($value)) {
                $ids.Add($value)
            }
        }
        $routing = Get-PropertyValue -Object $entry -Name 'routing'
        $routeId = Get-PropertyValue -Object $routing -Name 'cli_route_id'
        if ($routeId -is [string] -and -not [string]::IsNullOrWhiteSpace($routeId)) {
            $ids.Add($routeId)
        }
    }
    return @($ids | ForEach-Object { $_.ToLowerInvariant() } | Sort-Object -Unique)
}

function Get-ReadOnlyEndpointProbe {
    param(
        [string]$Name,
        [string]$Url,
        [switch]$InspectModelIds
    )

    $result = [ordered]@{
        name = $Name
        endpoint = $Url
        method = 'GET'
        credential_policy = 'no_authorization_header'
        reachable = $false
        status_code = $null
        json = $false
        access = 'unreachable'
        model_identifier_count = $null
        required_models = $null
        error_kind = $null
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Get -TimeoutSec $TimeoutSec `
            -Headers @{ Accept = 'application/json' } -ErrorAction Stop
        $result.reachable = $true
        $result.status_code = [int]$response.StatusCode
        $result.access = if ($response.StatusCode -eq 200) { 'anonymous_readable' } else { 'http_response' }
        try {
            $payload = $response.Content | ConvertFrom-Json -ErrorAction Stop
            $result.json = $true
            if ($InspectModelIds) {
                $ids = Get-ModelIdsFromPayload -Payload $payload
                # An offer can expose an ID, provider ID, and CLI route ID.
                # Report identifiers rather than incorrectly calling this a
                # count of distinct models or healthy routes.
                $result.model_identifier_count = $ids.Count
                $presence = [ordered]@{}
                foreach ($model in $requiredModels) {
                    $presence[$model] = $ids -contains $model
                }
                $result.required_models = $presence
            }
        } catch {
            $result.error_kind = 'invalid_json'
        }
    } catch {
        $response = $_.Exception.Response
        if ($null -ne $response) {
            $result.reachable = $true
            $result.status_code = [int]$response.StatusCode
            $result.access = switch ([int]$response.StatusCode) {
                401 { 'auth_protected_without_bearer' }
                403 { 'forbidden_without_bearer' }
                default { 'http_error' }
            }
        } else {
            $result.error_kind = $_.Exception.GetType().Name
        }
    }
    return [pscustomobject]$result
}

$relay = Assert-CanonicalLoopbackBaseUrl -Value $RelayBaseUrl -ExpectedPort 7350 -Label 'RelayBaseUrl'
$arena = Assert-CanonicalLoopbackBaseUrl -Value $ArenaBaseUrl -ExpectedPort 7356 -Label 'ArenaBaseUrl'

if ($WhatIfPreference) {
    [ordered]@{
        status = 'would_run_read_only_diagnosis'
        writes = @()
        process_actions = @()
        credential_actions = @()
        wsl_target = [ordered]@{ distro = $Distro; config = '~/.hermes/config.yaml' }
        endpoints = @(
            "$relay/v1/models", "$relay/api/models", "$relay/api/health-sampler",
            "$arena/api/model-cards", "$arena/api/client-manifest", "$arena/api/frontier-intelligence"
        )
    } | ConvertTo-Json -Depth 6
    return
}

$userProfile = [Environment]::GetFolderPath('UserProfile')
$localAppData = [Environment]::GetFolderPath('LocalApplicationData')
$windowsConfigs = @(
    Get-HermesConfigFootprint -Instance 'windows' -Role 'diagnostic_only_never_authoritative_for_wsl_shell' `
        -DisplayPath '~/.hermes/config.yaml' -Path ([System.IO.FileInfo](Join-Path $userProfile '.hermes\config.yaml'))
    Get-HermesConfigFootprint -Instance 'windows' -Role 'diagnostic_only_never_authoritative_for_wsl_shell' `
        -DisplayPath '%LOCALAPPDATA%/hermes/config.yaml' -Path ([System.IO.FileInfo](Join-Path $localAppData 'hermes\config.yaml'))
)
$wsl = Get-WslHermesFootprint -TargetDistro $Distro

$probes = @(
    Get-ReadOnlyEndpointProbe -Name 'modelrelay_v1_catalog' -Url "$relay/v1/models" -InspectModelIds
    Get-ReadOnlyEndpointProbe -Name 'modelrelay_health_projection' -Url "$relay/api/models" -InspectModelIds
    Get-ReadOnlyEndpointProbe -Name 'modelrelay_sampler_budget' -Url "$relay/api/health-sampler"
    Get-ReadOnlyEndpointProbe -Name 'arena_model_cards' -Url "$arena/api/model-cards" -InspectModelIds
    Get-ReadOnlyEndpointProbe -Name 'arena_client_manifest' -Url "$arena/api/client-manifest" -InspectModelIds
    Get-ReadOnlyEndpointProbe -Name 'arena_frontier_intelligence' -Url "$arena/api/frontier-intelligence"
)

$report = [ordered]@{
    schema_version = 1
    generated_at = [DateTime]::UtcNow.ToString('o')
    operation = 'read_only_hermes_modelrelay_diagnosis'
    guarantees = @(
        'no file writes', 'no process start_or_stop', 'no credential lookup_or_transfer',
        'no chat_completion_or_provider_canary'
    )
    interpretation = [ordered]@{
        wsl_hermes_is_authoritative = 'A Hermes prompt in a Linux shell is governed by the WSL config, not either Windows candidate.'
        windows_config = 'Windows config rows are evidence only; this tool never calls them the active WSL configuration.'
        health_scope = 'Catalog and projection reachability only; a successful response does not prove a provider inference route is healthy.'
    }
    windows_config_candidates = $windowsConfigs
    wsl_hermes = $wsl
    endpoint_probes = $probes
}

if (-not $wsl.wsl_reachable) {
    # Deliberately emit this only for a WSL-access failure.  It is an operator
    # handoff, not an action performed by this diagnostic script.
    $report['operator_remediation'] = [ordered]@{
        condition = 'The active WSL Hermes configuration could not be inspected from this Windows session.'
        steps = @(
            'In a normal host PowerShell session (outside a restricted automation sandbox), run the same diagnostic script again.',
            'If WSL is reachable and the active config needs repair, first run: python -m nexusctl.model_sync --dry-run --only hermes-wsl',
            'Only after reviewing that dry-run and intentionally authorizing a configuration change, run: python -m nexusctl.model_sync --only hermes-wsl --provision-hermes-key',
            'Relaunch Hermes from the same WSL distro and send one small non-tool prompt. Do not use a static Windows-to-WSL gateway IP.'
        )
        safety_note = 'The final command is intentionally not executed by this diagnostic; it may update WSL Hermes configuration and its private environment file.'
    }
}

$report | ConvertTo-Json -Depth 10
