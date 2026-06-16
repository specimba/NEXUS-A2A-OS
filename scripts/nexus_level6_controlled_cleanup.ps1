# NEXUS OS Level 6 controlled cleanup/migration protocol.
# Default mode is read-only dry run. Execute mode moves approved targets to D: quarantine.

[CmdletBinding()]
param(
    [switch]$Execute,
    [switch]$StopApprovedProcesses,
    [switch]$MoveApprovedStaleApps,
    [switch]$CleanApprovedCaches,
    [switch]$CleanNotionCaches,
    [switch]$CleanStreamlabsCaches,
    [switch]$QuarantineKiloSnapshot,
    [switch]$QuarantineKiloGitGarbage,
    [switch]$MoveLegacyProjectCandidates,
    [string]$QuarantineRoot = ("D:\NEXUS_COLD\level6_quarantine_{0}" -f (Get-Date -Format "yyyyMMdd"))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertTo-GiB {
    param([long]$Bytes)
    return [math]::Round($Bytes / 1GB, 3)
}

function Get-DriveRows {
    $driveNames = @("C", "D")
    foreach ($name in $driveNames) {
        $drive = [System.IO.DriveInfo]::GetDrives() | Where-Object { $_.Name -eq "$name`:\" } | Select-Object -First 1
        if ($null -eq $drive) {
            continue
        }

        [pscustomobject][ordered]@{
            Name = $name
            FreeGiB = [math]::Round($drive.AvailableFreeSpace / 1GB, 2)
            UsedGiB = [math]::Round(($drive.TotalSize - $drive.AvailableFreeSpace) / 1GB, 2)
            TotalGiB = [math]::Round($drive.TotalSize / 1GB, 2)
        }
    }
}

function Get-PathSizeBytes {
    param([Parameter(Mandatory)][string]$LiteralPath)

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        return 0L
    }

    $item = Get-Item -LiteralPath $LiteralPath -Force
    if (-not $item.PSIsContainer) {
        return [long]$item.Length
    }

    $total = 0L
    Get-ChildItem -LiteralPath $LiteralPath -Force -Recurse -ErrorAction SilentlyContinue |
        ForEach-Object {
            if (-not $_.PSIsContainer) {
                $total += [long]$_.Length
            }
        }
    return $total
}

function Get-EstimatedReliefGiB {
    param([Parameter(Mandatory)]$Rows)

    $total = 0.0
    foreach ($row in $Rows) {
        $action = [string]$row.action
        if ($action -match "MISSING|BLOCKED") {
            continue
        }

        $sizeProperty = $row.PSObject.Properties["size_gib"]
        if ($null -eq $sizeProperty -or $null -eq $sizeProperty.Value) {
            continue
        }

        $total += [double]$sizeProperty.Value
    }

    return [math]::Round($total, 3)
}

function Get-SafePathToken {
    param([Parameter(Mandatory)][string]$LiteralPath)

    $full = [System.IO.Path]::GetFullPath($LiteralPath)
    $token = $full -replace '^[A-Za-z]:\\', ''
    $token = $token -replace '[\\/:*?"<>|]', '_'
    return $token
}

function New-QuarantineDestination {
    param([Parameter(Mandatory)][string]$LiteralPath)

    $token = Get-SafePathToken -LiteralPath $LiteralPath
    $dest = Join-Path -Path $QuarantineRoot -ChildPath $token
    if (Test-Path -LiteralPath $dest) {
        $suffix = Get-Date -Format "yyyyMMdd_HHmmss"
        $dest = "$dest.$suffix"
    }
    return $dest
}

function Move-ToQuarantine {
    param(
        [Parameter(Mandatory)][string]$LiteralPath,
        [Parameter(Mandatory)][string]$Reason
    )

    $bytes = Get-PathSizeBytes -LiteralPath $LiteralPath
    $dest = New-QuarantineDestination -LiteralPath $LiteralPath
    $row = [ordered]@{
        action = if ($Execute) { "MOVE" } else { "DRY_RUN_MOVE" }
        source = $LiteralPath
        size_gib = ConvertTo-GiB -Bytes $bytes
        destination = $dest
        reason = $Reason
    }

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        $row.action = "MISSING"
        [pscustomobject]$row
        return
    }

    if ($Execute) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
        Move-Item -LiteralPath $LiteralPath -Destination $dest -Force
    }

    [pscustomobject]$row
}

function Get-ApprovedProcessMatches {
    $patterns = @()
    $processNamePatterns = @()

    if ($QuarantineKiloSnapshot -or $QuarantineKiloGitGarbage) {
        $patterns += "\\.windsurf\\extensions\\kilocode\.kilo-code-"
        $patterns += "\\AppData\\Roaming\\npm\\node_modules\\@kilocode\\cli\\"
        $processNamePatterns += "^(kilo|kilocode)$"
    }

    if ($MoveApprovedStaleApps) {
        $patterns += "\\AppData\\Local\\Programs\\Windsurf\\"
        $patterns += "\\.windsurf\\"
        $patterns += "\\AppData\\Local\\Programs\\Cursor\\"
        $patterns += "\\AppData\\Roaming\\Jan\\"
        $patterns += "\\AppData\\Local\\Programs\\Jan\\"
        $processNamePatterns += "^(Windsurf|Cursor|Jan|devin|kilo|kilocode)$"
    }

    if ($CleanApprovedCaches -or $CleanNotionCaches) {
        $patterns += "\\AppData\\Local\\Programs\\Notion\\"
        $patterns += "\\AppData\\Roaming\\Notion\\"
        $processNamePatterns += "^(Notion)$"
    }

    if ($CleanApprovedCaches -or $CleanStreamlabsCaches) {
        $patterns += "\\Program Files\\Streamlabs OBS\\"
        $patterns += "\\AppData\\Roaming\\slobs-client\\"
        $processNamePatterns += "^(Streamlabs OBS|slobs-client)$"
    }

    if ($patterns.Count -eq 0 -and $processNamePatterns.Count -eq 0) {
        return @()
    }

    try {
        return @(Get-CimInstance Win32_Process |
            Where-Object {
                $line = "$($_.ExecutablePath) $($_.CommandLine)"
                foreach ($pattern in $patterns) {
                    if ($line -match $pattern) {
                        return $true
                    }
                }
                return $false
            } |
            Select-Object ProcessId, Name, ExecutablePath, CommandLine)
    } catch {
        Write-Host ("PROCESS_CIM_UNAVAILABLE={0}" -f $_.Exception.Message)
    }

    return @(Get-Process -ErrorAction SilentlyContinue |
        ForEach-Object {
            $path = $null
            try {
                $path = $_.Path
            } catch {
                $path = $null
            }

            $line = "$path $($_.ProcessName)"
            $matched = $false
            foreach ($pattern in $patterns) {
                if ($line -match $pattern) {
                    $matched = $true
                }
            }
            foreach ($namePattern in $processNamePatterns) {
                if ($_.ProcessName -match $namePattern) {
                    $matched = $true
                }
            }

            if ($matched) {
                [pscustomobject][ordered]@{
                    ProcessId = $_.Id
                    Name = $_.ProcessName
                    ExecutablePath = $path
                    CommandLine = ""
                }
            }
        })
}

function Stop-ApprovedProcessMatches {
    $matches = @(Get-ApprovedProcessMatches)
    foreach ($proc in $matches) {
        [pscustomobject][ordered]@{
            action = if ($Execute -and $StopApprovedProcesses) { "STOP" } else { "DRY_RUN_STOP" }
            pid = $proc.ProcessId
            name = $proc.Name
            path = $proc.ExecutablePath
        }
        if ($Execute -and $StopApprovedProcesses) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Test-KiloRunning {
    $matches = @(Get-ApprovedProcessMatches | Where-Object {
        "$($_.ExecutablePath) $($_.CommandLine)" -match "\\kilocode|\\@kilocode\\|\\kilo-code-"
    })
    return ($matches.Count -gt 0)
}

function Get-KiloGitGarbageTargets {
    $snapshot = "C:\Users\speci.000\.local\share\kilo\snapshot"
    if (-not (Test-Path -LiteralPath $snapshot)) {
        return @()
    }

    @(Get-ChildItem -LiteralPath $snapshot -Recurse -Force -File -Filter "tmp_pack_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\objects\\pack\\tmp_pack_" } |
        Select-Object -ExpandProperty FullName)
}

Write-Host "NEXUS_LEVEL6_CONTROLLED_CLEANUP"
Write-Host ("mode={0}" -f ($(if ($Execute) { "EXECUTE" } else { "DRY_RUN" })))
Write-Host ("quarantine_root={0}" -f $QuarantineRoot)

$driveRows = Get-DriveRows
Write-Host "DRIVES_BEFORE"
$driveRows | Format-Table -AutoSize

Write-Host "APPROVED_PROCESS_MATCHES"
Stop-ApprovedProcessMatches | Format-Table -AutoSize -Wrap

$actionRows = New-Object System.Collections.Generic.List[object]

if ($MoveApprovedStaleApps) {
    $approvedStaleApps = @(
        @{ Path = "C:\Users\speci.000\Music\DJ.Studio\Exports\2212chilldeepmix.wav"; Reason = "User-approved personal media purge to quarantine" },
        @{ Path = "C:\Users\speci.000\.windsurf"; Reason = "User-approved broken Windsurf state purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Windsurf"; Reason = "User-approved broken Windsurf app state purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Local\Programs\Windsurf"; Reason = "User-approved broken Windsurf install purge to quarantine" },
        @{ Path = "C:\Users\speci.000\.cursor"; Reason = "User-approved unused Cursor state purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Cursor"; Reason = "User-approved unused Cursor app state purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Local\Programs\Cursor"; Reason = "User-approved unused Cursor install purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Jan"; Reason = "User-approved unused Jan app/model state purge to quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Local\Programs\Jan"; Reason = "User-approved unused Jan install purge to quarantine" }
    )

    foreach ($target in $approvedStaleApps) {
        $actionRows.Add((Move-ToQuarantine -LiteralPath $target.Path -Reason $target.Reason))
    }
}

if ($CleanApprovedCaches -or $CleanNotionCaches) {
    $approvedCaches = @(
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Notion\Partitions"; Reason = "User-approved Notion Electron cache quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Notion\Cache"; Reason = "User-approved Notion cache quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Notion\Code Cache"; Reason = "User-approved Notion code cache quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\Notion\GPUCache"; Reason = "User-approved Notion GPU cache quarantine" }
    )

    foreach ($target in $approvedCaches) {
        $actionRows.Add((Move-ToQuarantine -LiteralPath $target.Path -Reason $target.Reason))
    }
}

if ($CleanApprovedCaches -or $CleanStreamlabsCaches) {
    $approvedCaches = @(
        @{ Path = "C:\Users\speci.000\AppData\Roaming\slobs-client\Partitions"; Reason = "User-approved Streamlabs OBS Electron cache quarantine; Media is not touched" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\slobs-client\Cache"; Reason = "User-approved Streamlabs OBS cache quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\slobs-client\Code Cache"; Reason = "User-approved Streamlabs OBS code cache quarantine" },
        @{ Path = "C:\Users\speci.000\AppData\Roaming\slobs-client\GPUCache"; Reason = "User-approved Streamlabs OBS GPU cache quarantine" }
    )

    foreach ($target in $approvedCaches) {
        $actionRows.Add((Move-ToQuarantine -LiteralPath $target.Path -Reason $target.Reason))
    }
}

if ($MoveLegacyProjectCandidates) {
    $legacyProjects = @(
        @{ Path = "C:\MyFlaskAI"; Reason = "Legacy SEQUENCE Flask desk pack; move only with explicit legacy-project approval" },
        @{ Path = "C:\tmp"; Reason = "Temporary project clones/build artifacts; move only with explicit legacy-project approval" },
        @{ Path = "C:\GitHubVs"; Reason = "Legacy SEQUENCE app workspace; move only with explicit legacy-project approval" }
    )

    foreach ($target in $legacyProjects) {
        $actionRows.Add((Move-ToQuarantine -LiteralPath $target.Path -Reason $target.Reason))
    }
}

if ($QuarantineKiloSnapshot -or $QuarantineKiloGitGarbage) {
    if ((Test-KiloRunning) -and (-not $StopApprovedProcesses)) {
        $actionRows.Add([pscustomobject][ordered]@{
            action = "BLOCKED_KILO_RUNNING"
            source = "C:\Users\speci.000\.local\share\kilo\snapshot"
            size_gib = ConvertTo-GiB -Bytes (Get-PathSizeBytes -LiteralPath "C:\Users\speci.000\.local\share\kilo\snapshot")
            destination = ""
            reason = "Kilo processes are running; rerun with -StopApprovedProcesses or stop Kilo manually"
        })
    } elseif ($QuarantineKiloSnapshot) {
        $actionRows.Add((Move-ToQuarantine -LiteralPath "C:\Users\speci.000\.local\share\kilo\snapshot" -Reason "Kilo Git/LFS snapshot quarantine; contains large packs, garbage tmp packs, and sensitive session evidence"))
    } elseif ($QuarantineKiloGitGarbage) {
        foreach ($garbage in Get-KiloGitGarbageTargets) {
            $actionRows.Add((Move-ToQuarantine -LiteralPath $garbage -Reason "Kilo Git garbage tmp_pack quarantine"))
        }
    }
}

Write-Host "PLANNED_ACTIONS"
if ($actionRows.Count -gt 0) {
    $actionRows | Format-Table -AutoSize -Wrap
    $total = Get-EstimatedReliefGiB -Rows $actionRows
    Write-Host ("estimated_c_gib_relieved={0}" -f $total)
} else {
    Write-Host "No action flags were selected."
}

if ($Execute) {
    Write-Host "DRIVES_AFTER"
    Get-DriveRows |
        Format-Table -AutoSize
}
