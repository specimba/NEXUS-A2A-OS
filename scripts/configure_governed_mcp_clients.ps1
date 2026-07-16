# Register the governed NEXUS MCP/A2A facade with agent CLIs that do not expose
# a generic OpenAI-compatible LLM-provider setting.  This deliberately wires
# tools to 7354/SSE; it never redirects Grok or Devin OAuth/model traffic to
# ModelRelay 7350 and never transfers credentials.
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [ValidateSet('all', 'grok', 'devin')]
    [string]$Client = 'all',
    [ValidateSet('local', 'project', 'user')]
    [string]$DevinScope = 'local',
    [string]$BridgeUrl = 'http://127.0.0.1:7354/sse',
    [string]$BridgeHealthUrl = 'http://127.0.0.1:7354/health',
    [string]$ServerName = 'nexus-governed-bridge',
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = 'Stop'

function Get-CommandPath([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { return $null }
    return $command.Source
}

function Test-GovernedBridge {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ge 400) { return $false }
        $payload = $response.Content | ConvertFrom-Json -ErrorAction Stop
        return $payload.version -eq '2.4.0-p0-continuity' -and @($payload.tools).Count -eq 25
    } catch {
        return $false
    }
}

if ($BridgeUrl -notmatch '^http://127\.0\.0\.1:7354/sse$') {
    throw 'Only the canonical local governed SSE facade is allowed: http://127.0.0.1:7354/sse'
}
if (-not $SkipHealthCheck -and -not (Test-GovernedBridge -Url $BridgeHealthUrl)) {
    throw 'Governed MCP bridge health contract failed; do not register a stale or unknown tool surface.'
}

$results = @()
if ($Client -in @('all', 'grok')) {
    $grok = Get-CommandPath 'grok'
    if (-not $grok) {
        $results += [ordered]@{ client = 'grok'; status = 'missing_cli' }
    } elseif ($PSCmdlet.ShouldProcess('Grok CLI MCP configuration', "add/update $ServerName -> $BridgeUrl (sse)")) {
        & $grok mcp add $ServerName --url $BridgeUrl --type sse
        if ($LASTEXITCODE -ne 0) { throw "grok mcp add failed with exit code $LASTEXITCODE" }
        $results += [ordered]@{ client = 'grok'; status = 'configured'; transport = 'sse'; endpoint = $BridgeUrl }
    } else {
        $results += [ordered]@{ client = 'grok'; status = 'would_configure'; transport = 'sse'; endpoint = $BridgeUrl }
    }
}

if ($Client -in @('all', 'devin')) {
    $devin = Get-CommandPath 'devin'
    if (-not $devin) {
        $results += [ordered]@{ client = 'devin'; status = 'missing_cli' }
    } elseif ($PSCmdlet.ShouldProcess('Devin CLI MCP configuration', "add $ServerName -> $BridgeUrl (sse, $DevinScope scope)")) {
        & $devin mcp add --transport sse --scope $DevinScope $ServerName --url $BridgeUrl
        if ($LASTEXITCODE -ne 0) { throw "devin mcp add failed with exit code $LASTEXITCODE" }
        $results += [ordered]@{ client = 'devin'; status = 'configured'; scope = $DevinScope; transport = 'sse'; endpoint = $BridgeUrl }
    } else {
        $results += [ordered]@{ client = 'devin'; status = 'would_configure'; scope = $DevinScope; transport = 'sse'; endpoint = $BridgeUrl }
    }
}

[ordered]@{
    bridge = [ordered]@{
        endpoint = $BridgeUrl
        health_checked = -not $SkipHealthCheck
        policy = 'MCP/A2A tools only; ModelRelay 7350 remains a separate OpenAI-compatible inference boundary'
    }
    results = $results
} | ConvertTo-Json -Depth 5
