param(
    [string]$GrokHome = "$env:USERPROFILE\.grok",
    [string]$OutputRoot = "logs/forensics/grok-upload-queue",
    [int]$TopN = 50,
    [switch]$HashTopFiles
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $repoRoot (Join-Path $OutputRoot $runId)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$queueDir = Join-Path $GrokHome "upload_queue"
$inventoryPath = Join-Path $outDir "queue_inventory.csv"
$groupsPath = Join-Path $outDir "dedup_groups.csv"
$topPath = Join-Path $outDir "top_files.csv"
$sessionPath = Join-Path $outDir "session_metadata.csv"
$indicatorPath = Join-Path $outDir "binary_indicators.txt"
$summaryPath = Join-Path $outDir "summary.json"

function Convert-UnixMsToIso($msText) {
    try {
        $ms = [int64]$msText
        return ([DateTimeOffset]::FromUnixTimeMilliseconds($ms).ToLocalTime()).ToString("o")
    } catch {
        return ""
    }
}

function Get-FileSignature($path, $length) {
    $readLen = [Math]::Min([int64]65536, [int64]$length)
    if ($readLen -le 0) {
        return [pscustomobject]@{ Magic = "empty"; Hex16 = ""; PrintableRatio = 0.0 }
    }

    $buffer = New-Object byte[] $readLen
    $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $bytesRead = $stream.Read($buffer, 0, $readLen)
    } finally {
        $stream.Close()
    }

    $slice = if ($bytesRead -lt $buffer.Length) { $buffer[0..($bytesRead - 1)] } else { $buffer }
    $hex16 = (($slice | Select-Object -First 16 | ForEach-Object { $_.ToString("X2") }) -join "")

    $magic = "binary"
    if ($hex16.StartsWith("504B0304")) { $magic = "zip" }
    elseif ($hex16.StartsWith("1F8B")) { $magic = "gzip" }
    elseif ($hex16.StartsWith("89504E47")) { $magic = "png" }
    elseif ($hex16.StartsWith("FFD8FF")) { $magic = "jpeg" }
    elseif ($hex16.StartsWith("25504446")) { $magic = "pdf" }
    elseif ($hex16.StartsWith("934E554D5059")) { $magic = "numpy" }
    else {
        $ascii = [System.Text.Encoding]::ASCII.GetString($slice)
        if ($ascii.StartsWith("SQLite format 3")) { $magic = "sqlite" }
        else {
            $trimmed = $ascii.TrimStart()
            if ($trimmed.StartsWith("{") -or $trimmed.StartsWith("[")) { $magic = "json_or_text" }
        }
    }

    $printable = 0
    foreach ($b in $slice) {
        if (($b -ge 32 -and $b -le 126) -or $b -in @(9,10,13)) {
            $printable++
        }
    }
    $ratio = if ($bytesRead -gt 0) { [math]::Round($printable / $bytesRead, 4) } else { 0.0 }
    return [pscustomobject]@{ Magic = $magic; Hex16 = $hex16; PrintableRatio = $ratio }
}

if (-not (Test-Path -LiteralPath $queueDir)) {
    throw "Upload queue not found: $queueDir"
}

$files = @(Get-ChildItem -LiteralPath $queueDir -Force -File)
$inventory = foreach ($f in $files) {
    $sessionPrefix = ""
    $dedupKey = ""
    $encodedMs = ""
    $ordinal = ""
    if ($f.Name -match "^([0-9a-f]{8})_turn\d+_dedup_([a-f0-9]+)_([0-9]{13})_([0-9]+)$") {
        $sessionPrefix = $Matches[1]
        $dedupKey = $Matches[2]
        $encodedMs = $Matches[3]
        $ordinal = $Matches[4]
    } elseif ($f.Name -match "^dedup_([a-f0-9]+)_([0-9]{13})_([0-9]+)$") {
        $sessionPrefix = "direct"
        $dedupKey = $Matches[1]
        $encodedMs = $Matches[2]
        $ordinal = $Matches[3]
    } else {
        $sessionPrefix = "unparsed"
    }

    [pscustomobject]@{
        name = $f.Name
        bytes = $f.Length
        mb = [math]::Round($f.Length / 1MB, 2)
        creation_time = $f.CreationTime.ToString("o")
        last_write_time = $f.LastWriteTime.ToString("o")
        encoded_local_time = Convert-UnixMsToIso $encodedMs
        session_prefix = $sessionPrefix
        dedup_key = $dedupKey
        ordinal = $ordinal
    }
}
$inventory | Export-Csv -NoTypeInformation -Encoding UTF8 $inventoryPath

$inventory |
    Group-Object dedup_key |
    ForEach-Object {
        $group = $_.Group
        [pscustomobject]@{
            dedup_key = if ($_.Name) { $_.Name } else { "missing" }
            count = $_.Count
            total_bytes = ($group | Measure-Object bytes -Sum).Sum
            total_mb = [math]::Round((($group | Measure-Object bytes -Sum).Sum) / 1MB, 2)
            max_mb = [math]::Round((($group | Measure-Object bytes -Maximum).Maximum) / 1MB, 2)
            first_write = ($group | Sort-Object last_write_time | Select-Object -First 1).last_write_time
            last_write = ($group | Sort-Object last_write_time -Descending | Select-Object -First 1).last_write_time
        }
    } |
    Sort-Object total_bytes -Descending |
    Export-Csv -NoTypeInformation -Encoding UTF8 $groupsPath

$topFiles = $files | Sort-Object Length -Descending | Select-Object -First $TopN
$topRows = foreach ($f in $topFiles) {
    $sig = Get-FileSignature $f.FullName $f.Length
    $sha256 = ""
    if ($HashTopFiles) {
        $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash
    }
    [pscustomobject]@{
        name = $f.Name
        bytes = $f.Length
        mb = [math]::Round($f.Length / 1MB, 2)
        creation_time = $f.CreationTime.ToString("o")
        last_write_time = $f.LastWriteTime.ToString("o")
        magic = $sig.Magic
        hex16 = $sig.Hex16
        printable_ratio_first64k = $sig.PrintableRatio
        sha256 = $sha256
    }
}
$topRows | Export-Csv -NoTypeInformation -Encoding UTF8 $topPath

$sessionRoot = Join-Path $GrokHome "sessions"
if (Test-Path -LiteralPath $sessionRoot) {
    Get-ChildItem -LiteralPath $sessionRoot -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "\\upload_queue\\" } |
        Select-Object FullName, Length, CreationTime, LastWriteTime |
        Export-Csv -NoTypeInformation -Encoding UTF8 $sessionPath
}

$exePath = Join-Path $GrokHome "bin\grok.exe"
if (Test-Path -LiteralPath $exePath) {
    $patterns = @(
        "upload_queue",
        "uploadId",
        "partUrls",
        "dedup_binary",
        "dedup_untracked",
        "response.queued",
        "response.failed",
        "api.x.ai",
        "auth.x.ai",
        "multipart",
        "presign",
        "bucket",
        "artifact"
    )
    foreach ($pattern in $patterns) {
        $count = (rg -a -o --fixed-strings $pattern $exePath | Measure-Object).Count
        "{0},{1}" -f $pattern, $count | Add-Content -Encoding UTF8 $indicatorPath
    }
}

$summary = [ordered]@{
    run_id = $runId
    grok_home = $GrokHome
    queue_dir = $queueDir
    file_count = $files.Count
    total_bytes = ($files | Measure-Object Length -Sum).Sum
    total_gb = [math]::Round((($files | Measure-Object Length -Sum).Sum) / 1GB, 3)
    first_write = ($files | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime.ToString("o")
    last_write = ($files | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime.ToString("o")
    unique_dedup_keys = @($inventory | Where-Object dedup_key | Select-Object -ExpandProperty dedup_key -Unique).Count
    session_prefixed_files = @($inventory | Where-Object { $_.session_prefix -ne "direct" -and $_.session_prefix -ne "unparsed" }).Count
    direct_dedup_files = @($inventory | Where-Object { $_.session_prefix -eq "direct" }).Count
    unparsed_files = @($inventory | Where-Object { $_.session_prefix -eq "unparsed" }).Count
    output_dir = $outDir
    files = @{
        inventory = $inventoryPath
        dedup_groups = $groupsPath
        top_files = $topPath
        session_metadata = $sessionPath
        binary_indicators = $indicatorPath
    }
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $summaryPath
Write-Output ($summary | ConvertTo-Json -Depth 6)
