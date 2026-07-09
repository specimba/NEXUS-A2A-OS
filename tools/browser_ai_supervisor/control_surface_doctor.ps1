param(
    # 9224 is the canonical NEXUS multi-lane Chrome CDP port (gateway / grok lane).
    # Older defaults (9222/9223/9333) remain as probes for legacy profiles.
    [int[]]$CdpPorts = @(9224, 9222, 9223, 9333),
    [string]$RequiredUrlPattern = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Redact-Url {
    param([string]$Url)
    if (-not $Url) { return $Url }
    try {
        $u = [Uri]$Url
        $base = $u.GetLeftPart([System.UriPartial]::Path)
        if ($u.Query) { return "$base?REDACTED" }
        return $base
    } catch {
        return ($Url -replace "\?.*$", "?REDACTED")
    }
}

function Test-CdpPort {
    param([int]$Port)
    $uri = "http://127.0.0.1:$Port/json/version"
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $uri -TimeoutSec 2
        $payload = $response.Content | ConvertFrom-Json
        [pscustomobject]@{ port = $Port; ok = $true; browser = $payload.Browser; webSocketDebuggerUrl = $payload.webSocketDebuggerUrl }
    } catch {
        [pscustomobject]@{ port = $Port; ok = $false; browser = $null; webSocketDebuggerUrl = $null }
    }
}

function Get-CdpTargets {
    param([int]$Port)
    $uri = "http://127.0.0.1:$Port/json/list"
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $uri -TimeoutSec 2
        @($response.Content | ConvertFrom-Json) | ForEach-Object {
            [pscustomobject]@{ port = $Port; type = $_.type; title = $_.title; url = $_.url }
        }
    } catch { @() }
}

function Get-BrowserProcesses {
    foreach ($name in @("chrome.exe", "firefox.exe", "msedge.exe")) {
        Get-CimInstance Win32_Process -Filter "name = '$name'" -ErrorAction SilentlyContinue |
            Select-Object @{Name="name";Expression={$_.Name}}, ProcessId, CommandLine
    }
}

$cdp = @(foreach ($port in $CdpPorts) { Test-CdpPort -Port $port })
$targets = @(foreach ($port in $CdpPorts) { Get-CdpTargets -Port $port })
$browsers = @(Get-BrowserProcesses)
$hasCdp = [bool]($cdp | Where-Object { $_.ok })
$matchingTargets = if ($RequiredUrlPattern) { @($targets | Where-Object { $_.url -match $RequiredUrlPattern -or $_.title -match $RequiredUrlPattern }) } else { @() }
$duplicateRequiredTargets = if ($RequiredUrlPattern) { @($matchingTargets).Count -gt 1 } else { $false }
$hasRequiredTarget = if ($RequiredUrlPattern) { [bool]($matchingTargets | Select-Object -First 1) } else { $hasCdp }
$hasBrowser = [bool]($browsers | Select-Object -First 1)

$status = if ($duplicateRequiredTargets) { "NOTIFY_SETUP_REQUIRED" } elseif ($hasCdp -and $hasRequiredTarget) { "OK_CDP" } else { "NOTIFY_SETUP_REQUIRED" }
$blocker = if ($duplicateRequiredTargets) {
    "Multiple targets match '$RequiredUrlPattern' on ports $($CdpPorts -join ', '). Close duplicate tabs before autonomous control."
} elseif ($hasCdp -and $hasRequiredTarget) {
    $null
} elseif ($hasCdp -and $RequiredUrlPattern) {
    "CDP exists, but no target matching '$RequiredUrlPattern' is exposed on ports $($CdpPorts -join ', '). Do not use this endpoint for authenticated-source automation until the target page is visible."
} elseif ($hasBrowser) {
    "Real browser process exists, but no approved Chrome/Firefox CDP endpoint was found on ports $($CdpPorts -join ', '). Use desktop interaction tooling or launch a dedicated authenticated browser profile with remote debugging."
} else {
    "No real Chrome/Firefox/Edge process was visible to this session. Open an authenticated browser tab or launch a dedicated authenticated CDP profile."
}

$safeMatchingTargets = @($matchingTargets | ForEach-Object { [pscustomobject]@{ port = $_.port; type = $_.type; title = $_.title; url = (Redact-Url $_.url) } })
$safeTargetSample = @($targets | Where-Object { $_.type -eq "page" } | Select-Object -First 10 | ForEach-Object { [pscustomobject]@{ port = $_.port; type = $_.type; title = $_.title; url = (Redact-Url $_.url) } })

$result = [pscustomobject]@{
    status = $status
    blocker = $blocker
    cdp = $cdp
    requiredUrlPattern = $RequiredUrlPattern
    matchingTargets = $safeMatchingTargets
    target_count = @($targets).Count
    duplicate_required_targets = $duplicateRequiredTargets
    target_sample = $safeTargetSample
    browser_process_count = $browsers.Count
    browser_processes = @($browsers | ForEach-Object { [pscustomobject]@{ name = $_.name; processId = $_.ProcessId; hasRemoteDebugging = ($_.CommandLine -match "--remote-debugging-port") } })
    supervisor_rule = "Do not use Playwright or fresh in-app browsers for authenticated AI sources."
}

if ($Json) { $result | ConvertTo-Json -Depth 8 } else { $result | Format-List }


