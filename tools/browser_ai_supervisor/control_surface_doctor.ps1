param(
    # 9224 is the canonical NEXUS multi-lane Chrome CDP port (gateway / grok lane).
    # Older defaults (9222/9223/9333) remain as probes for legacy profiles.
    [int[]]$CdpPorts = @(9224, 9222, 9223, 9333),
    [string]$RequiredUrlPattern = "",
    [switch]$Json,
    # When set, auto-close duplicate page targets for RequiredUrlPattern via dedupe_lane_tabs_cdp.mjs
    [switch]$AutoDedupe
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

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
            [pscustomobject]@{ port = $Port; type = $_.type; title = $_.title; url = $_.url; id = $_.id }
        }
    } catch { @() }
}

function Get-BrowserProcesses {
    foreach ($name in @("chrome.exe", "firefox.exe", "msedge.exe")) {
        Get-CimInstance Win32_Process -Filter "name = '$name'" -ErrorAction SilentlyContinue |
            Select-Object @{Name="name";Expression={$_.Name}}, ProcessId, CommandLine
    }
}

function Get-NormPath {
    param([string]$Url)
    if (-not $Url) { return "" }
    try {
        $u = [Uri]$Url
        return ($u.GetLeftPart([System.UriPartial]::Path)).ToLowerInvariant()
    } catch {
        return ($Url -split "\?")[0].ToLowerInvariant()
    }
}

$cdp = @(foreach ($port in $CdpPorts) { Test-CdpPort -Port $port })
$targets = @(foreach ($port in $CdpPorts) { Get-CdpTargets -Port $port })
$browsers = @(Get-BrowserProcesses)
$hasCdp = [bool]($cdp | Where-Object { $_.ok })

# Only PAGE targets count for lane matching (not iframes / service workers / workers).
$pageTargets = @($targets | Where-Object { $_.type -eq "page" })
$matchingPageTargets = if ($RequiredUrlPattern) {
    @($pageTargets | Where-Object {
        ($_.url -and ($_.url -match $RequiredUrlPattern)) -or
        ($_.title -and ($_.title -match $RequiredUrlPattern))
    })
} else { @() }

# Duplicate = more than one page with same normalized origin+path for the required pattern
$dupeGroups = @{}
foreach ($t in $matchingPageTargets) {
    $k = Get-NormPath $t.url
    if (-not $k) { $k = "title:" + [string]$t.title }
    if (-not $dupeGroups.ContainsKey($k)) { $dupeGroups[$k] = New-Object System.Collections.ArrayList }
    [void]$dupeGroups[$k].Add($t)
}
$duplicateKeys = @($dupeGroups.Keys | Where-Object { $dupeGroups[$_].Count -gt 1 })
$duplicateRequiredTargets = [bool]($duplicateKeys.Count -gt 0)

$autoDedupeResult = $null
if ($AutoDedupe -and $RequiredUrlPattern -and $duplicateRequiredTargets) {
    $dedupeJs = Join-Path $PSScriptRoot "dedupe_lane_tabs_cdp.mjs"
    $primaryPort = @($cdp | Where-Object { $_.ok } | Select-Object -First 1).port
    if (-not $primaryPort) { $primaryPort = 9224 }
    if (Test-Path $dedupeJs) {
        try {
            $raw = & node $dedupeJs --port $primaryPort --match $RequiredUrlPattern 2>&1 | Out-String
            $autoDedupeResult = $raw.Trim()
            # refresh targets after dedupe
            $targets = @(foreach ($port in $CdpPorts) { Get-CdpTargets -Port $port })
            $pageTargets = @($targets | Where-Object { $_.type -eq "page" })
            $matchingPageTargets = if ($RequiredUrlPattern) {
                @($pageTargets | Where-Object {
                    ($_.url -and ($_.url -match $RequiredUrlPattern)) -or
                    ($_.title -and ($_.title -match $RequiredUrlPattern))
                })
            } else { @() }
            $dupeGroups = @{}
            foreach ($t in $matchingPageTargets) {
                $k = Get-NormPath $t.url
                if (-not $k) { $k = "title:" + [string]$t.title }
                if (-not $dupeGroups.ContainsKey($k)) { $dupeGroups[$k] = New-Object System.Collections.ArrayList }
                [void]$dupeGroups[$k].Add($t)
            }
            $duplicateKeys = @($dupeGroups.Keys | Where-Object { $dupeGroups[$_].Count -gt 1 })
            $duplicateRequiredTargets = [bool]($duplicateKeys.Count -gt 0)
        } catch {
            $autoDedupeResult = "AUTO_DEDUPE_FAILED: $_"
        }
    }
}

$hasRequiredTarget = if ($RequiredUrlPattern) { [bool]($matchingPageTargets | Select-Object -First 1) } else { $hasCdp }
$hasBrowser = [bool]($browsers | Select-Object -First 1)

$status = if ($duplicateRequiredTargets) { "NOTIFY_SETUP_REQUIRED" } elseif ($hasCdp -and $hasRequiredTarget) { "OK_CDP" } else { "NOTIFY_SETUP_REQUIRED" }
$blocker = if ($duplicateRequiredTargets) {
    "Multiple page targets match '$RequiredUrlPattern' on ports $($CdpPorts -join ', '). Close duplicates (or re-run with -AutoDedupe)."
} elseif ($hasCdp -and $hasRequiredTarget) {
    $null
} elseif ($hasCdp -and $RequiredUrlPattern) {
    "CDP exists, but no page target matching '$RequiredUrlPattern' is exposed on ports $($CdpPorts -join ', '). Do not use this endpoint for authenticated-source automation until the target page is visible."
} elseif ($hasBrowser) {
    "Real browser process exists, but no approved Chrome/Firefox CDP endpoint was found on ports $($CdpPorts -join ', '). Use desktop interaction tooling or launch a dedicated authenticated browser profile with remote debugging."
} else {
    "No real Chrome/Firefox/Edge process was visible to this session. Open an authenticated browser tab or launch a dedicated authenticated CDP profile."
}

$safeMatchingTargets = @($matchingPageTargets | ForEach-Object {
    [pscustomobject]@{ port = $_.port; type = $_.type; title = $_.title; url = (Redact-Url $_.url) }
})
$safeTargetSample = @($pageTargets | Select-Object -First 15 | ForEach-Object {
    [pscustomobject]@{ port = $_.port; type = $_.type; title = $_.title; url = (Redact-Url $_.url) }
})

$result = [pscustomobject]@{
    status = $status
    blocker = $blocker
    cdp = $cdp
    requiredUrlPattern = $RequiredUrlPattern
    matchingTargets = $safeMatchingTargets
    matching_page_count = @($matchingPageTargets).Count
    target_count = @($pageTargets).Count
    duplicate_required_targets = $duplicateRequiredTargets
    duplicate_keys = $duplicateKeys
    auto_dedupe = $autoDedupeResult
    target_sample = $safeTargetSample
    browser_process_count = $browsers.Count
    browser_processes = @($browsers | ForEach-Object {
        [pscustomobject]@{
            name = $_.name
            processId = $_.ProcessId
            hasRemoteDebugging = ($_.CommandLine -match "--remote-debugging-port")
        }
    })
    supervisor_rule = "Do not use Playwright or fresh in-app browsers for authenticated AI sources."
}

if ($Json) { $result | ConvertTo-Json -Depth 8 } else { $result | Format-List }
