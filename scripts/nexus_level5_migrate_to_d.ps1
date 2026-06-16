param(
    [switch]$Execute,
    [switch]$IncludeGitInternals,
    [switch]$SkipTempMoves,
    [switch]$ForceStopGit,
    [string]$RepoRoot = "C:\Users\speci.000\Documents\NEXUS",
    [string]$DestinationRoot = "D:\NEXUS_COLD\level5_migrations_20260605\NEXUS"
)

$ErrorActionPreference = "Stop"

function Get-DirectorySize {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ Bytes = 0L; Files = 0 }
    }
    $files = Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue
    $measure = $files | Measure-Object -Property Length -Sum
    return [pscustomobject]@{ Bytes = [int64]($measure.Sum); Files = [int]($measure.Count) }
}

function Assert-UnderRoot {
    param(
        [string]$Path,
        [string]$Root
    )
    $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes expected root. Path=$resolvedPath Root=$resolvedRoot"
    }
}

function Move-ToDWithJunction {
    param(
        [string]$Source,
        [string]$Target
    )

    Assert-UnderRoot -Path $Source -Root $RepoRoot
    Assert-UnderRoot -Path $Target -Root $DestinationRoot

    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host "SKIP missing source: $Source"
        return
    }

    $sourceItem = Get-Item -LiteralPath $Source -Force
    if (($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Write-Host "SKIP already reparse point: $Source"
        return
    }

    if (Test-Path -LiteralPath $Target) {
        throw "Target already exists; refusing overwrite: $Target"
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Target) -Force | Out-Null

    Write-Host "MOVE: $Source -> $Target"
    if ($Execute) {
        Move-Item -LiteralPath $Source -Destination $Target
        New-Item -ItemType Junction -Path $Source -Target $Target | Out-Null
    }
}

function Move-ToDNoJunction {
    param(
        [string]$Source,
        [string]$Target
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host "SKIP missing source: $Source"
        return
    }
    if (Test-Path -LiteralPath $Target) {
        throw "Target already exists; refusing overwrite: $Target"
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Target) -Force | Out-Null

    Write-Host "MOVE TEMP: $Source -> $Target"
    if ($Execute) {
        Move-Item -LiteralPath $Source -Destination $Target
    }
}

$repoFull = [System.IO.Path]::GetFullPath($RepoRoot)
$destFull = [System.IO.Path]::GetFullPath($DestinationRoot)

if (-not (Test-Path -LiteralPath $repoFull)) {
    throw "Repo root not found: $repoFull"
}
if (-not $destFull.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must be on D: for Level 5 migration. Destination=$destFull"
}

$gitProcesses = Get-Process -Name git,git-lfs -ErrorAction SilentlyContinue
if ($IncludeGitInternals -and $gitProcesses.Count -gt 0) {
    if (-not $ForceStopGit) {
        $pids = ($gitProcesses | Select-Object -ExpandProperty Id) -join ","
        throw "Git processes are active; refusing to move .git internals. PIDs=$pids"
    }
    $pids = ($gitProcesses | Select-Object -ExpandProperty Id) -join ","
    Write-Host "STOP GIT WRITERS: $pids"
    if ($Execute) {
        $gitProcesses | Stop-Process -Force
        Start-Sleep -Seconds 2
    }
    $gitProcesses = Get-Process -Name git,git-lfs -ErrorAction SilentlyContinue
    if ($Execute -and $gitProcesses.Count -gt 0) {
        $pids = ($gitProcesses | Select-Object -ExpandProperty Id) -join ","
        throw "Git processes are still active after stop attempt. PIDs=$pids"
    }
}

$items = @(
    @{ Source = Join-Path $repoFull "models"; Target = Join-Path $destFull "models" },
    @{ Source = Join-Path $repoFull "benchmarks"; Target = Join-Path $destFull "benchmarks" },
    @{ Source = Join-Path $repoFull "foundry_datasets"; Target = Join-Path $destFull "foundry_datasets" },
    @{ Source = Join-Path $repoFull "datasets"; Target = Join-Path $destFull "datasets" }
)

if ($IncludeGitInternals) {
    $items += @(
        @{ Source = Join-Path $repoFull ".git\lfs"; Target = Join-Path $destFull ".git\lfs" },
        @{ Source = Join-Path $repoFull ".git\objects"; Target = Join-Path $destFull ".git\objects" }
    )
}

Write-Host "NEXUS Level 5 migration dry-run=$(-not $Execute) includeGitInternals=$IncludeGitInternals"
Write-Host "Repo: $repoFull"
Write-Host "Dest: $destFull"

$totalBytes = 0L
foreach ($item in $items) {
    $size = Get-DirectorySize -Path $item.Source
    $totalBytes += $size.Bytes
    "{0,8:N2} GiB  {1,8} files  {2}" -f ($size.Bytes / 1GB), $size.Files, $item.Source
}

$tempMoves = @(
    @{
        Source = "C:\Users\speci.000\AppData\Local\Temp\DABD0504-A782-4440-82DE-9C4D759FEED7"
        Target = "D:\NEXUS_COLD\level5_migrations_20260605\temp_quarantine\DABD0504-A782-4440-82DE-9C4D759FEED7"
    },
    @{
        Source = "C:\Users\speci.000\AppData\Local\Temp\YAwBx7aX"
        Target = "D:\NEXUS_COLD\level5_migrations_20260605\temp_quarantine\YAwBx7aX"
    }
)

foreach ($move in $tempMoves) {
    if ($SkipTempMoves) {
        continue
    }
    if (Test-Path -LiteralPath $move.Source) {
        $size = Get-DirectorySize -Path $move.Source
        $totalBytes += $size.Bytes
        "{0,8:N2} GiB  {1,8} files  {2}" -f ($size.Bytes / 1GB), $size.Files, $move.Source
    }
}

"Estimated C: relief: {0:N2} GiB" -f ($totalBytes / 1GB)

if (-not $Execute) {
    Write-Host "DRY RUN ONLY. Re-run with -Execute to move data and create junctions."
    exit 0
}

foreach ($item in $items) {
    Move-ToDWithJunction -Source $item.Source -Target $item.Target
}

if (-not $SkipTempMoves) {
    foreach ($move in $tempMoves) {
        Move-ToDNoJunction -Source $move.Source -Target $move.Target
    }
}

Write-Host "Migration complete. Verify with:"
Write-Host "  Get-PSDrive C,D"
Write-Host "  git -C `"$repoFull`" status --short"
