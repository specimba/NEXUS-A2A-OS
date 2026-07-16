#Requires -Version 7.4

<#
.SYNOPSIS
Starts the governed NEXUS SAGE Brain ingress on its canonical loopback port.

.DESCRIPTION
This launcher is deliberately local-only. It refuses occupied ports, reads an
operator-managed credential file outside the repository, starts the repository
virtual-environment Python as a hidden process, and reports only bounded status.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SageKeyFile,

    [ValidateSet("observe_only", "proposal_write")]
    [string]$Mode = "observe_only",

    [switch]$EnableProposalWrite,

    [ValidateRange(5, 60)]
    [int]$StartupTimeoutSeconds = 30,

    [string]$BindAddress = "127.0.0.1",

    [int]$Port = 7352
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-SageProcessIdentity {
    param([Parameter(Mandatory = $true)][object]$ProcessRecord)

    return ([DateTime]($ProcessRecord.CreationDate)).ToUniversalTime().Ticks
}

function Get-SageProcessSnapshot {
    return @(
        Get-CimInstance `
            -ClassName Win32_Process `
            -Property ProcessId, ParentProcessId, CreationDate `
            -ErrorAction Stop
    )
}

function Test-SageOwnedProcessRecord {
    param(
        [Parameter(Mandatory = $true)][hashtable]$OwnedProcesses,
        [Parameter(Mandatory = $true)][object]$ProcessRecord
    )

    $candidatePid = [int]$ProcessRecord.ProcessId
    return (
        $OwnedProcesses.ContainsKey($candidatePid) -and
        $OwnedProcesses[$candidatePid] -eq (Get-SageProcessIdentity -ProcessRecord $ProcessRecord)
    )
}

function Update-SageOwnedProcesses {
    param(
        [Parameter(Mandatory = $true)][hashtable]$OwnedProcesses,
        [Parameter(Mandatory = $true)][object[]]$Snapshot
    )

    $byPid = @{}
    foreach ($record in $Snapshot) {
        $recordPid = [int]$record.ProcessId
        if ($recordPid -gt 0) {
            $byPid[$recordPid] = $record
        }
    }

    $validOwnedPids = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($ownedPid in @($OwnedProcesses.Keys)) {
        $candidatePid = [int]$ownedPid
        if (-not $byPid.ContainsKey($candidatePid)) {
            # Preserve a captured parent identity after that process exits so
            # its already-created orphan child can still be attributed.
            $validOwnedPids.Add($candidatePid) | Out-Null
        }
        elseif (
            Test-SageOwnedProcessRecord `
                -OwnedProcesses $OwnedProcesses `
                -ProcessRecord $byPid[$candidatePid]
        ) {
            $validOwnedPids.Add($candidatePid) | Out-Null
        }
    }

    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($record in $Snapshot) {
            $recordPid = [int]$record.ProcessId
            $parentPid = [int]$record.ParentProcessId
            if (
                $recordPid -gt 0 -and
                -not $OwnedProcesses.ContainsKey($recordPid) -and
                $validOwnedPids.Contains($parentPid) -and
                (Get-SageProcessIdentity -ProcessRecord $record) -ge $OwnedProcesses[$parentPid]
            ) {
                $OwnedProcesses[$recordPid] = Get-SageProcessIdentity -ProcessRecord $record
                $validOwnedPids.Add($recordPid) | Out-Null
                $changed = $true
            }
        }
    }
}

function Stop-SageOwnedProcessTree {
    param(
        [System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][hashtable]$OwnedProcesses,
        [int]$VerifiedListenerPid = 0
    )

    # The retained process handle is safer than a PID-only kill and asks .NET
    # to terminate the live supervisor tree in one bounded operation.
    if ($null -ne $Process -and -not $Process.HasExited) {
        try {
            $Process.Kill($true)
            $Process.WaitForExit(5000) | Out-Null
        }
        catch {
            # The identity-checked orphan sweep below remains authoritative.
        }
    }

    # A Windows venv supervisor can exit before its child listener. Sweep only
    # descendants whose PID and creation timestamp were observed in this run.
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        try {
            $snapshot = @(Get-SageProcessSnapshot)
        }
        catch {
            break
        }
        Update-SageOwnedProcesses -OwnedProcesses $OwnedProcesses -Snapshot $snapshot
        $activeOwned = @(
            $snapshot |
                Where-Object {
                    Test-SageOwnedProcessRecord `
                        -OwnedProcesses $OwnedProcesses `
                        -ProcessRecord $_
                } |
                Sort-Object @{
                    Expression = {
                        if ([int]$_.ProcessId -eq $VerifiedListenerPid) { 0 } else { 1 }
                    }
                }
        )
        if ($activeOwned.Count -eq 0) {
            break
        }
        foreach ($record in $activeOwned) {
            $candidatePid = [int]$record.ProcessId
            try {
                $current = @(
                    Get-CimInstance `
                        -ClassName Win32_Process `
                        -Filter "ProcessId = $candidatePid" `
                        -Property ProcessId, ParentProcessId, CreationDate `
                        -ErrorAction Stop
                )
                if (
                    $current.Count -eq 1 -and
                    (Test-SageOwnedProcessRecord `
                        -OwnedProcesses $OwnedProcesses `
                        -ProcessRecord $current[0])
                ) {
                    Stop-Process -Id $candidatePid -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                # Already exited or no longer the same process identity.
            }
        }
        Start-Sleep -Milliseconds 100
    }
}

if ($BindAddress -cne "127.0.0.1") {
    throw "SAGE_BRAIN_NON_LOOPBACK_REFUSED"
}
if ($Port -ne 7352) {
    throw "SAGE_BRAIN_NONCANONICAL_PORT_REFUSED"
}

# A raw inherited credential is never an accepted input to this launcher or
# its child. Only the explicitly selected key file may supply authentication.
Remove-Item Env:NEXUS_SAGE_API_KEY -ErrorAction SilentlyContinue

if ($Mode -eq "proposal_write" -and -not $EnableProposalWrite) {
    throw "SAGE_PROPOSAL_WRITE_REQUIRES_EXPLICIT_ENABLE"
}
if ($EnableProposalWrite -and $Mode -ne "proposal_write") {
    throw "SAGE_PROPOSAL_WRITE_SWITCH_MODE_MISMATCH"
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoFullPath = [System.IO.Path]::GetFullPath($repoRoot)
$repoPrefix = $repoFullPath.TrimEnd(
    [char[]]@(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
) + [System.IO.Path]::DirectorySeparatorChar

try {
    $resolvedKeyPath = Resolve-Path -LiteralPath $SageKeyFile -ErrorAction Stop
    $keyItem = Get-Item -LiteralPath $resolvedKeyPath.Path -Force -ErrorAction Stop
    $keyEntryPath = [System.IO.Path]::GetFullPath($keyItem.FullName)
    if ($keyItem.PSIsContainer) {
        throw "not-a-file"
    }
    if (($keyItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        $linkTarget = $keyItem.ResolveLinkTarget($true)
        if ($null -eq $linkTarget) {
            throw "unresolved-link"
        }
        $keyFilePath = [System.IO.Path]::GetFullPath($linkTarget.FullName)
    }
    else {
        $keyFilePath = [System.IO.Path]::GetFullPath($keyItem.FullName)
    }
}
catch {
    throw "SAGE_KEY_FILE_UNAVAILABLE"
}

if ($keyEntryPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO"
}

if (
    $keyFilePath.Equals($repoFullPath, [System.StringComparison]::OrdinalIgnoreCase) -or
    $keyFilePath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)
) {
    throw "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO"
}

try {
    $sageKey = [System.IO.File]::ReadAllText(
        $keyFilePath,
        [System.Text.Encoding]::UTF8
    ).Trim()
}
catch {
    throw "SAGE_KEY_FILE_UNREADABLE"
}
if ($sageKey.Length -lt 32 -or $sageKey -match "\s") {
    $sageKey = $null
    throw "SAGE_KEY_FILE_INVALID"
}

try {
    $listeners = @(
        Get-NetTCPConnection -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalPort -eq $Port }
    )
}
catch {
    $sageKey = $null
    throw "SAGE_BRAIN_PORT_PREFLIGHT_FAILED"
}
if ($listeners.Count -gt 0) {
    $ownerPids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ","
    $sageKey = $null
    throw "SAGE_BRAIN_PORT_IN_USE port=7352 owner_pid=$ownerPids"
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $sageKey = $null
    throw "SAGE_BRAIN_VENV_PYTHON_MISSING"
}

$localAppData = [System.Environment]::GetFolderPath(
    [System.Environment+SpecialFolder]::LocalApplicationData
)
if ([string]::IsNullOrWhiteSpace($localAppData)) {
    $localAppData = Join-Path $HOME ".nexus_pi"
}
$runtimeRoot = Join-Path $localAppData "NEXUS\sage_brain"
$stateRoot = Join-Path $runtimeRoot "state"
$logRoot = Join-Path $runtimeRoot "logs"

$separator = [string][System.IO.Path]::DirectorySeparatorChar
$stateFullPath = [System.IO.Path]::GetFullPath($stateRoot).TrimEnd(
    [char[]]@(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
)
$keyDirectory = [System.IO.Path]::GetFullPath(
    [System.IO.Path]::GetDirectoryName($keyFilePath)
).TrimEnd(
    [char[]]@(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
)
$statePrefix = $stateFullPath + $separator
$keyDirectoryPrefix = $keyDirectory + $separator
if (
    $stateFullPath.Equals($keyDirectory, [System.StringComparison]::OrdinalIgnoreCase) -or
    $statePrefix.StartsWith($keyDirectoryPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    $keyDirectoryPrefix.StartsWith($statePrefix, [System.StringComparison]::OrdinalIgnoreCase)
) {
    $sageKey = $null
    throw "SAGE_RUNTIME_MUST_NOT_SHARE_KEY_DIRECTORY"
}
try {
    New-Item -ItemType Directory -Path $stateRoot -Force -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $logRoot -Force -ErrorAction Stop | Out-Null
}
catch {
    $sageKey = $null
    throw "SAGE_BRAIN_RUNTIME_DIR_UNAVAILABLE"
}

$stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$stdoutLog = Join-Path $logRoot "brain-$stamp.out.log"
$stderrLog = Join-Path $logRoot "brain-$stamp.err.log"

# Explicitly remove the raw key from the child and pass only the file path.
$childEnvironment = @{
    "NEXUS_SAGE_API_KEY" = $null
    "NEXUS_SAGE_API_KEY_FILE" = $keyFilePath
    "NEXUS_SAGE_GATEWAY_MODE" = $Mode
    "NEXUS_SAGE_RUNTIME_DIR" = $stateRoot
    "PYTHONUNBUFFERED" = "1"
}
$argumentList = @("-m", "nexus_os.api.brain_api", "--host", $BindAddress, "--port", [string]$Port)

$process = $null
$ownedProcesses = @{}
$verifiedListenerPid = 0
$safeFailure = "SAGE_BRAIN_START_FAILED"
try {
    $process = Start-Process `
        -FilePath $python `
        -ArgumentList $argumentList `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -Environment $childEnvironment `
        -PassThru `
        -ErrorAction Stop

    try {
        $supervisor = @(
            Get-CimInstance `
                -ClassName Win32_Process `
                -Filter "ProcessId = $($process.Id)" `
                -Property ProcessId, ParentProcessId, CreationDate `
                -ErrorAction Stop
        )
        if ($supervisor.Count -ne 1) {
            throw "supervisor-identity-unavailable"
        }
        $ownedProcesses[[int]$process.Id] = Get-SageProcessIdentity -ProcessRecord $supervisor[0]
    }
    catch {
        $safeFailure = "SAGE_BRAIN_SUPERVISOR_IDENTITY_FAILED"
        throw $safeFailure
    }

    $brainReady = $false
    $sageReady = $false
    $listenerConfirmed = $false
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $listeners = @()
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $processSnapshot = @(Get-SageProcessSnapshot)
            Update-SageOwnedProcesses `
                -OwnedProcesses $ownedProcesses `
                -Snapshot $processSnapshot
            $listeners = @(
                Get-NetTCPConnection -State Listen -ErrorAction Stop |
                    Where-Object { $_.LocalPort -eq $Port }
            )
        }
        catch {
            $processSnapshot = @()
            $listeners = @()
        }
        # Require exactly one loopback listener whose process identity was
        # observed as the supervisor or one of its descendants in this run.
        # Brain identity and fresh-key authentication remain separate gates.

        if ($listeners.Count -gt 1) {
            $safeFailure = "SAGE_BRAIN_AMBIGUOUS_LISTENER_DETECTED"
            break
        }
        if ($listeners.Count -eq 1) {
            $wrongBind = @(
                $listeners | Where-Object { $_.LocalAddress -cne $BindAddress }
            )
            if ($wrongBind.Count -gt 0) {
                $safeFailure = "SAGE_BRAIN_NON_LOOPBACK_LISTENER_DETECTED"
                break
            }
        }

        if ($listeners.Count -eq 0) {
            if ($process.HasExited -and $ownedProcesses.Count -eq 1) {
                $safeFailure = "SAGE_BRAIN_PROCESS_EXITED_EARLY"
                break
            }
            Start-Sleep -Milliseconds 500
            continue
        }

        $candidateListenerPid = [int]$listeners[0].OwningProcess
        $candidateListener = @(
            $processSnapshot |
                Where-Object { [int]$_.ProcessId -eq $candidateListenerPid }
        )
        if (
            $candidateListener.Count -ne 1 -or
            -not (Test-SageOwnedProcessRecord `
                -OwnedProcesses $ownedProcesses `
                -ProcessRecord $candidateListener[0])
        ) {
            $safeFailure = "SAGE_BRAIN_UNOWNED_LISTENER_DETECTED"
            break
        }
        $verifiedListenerPid = $candidateListenerPid
        $brainReady = $false
        $sageReady = $false

        try {
            $brainIdentity = Invoke-RestMethod `
                -Method Get `
                -Uri "http://127.0.0.1:$Port/" `
                -TimeoutSec 3 `
                -ErrorAction Stop
            $brainReady = $brainIdentity.service -eq "NEXUS Brain API"
        }
        catch {
            $brainReady = $false
        }

        if ($brainReady) {
            try {
                $sageHeaders = @{
                    Authorization = "Bearer $sageKey"
                    Accept = "application/json"
                }
                $sageHealth = Invoke-RestMethod `
                    -Method Get `
                    -Uri "http://127.0.0.1:$Port/api/sage/v1/health" `
                    -Headers $sageHeaders `
                    -TimeoutSec 3 `
                    -ErrorAction Stop
                $sageReady = (
                    $sageHealth.ok -eq $true -and
                    $sageHealth.service -eq "nexus-sage-ingress" -and
                    $sageHealth.mode -eq $Mode -and
                    $sageHealth.execution_allowed -eq $false
                )
            }
            catch {
                $sageReady = $false
            }
        }

        if ($brainReady -and $sageReady) {
            try {
                $confirmationSnapshot = @(Get-SageProcessSnapshot)
                Update-SageOwnedProcesses `
                    -OwnedProcesses $ownedProcesses `
                    -Snapshot $confirmationSnapshot
                $confirmedListeners = @(
                    Get-NetTCPConnection -State Listen -ErrorAction Stop |
                        Where-Object { $_.LocalPort -eq $Port }
                )
            }
            catch {
                $safeFailure = "SAGE_BRAIN_LISTENER_CONFIRMATION_FAILED"
                break
            }
            if ($confirmedListeners.Count -ne 1) {
                $safeFailure = "SAGE_BRAIN_AMBIGUOUS_LISTENER_DETECTED"
                break
            }
            if ($confirmedListeners[0].LocalAddress -cne $BindAddress) {
                $safeFailure = "SAGE_BRAIN_NON_LOOPBACK_LISTENER_DETECTED"
                break
            }
            $confirmedListenerPid = [int]$confirmedListeners[0].OwningProcess
            $confirmedListener = @(
                $confirmationSnapshot |
                    Where-Object { [int]$_.ProcessId -eq $confirmedListenerPid }
            )
            if (
                $confirmedListenerPid -ne $verifiedListenerPid -or
                $confirmedListener.Count -ne 1 -or
                -not (Test-SageOwnedProcessRecord `
                    -OwnedProcesses $ownedProcesses `
                    -ProcessRecord $confirmedListener[0])
            ) {
                $safeFailure = "SAGE_BRAIN_LISTENER_CHANGED_DURING_READINESS"
                break
            }
            $listenerConfirmed = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not ($brainReady -and $sageReady -and $listenerConfirmed)) {
        if ($safeFailure -eq "SAGE_BRAIN_START_FAILED") {
            $safeFailure = "SAGE_BRAIN_READINESS_FAILED"
        }
        throw $safeFailure
    }

    Write-Output (
        (
            "SAGE_BRAIN_READY pid={0} listener_pid={0} supervisor_pid={1} " +
            "bind=127.0.0.1 port=7352 mode={2} execution_allowed=false"
        ) -f
        $verifiedListenerPid,
        $process.Id,
        $Mode
    )
}
catch {
    Stop-SageOwnedProcessTree `
        -Process $process `
        -OwnedProcesses $ownedProcesses `
        -VerifiedListenerPid $verifiedListenerPid
    if ($_.Exception.Message -match "^SAGE_[A-Z0-9_]+$") {
        throw $_.Exception.Message
    }
    throw $safeFailure
}
finally {
    $sageHeaders = $null
    $sageKey = $null
}
