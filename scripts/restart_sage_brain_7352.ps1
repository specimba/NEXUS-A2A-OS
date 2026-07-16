#Requires -Version 7.4

<#
.SYNOPSIS
Controlled reload helper for the canonical loopback-only NEXUS SAGE Brain.

.DESCRIPTION
This helper is intentionally narrower than a generic service restart. It can
only operate on the Brain listener at 127.0.0.1:7352, requires an operator
key file outside the repository, verifies the current Brain and SAGE health
contracts plus the listener process identity before stopping anything, then
reuses start_sage_brain.ps1 for the actual launch. It never prints key data.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SageKeyFile,

    [ValidateSet("observe_only", "proposal_write")]
    [string]$Mode = "observe_only",

    [switch]$EnableProposalWrite,

    [ValidateRange(5, 60)]
    [int]$StartupTimeoutSeconds = 30,

    [ValidateRange(1, 30)]
    [int]$HealthRetries = 12,

    [ValidateRange(100, 5000)]
    [int]$HealthDelayMs = 500
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$requestedWhatIf = [bool]$WhatIfPreference

# `Get-NetTCPConnection` may auto-load NetTCPIP, whose module initialization
# creates aliases. With PowerShell's global WhatIf preference still set, that
# read-only import is itself skipped and preflight fails. Capture the caller's
# dry-run request, clear only the ambient preference for read-only discovery,
# and gate every mutation below on the captured value before Stop-Process or
# the launcher can be reached.
if ($requestedWhatIf) {
    $WhatIfPreference = $false
}

$port = 7352
$bindAddress = "127.0.0.1"
$sageKey = $null
$sageHeaders = $null

function Resolve-OperatorSageKeyFile {
    param(
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $repoFullPath = [System.IO.Path]::GetFullPath($RepoRoot)
    $repoPrefix = $repoFullPath.TrimEnd(
        [char[]]@(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
    ) + [System.IO.Path]::DirectorySeparatorChar

    try {
        $resolved = Resolve-Path -LiteralPath $InputPath -ErrorAction Stop
        $item = Get-Item -LiteralPath $resolved.Path -Force -ErrorAction Stop
        if ($item.PSIsContainer) {
            throw "not-a-file"
        }
        $entryPath = [System.IO.Path]::GetFullPath($item.FullName)
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            $target = $item.ResolveLinkTarget($true)
            if ($null -eq $target) {
                throw "unresolved-link"
            }
            $keyPath = [System.IO.Path]::GetFullPath($target.FullName)
        }
        else {
            $keyPath = [System.IO.Path]::GetFullPath($item.FullName)
        }
    }
    catch {
        throw "SAGE_KEY_FILE_UNAVAILABLE"
    }

    if ($entryPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO"
    }
    if (
        $keyPath.Equals($repoFullPath, [System.StringComparison]::OrdinalIgnoreCase) -or
        $keyPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO"
    }
    return $keyPath
}

function Read-ValidatedSageKey {
    param([Parameter(Mandatory = $true)][string]$KeyPath)

    try {
        $key = [System.IO.File]::ReadAllText(
            $KeyPath,
            [System.Text.Encoding]::UTF8
        ).Trim()
    }
    catch {
        throw "SAGE_KEY_FILE_UNREADABLE"
    }
    if ($key.Length -lt 32 -or $key -match "\s") {
        $key = $null
        throw "SAGE_KEY_FILE_INVALID"
    }
    return $key
}

function Get-SageBrainListener {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        $listeners = @(
            Get-NetTCPConnection -State Listen -ErrorAction Stop |
                Where-Object { $_.LocalPort -eq $Port }
        )
    }
    catch {
        throw "SAGE_BRAIN_PORT_PREFLIGHT_FAILED"
    }
    if ($listeners.Count -gt 1) {
        throw "SAGE_BRAIN_AMBIGUOUS_LISTENER_DETECTED"
    }
    if ($listeners.Count -eq 0) {
        return $null
    }
    if ($listeners[0].LocalAddress -cne "127.0.0.1") {
        throw "SAGE_BRAIN_NON_LOOPBACK_LISTENER_DETECTED"
    }
    return [pscustomobject]@{
        ProcessId = [int]$listeners[0].OwningProcess
        LocalAddress = [string]$listeners[0].LocalAddress
    }
}

function Get-SageBrainProcessRecord {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    try {
        $records = @(
            Get-CimInstance `
                -ClassName Win32_Process `
                -Filter "ProcessId = $ProcessId" `
                -Property ProcessId, ParentProcessId, CreationDate, CommandLine, ExecutablePath `
                -ErrorAction Stop
        )
    }
    catch {
        throw "SAGE_BRAIN_PROCESS_IDENTITY_UNAVAILABLE"
    }
    if ($records.Count -ne 1) {
        throw "SAGE_BRAIN_PROCESS_IDENTITY_UNAVAILABLE"
    }
    return $records[0]
}

function Get-SageBrainProcessIdentity {
    param([Parameter(Mandatory = $true)][object]$ProcessRecord)

    return "{0}:{1}" -f (
        [int]$ProcessRecord.ProcessId,
        ([DateTime]$ProcessRecord.CreationDate).ToUniversalTime().Ticks
    )
}

function Test-SageBrainProcessRecord {
    param(
        [Parameter(Mandatory = $true)][object]$ProcessRecord,
        [Parameter(Mandatory = $true)][int]$ExpectedProcessId,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    if ([int]$ProcessRecord.ProcessId -ne $ExpectedProcessId) {
        return $false
    }
    $commandLine = [string]$ProcessRecord.CommandLine
    $executablePath = [string]$ProcessRecord.ExecutablePath
    if ([string]::IsNullOrWhiteSpace($commandLine) -or [string]::IsNullOrWhiteSpace($executablePath)) {
        return $false
    }
    try {
        $expectedPython = [System.IO.Path]::GetFullPath(
            (Join-Path $RepoRoot ".venv\Scripts\python.exe")
        )
        $actualPython = [System.IO.Path]::GetFullPath($executablePath)
    }
    catch {
        return $false
    }
    return (
        $actualPython.Equals($expectedPython, [System.StringComparison]::OrdinalIgnoreCase) -and
        $commandLine -match "(?i)(?:^|\s)nexus_os\.api\.brain_api(?:\s|$)"
    )
}

function Test-SageBrainPublicHealth {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        $payload = Invoke-RestMethod `
            -Method Get `
            -Uri "http://127.0.0.1:$Port/" `
            -TimeoutSec 3 `
            -ErrorAction Stop
        return $payload.service -eq "NEXUS Brain API"
    }
    catch {
        return $false
    }
}

function Test-SageAuthenticatedHealth {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$ExpectedMode = ""
    )

    try {
        $headers = @{
            Authorization = "Bearer $Key"
            Accept = "application/json"
        }
        $payload = Invoke-RestMethod `
            -Method Get `
            -Uri "http://127.0.0.1:$Port/api/sage/v1/health" `
            -Headers $headers `
            -TimeoutSec 3 `
            -ErrorAction Stop
        $modeMatches = [string]::IsNullOrWhiteSpace($ExpectedMode) -or $payload.mode -eq $ExpectedMode
        return (
            $payload.ok -eq $true -and
            $payload.service -eq "nexus-sage-ingress" -and
            $payload.execution_allowed -eq $false -and
            $modeMatches
        )
    }
    catch {
        return $false
    }
}

function Wait-SageBrainPortReleased {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][int]$PreviousProcessId,
        [Parameter(Mandatory = $true)][int]$Retries,
        [Parameter(Mandatory = $true)][int]$DelayMs
    )

    for ($attempt = 1; $attempt -le $Retries; $attempt += 1) {
        $listener = Get-SageBrainListener -Port $Port
        if ($null -eq $listener) {
            return
        }
        if ($listener.ProcessId -ne $PreviousProcessId) {
            throw "SAGE_BRAIN_PORT_RECLAIMED_BY_UNVERIFIED_PROCESS"
        }
        Start-Sleep -Milliseconds $DelayMs
    }
    throw "SAGE_BRAIN_PORT_NOT_RELEASED"
}

if ($port -ne 7352) {
    throw "SAGE_BRAIN_NONCANONICAL_PORT_REFUSED"
}
if ($Mode -eq "proposal_write" -and -not $EnableProposalWrite) {
    throw "SAGE_PROPOSAL_WRITE_REQUIRES_EXPLICIT_ENABLE"
}
if ($EnableProposalWrite -and $Mode -ne "proposal_write") {
    throw "SAGE_PROPOSAL_WRITE_SWITCH_MODE_MISMATCH"
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$launcher = Join-Path $repoRoot "scripts\start_sage_brain.ps1"
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "SAGE_BRAIN_LAUNCHER_MISSING"
}

try {
    # Do not inherit a potentially stale raw key through this restart shell.
    Remove-Item Env:NEXUS_SAGE_API_KEY -ErrorAction SilentlyContinue
    $keyFilePath = Resolve-OperatorSageKeyFile -InputPath $SageKeyFile -RepoRoot $repoRoot

    $currentListener = Get-SageBrainListener -Port $port
    $currentProcess = $null
    $currentIdentity = $null
    if ($null -ne $currentListener) {
        $currentProcess = Get-SageBrainProcessRecord -ProcessId $currentListener.ProcessId
        if (-not (Test-SageBrainProcessRecord `
            -ProcessRecord $currentProcess `
            -ExpectedProcessId $currentListener.ProcessId `
            -RepoRoot $repoRoot)) {
            throw "SAGE_BRAIN_UNOWNED_LISTENER_DETECTED"
        }
        $currentIdentity = Get-SageBrainProcessIdentity -ProcessRecord $currentProcess
        if (-not (Test-SageBrainPublicHealth -Port $port)) {
            throw "SAGE_BRAIN_OWNERSHIP_CONTRACT_FAILED"
        }
    }

    if ($requestedWhatIf) {
        [ordered]@{
            status = "would_restart"
            port = $port
            previous_listener_pid = if ($null -eq $currentListener) { $null } else { $currentListener.ProcessId }
            source = $launcher
            mode = $Mode
            preflight = if ($null -eq $currentListener) { "no_listener" } else { "brain_identity_and_public_health_verified" }
            key = "operator_file_resolved_not_read_for_whatif"
        } | ConvertTo-Json
        return
    }

    # A dry run intentionally never reads operator secret material. The real
    # action must prove the authenticated SAGE contract before it can stop a
    # verified listener.
    $sageKey = Read-ValidatedSageKey -KeyPath $keyFilePath
    if ($null -ne $currentListener -and -not (Test-SageAuthenticatedHealth -Port $port -Key $sageKey)) {
        throw "SAGE_BRAIN_AUTHENTICATED_HEALTH_FAILED"
    }

    if ($null -ne $currentListener) {
        if (-not $PSCmdlet.ShouldProcess(
            "verified SAGE Brain listener PID $($currentListener.ProcessId) on 7352",
            "stop only the verified canonical Brain listener for source reload"
        )) {
            [ordered]@{ status = "not_restarted"; port = $port; reason = "operator_declined" } | ConvertTo-Json
            return
        }

        $listenerBeforeStop = Get-SageBrainListener -Port $port
        if ($null -eq $listenerBeforeStop -or $listenerBeforeStop.ProcessId -ne $currentListener.ProcessId) {
            throw "SAGE_BRAIN_LISTENER_CHANGED_BEFORE_STOP"
        }
        $processBeforeStop = Get-SageBrainProcessRecord -ProcessId $currentListener.ProcessId
        if (
            (Get-SageBrainProcessIdentity -ProcessRecord $processBeforeStop) -ne $currentIdentity -or
            -not (Test-SageBrainProcessRecord `
                -ProcessRecord $processBeforeStop `
                -ExpectedProcessId $currentListener.ProcessId `
                -RepoRoot $repoRoot)
        ) {
            throw "SAGE_BRAIN_LISTENER_CHANGED_BEFORE_STOP"
        }

        Stop-Process -Id $currentListener.ProcessId -Force -ErrorAction Stop
        Wait-SageBrainPortReleased `
            -Port $port `
            -PreviousProcessId $currentListener.ProcessId `
            -Retries $HealthRetries `
            -DelayMs $HealthDelayMs
    }

    $launchArguments = @{
        SageKeyFile = $keyFilePath
        Mode = $Mode
        StartupTimeoutSeconds = $StartupTimeoutSeconds
        BindAddress = $bindAddress
        Port = $port
    }
    if ($EnableProposalWrite) {
        $launchArguments.EnableProposalWrite = $true
    }
    & $launcher @launchArguments | Out-Null

    for ($attempt = 1; $attempt -le $HealthRetries; $attempt += 1) {
        Start-Sleep -Milliseconds $HealthDelayMs
        $newListener = Get-SageBrainListener -Port $port
        if ($null -eq $newListener) {
            continue
        }
        $newProcess = Get-SageBrainProcessRecord -ProcessId $newListener.ProcessId
        if (-not (Test-SageBrainProcessRecord `
            -ProcessRecord $newProcess `
            -ExpectedProcessId $newListener.ProcessId `
            -RepoRoot $repoRoot)) {
            throw "SAGE_BRAIN_UNOWNED_LISTENER_DETECTED"
        }
        if (
            (Test-SageBrainPublicHealth -Port $port) -and
            (Test-SageAuthenticatedHealth -Port $port -Key $sageKey -ExpectedMode $Mode)
        ) {
            [ordered]@{
                status = "restarted"
                port = $port
                previous_listener_pid = if ($null -eq $currentListener) { $null } else { $currentListener.ProcessId }
                listener_pid = $newListener.ProcessId
                source = $launcher
                mode = $Mode
                public_health = "verified"
                sage_health = "authenticated_verified"
                execution_allowed = $false
            } | ConvertTo-Json
            return
        }
    }
    throw "SAGE_BRAIN_RESTART_READINESS_FAILED"
}
finally {
    $sageHeaders = $null
    $sageKey = $null
}
