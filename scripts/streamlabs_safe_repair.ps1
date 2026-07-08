param(
    [switch]$Apply,
    [switch]$ResetCaches
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SlobsRoot = Join-Path $env:APPDATA "slobs-client"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $RepoRoot "backups\streamlabs-obs-$Stamp"

function Get-StreamlabsRuntimeProcess {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -in @(
                "Streamlabs OBS",
                "obs64",
                "obs-browser-page",
                "crash-handler-process",
                "crashhelper"
            )
        }
}

function Copy-IfExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$DestinationRoot
    )

    if (Test-Path -LiteralPath $Path) {
        $leaf = Split-Path -Leaf $Path
        $dest = Join-Path $DestinationRoot $leaf
        Copy-Item -LiteralPath $Path -Destination $dest -Force
        Write-Output "backed_up`t$Path"
    }
}

function Set-KeyValueLine {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $lines = Get-Content -LiteralPath $Path
    $pattern = "^\s*$([regex]::Escape($Key))\s*="
    $updated = $false
    $out = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $updated = $true
            "$Key=$Value"
        } else {
            $line
        }
    }

    if (-not $updated) {
        $out += "$Key=$Value"
    }

    Set-Content -LiteralPath $Path -Value $out -Encoding UTF8
    Write-Output "patched`t$Path`t$Key=$Value"
}

function Rename-CacheDir {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        $target = "$Path.bak-$Stamp"
        Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $target)
        Write-Output "renamed_cache`t$Path`t$target"
    }
}

if (-not (Test-Path -LiteralPath $SlobsRoot)) {
    throw "Streamlabs config root not found: $SlobsRoot"
}

if ($Apply) {
    $running = @(Get-StreamlabsRuntimeProcess)
    if ($running.Count -gt 0) {
        $names = ($running | Select-Object -ExpandProperty ProcessName -Unique) -join ", "
        throw "Refusing to patch while Streamlabs runtime is active: $names. This script never kills OBS or Chrome; close Streamlabs manually first, then re-run with -Apply."
    }
}

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
Write-Output "backup_root`t$BackupRoot"

$files = @(
    "basic.ini",
    "global.ini",
    "streamEncoder.json",
    "recordEncoder.json",
    "app.log",
    "crash-handler.log",
    "brief-crash-info.json",
    "long_calls.txt"
)

foreach ($file in $files) {
    Copy-IfExists -Path (Join-Path $SlobsRoot $file) -DestinationRoot $BackupRoot
}

$sceneDir = Join-Path $SlobsRoot "SceneCollections"
$scene = Join-Path $sceneDir "4c516060-fc41-4fb9-a715-079742e315be.json"
Copy-IfExists -Path $scene -DestinationRoot $BackupRoot

$obsLogDir = Join-Path $SlobsRoot "node-obs\logs"
if (Test-Path -LiteralPath $obsLogDir) {
    $latestObsLog = Get-ChildItem -LiteralPath $obsLogDir -File -Filter "*.txt" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latestObsLog) {
        Copy-IfExists -Path $latestObsLog.FullName -DestinationRoot $BackupRoot
    }
}

if (-not $Apply) {
    Write-Output "dry_run`tNo Streamlabs files patched. Re-run with -Apply to patch config."
    Write-Output "dry_run`tUse -ResetCaches with -Apply to rename Streamlabs cache directories."
    exit 0
}

$globalIni = Join-Path $SlobsRoot "global.ini"
if (Test-Path -LiteralPath $globalIni) {
    Set-KeyValueLine -Path $globalIni -Key "BrowserHWAccel" -Value "false"
    Set-KeyValueLine -Path $globalIni -Key "fileCaching" -Value "false"
}

$basicIni = Join-Path $SlobsRoot "basic.ini"
if (Test-Path -LiteralPath $basicIni) {
    Set-KeyValueLine -Path $basicIni -Key "ForceGPUAsRenderDevice" -Value "false"
}

$streamEncoder = Join-Path $SlobsRoot "streamEncoder.json"
if (Test-Path -LiteralPath $streamEncoder) {
    $encoder = Get-Content -LiteralPath $streamEncoder -Raw | ConvertFrom-Json
    if ($null -ne $encoder.PSObject.Properties["lookahead"]) {
        $encoder.lookahead = $false
    }
    if ($null -ne $encoder.PSObject.Properties["adaptive_quantization"]) {
        $encoder.adaptive_quantization = $false
    }
    if ($null -ne $encoder.PSObject.Properties["bf"]) {
        $encoder.bf = 0
    }
    $encoder | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $streamEncoder -Encoding UTF8
    Write-Output "patched`t$streamEncoder`tNVENC extras reduced"
}

if ($ResetCaches) {
    $cacheDirs = @(
        "Cache",
        "GPUCache",
        "DawnCache",
        "Code Cache",
        "Session Storage",
        "plugin_config\obs-browser\Cache",
        "plugin_config\obs-browser\GPUCache",
        "plugin_config\obs-browser\DawnCache",
        "plugin_config\obs-browser\Code Cache"
    )

    foreach ($dir in $cacheDirs) {
        Rename-CacheDir -Path (Join-Path $SlobsRoot $dir)
    }
}

Write-Output "complete`tStreamlabs safe repair finished."
