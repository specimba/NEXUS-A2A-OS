param(
    [string]$UserRoot = "C:\Users\speci.000",
    [string]$RepoRoot = "C:\Users\speci.000\Documents\NEXUS",
    [int]$Top = 20
)

$ErrorActionPreference = "Continue"

function Format-BytesGB {
    param([Int64]$Bytes)
    return [math]::Round(($Bytes / 1GB), 2)
}

function Get-TreeStatsNoReparse {
    param([string]$Path)

    $total = 0L
    $files = 0L
    $dirs = 0L
    $latest = $null

    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ Bytes = 0L; Files = 0L; Dirs = 0L; LatestWrite = $null }
    }

    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($Path)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        try {
            foreach ($entry in [System.IO.Directory]::EnumerateFileSystemEntries($current)) {
                try {
                    $attrs = [System.IO.File]::GetAttributes($entry)
                    if (($attrs -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                        continue
                    }

                    if (($attrs -band [System.IO.FileAttributes]::Directory) -ne 0) {
                        $dirs++
                        $dirInfo = [System.IO.DirectoryInfo]$entry
                        if ($null -eq $latest -or $dirInfo.LastWriteTime -gt $latest) {
                            $latest = $dirInfo.LastWriteTime
                        }
                        $stack.Push($entry)
                    } else {
                        $fileInfo = [System.IO.FileInfo]$entry
                        $total += $fileInfo.Length
                        $files++
                        if ($null -eq $latest -or $fileInfo.LastWriteTime -gt $latest) {
                            $latest = $fileInfo.LastWriteTime
                        }
                    }
                } catch {}
            }
        } catch {}
    }

    return [pscustomobject]@{ Bytes = $total; Files = $files; Dirs = $dirs; LatestWrite = $latest }
}

function Get-FirstLevelDirReport {
    param(
        [string]$Path,
        [string]$Label,
        [int]$Limit = 20
    )

    Write-Output ""
    Write-Output "## $Label"
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Output "MISSING $Path"
        return
    }

    $rows = @()
    foreach ($dir in Get-ChildItem -LiteralPath $Path -Force -Directory -ErrorAction SilentlyContinue) {
        if (($dir.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            $rows += [pscustomobject]@{
                Path = $dir.FullName
                SizeGB = 0
                Files = 0
                Dirs = 0
                LatestWrite = $dir.LastWriteTime
                Note = "junction/reparse-skipped"
            }
            continue
        }
        $stats = Get-TreeStatsNoReparse -Path $dir.FullName
        $rows += [pscustomobject]@{
            Path = $dir.FullName
            SizeGB = Format-BytesGB $stats.Bytes
            Files = $stats.Files
            Dirs = $stats.Dirs
            LatestWrite = $stats.LatestWrite
            Note = ""
        }
    }

    $rows |
        Sort-Object SizeGB -Descending |
        Select-Object -First $Limit |
        Format-Table -AutoSize
}

function Get-TopFilesNoReparse {
    param(
        [string]$Path,
        [string]$Label,
        [int]$Limit = 30
    )

    Write-Output ""
    Write-Output "## $Label"
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Output "MISSING $Path"
        return
    }

    $topFiles = New-Object System.Collections.Generic.List[object]
    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($Path)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        try {
            foreach ($entry in [System.IO.Directory]::EnumerateFileSystemEntries($current)) {
                try {
                    $attrs = [System.IO.File]::GetAttributes($entry)
                    if (($attrs -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                        continue
                    }
                    if (($attrs -band [System.IO.FileAttributes]::Directory) -ne 0) {
                        $stack.Push($entry)
                    } else {
                        $fileInfo = [System.IO.FileInfo]$entry
                        if ($fileInfo.Length -ge 100MB) {
                            $topFiles.Add([pscustomobject]@{
                                SizeGB = Format-BytesGB $fileInfo.Length
                                LastWrite = $fileInfo.LastWriteTime
                                Path = $fileInfo.FullName
                            })
                        }
                    }
                } catch {}
            }
        } catch {}
    }

    $topFiles |
        Sort-Object SizeGB -Descending |
        Select-Object -First $Limit |
        Format-Table -AutoSize
}

function Get-InstalledAppReport {
    Write-Output ""
    Write-Output "## Installed Apps By Registry Estimated Size"
    $keys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    $apps = foreach ($key in $keys) {
        Get-ItemProperty $key -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -and $_.EstimatedSize } |
            ForEach-Object {
                [pscustomobject]@{
                    SizeGB = [math]::Round(($_.EstimatedSize / 1024 / 1024), 2)
                    Name = $_.DisplayName
                    Version = $_.DisplayVersion
                    InstallLocation = $_.InstallLocation
                }
            }
    }
    $apps |
        Sort-Object SizeGB -Descending |
        Select-Object -First 30 |
        Format-Table -AutoSize
}

Write-Output "# NEXUS Disk Inventory Read-Only"
Write-Output ("Timestamp: {0:o}" -f (Get-Date))

Write-Output ""
Write-Output "## Drive Free Space"
Get-PSDrive -PSProvider FileSystem |
    Where-Object { $_.Name -in @("C", "D") } |
    Select-Object Name,
        @{n="FreeGB";e={[math]::Round($_.Free/1GB,2)}},
        @{n="UsedGB";e={[math]::Round($_.Used/1GB,2)}} |
    Format-Table -AutoSize

Get-FirstLevelDirReport -Path "C:\" -Label "C Root First-Level Directories" -Limit $Top
Get-FirstLevelDirReport -Path $UserRoot -Label "User Root First-Level Directories" -Limit $Top
Get-FirstLevelDirReport -Path (Join-Path $UserRoot "AppData\Local") -Label "AppData Local First-Level Directories" -Limit $Top
Get-FirstLevelDirReport -Path (Join-Path $UserRoot "AppData\Roaming") -Label "AppData Roaming First-Level Directories" -Limit $Top
Get-FirstLevelDirReport -Path (Join-Path $UserRoot "AppData\Local\Packages") -Label "Windows Store Packages" -Limit $Top
Get-FirstLevelDirReport -Path (Join-Path $UserRoot "Downloads") -Label "Downloads First-Level Directories" -Limit $Top
Get-FirstLevelDirReport -Path $RepoRoot -Label "NEXUS Repo First-Level Directories Skipping Junction Targets" -Limit $Top

Get-TopFilesNoReparse -Path $UserRoot -Label "Top User Files >=100MB Skipping Junction Targets" -Limit 40
Get-TopFilesNoReparse -Path "C:\" -Label "Top C Files >=100MB Skipping Junction Targets" -Limit 40

Get-InstalledAppReport

Write-Output ""
Write-Output "## WSL Distributions"
wsl.exe -l -v 2>$null

