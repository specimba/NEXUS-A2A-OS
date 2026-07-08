param(
    [int]$SinceHours = 24,
    [string]$SlobsRoot = (Join-Path $env:APPDATA "slobs-client")
)

$ErrorActionPreference = "Continue"

function Write-Section {
    param([string]$Name)
    ""
    "## $Name"
}

function Convert-BytesToGB {
    param([double]$Value)
    [math]::Round($Value / 1GB, 2)
}

$since = (Get-Date).AddHours(-1 * $SinceHours)

"# Streamlabs Health Probe"
""
"Runtime: $(Get-Date -Format o)"
"Window: last $SinceHours hours"
"SlobsRoot: $SlobsRoot"

Write-Section "Current Streamlabs Processes"
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -match 'Streamlabs|obs64|slobs|crash' } |
    Select-Object Id, ProcessName, @{Name='PrivateGB';Expression={Convert-BytesToGB $_.PrivateMemorySize64}}, @{Name='WorkingGB';Expression={Convert-BytesToGB $_.WorkingSet64}}, StartTime |
    Format-Table -AutoSize |
    Out-String |
    Write-Output

Write-Section "Memory Commit"
$counter = Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit','\Memory\Available MBytes','\Paging File(_Total)\% Usage' -ErrorAction SilentlyContinue
$values = @{}
foreach ($sample in $counter.CounterSamples) {
    $values[$sample.Path] = $sample.CookedValue
}
$committedKey = $values.Keys | Where-Object { $_ -like '*committed bytes' } | Select-Object -First 1
$limitKey = $values.Keys | Where-Object { $_ -like '*commit limit' } | Select-Object -First 1
if ($committedKey -and $limitKey) {
    $used = $values[$committedKey]
    $limit = $values[$limitKey]
    [pscustomobject]@{
        CommitUsedGB = Convert-BytesToGB $used
        CommitLimitGB = Convert-BytesToGB $limit
        CommitPercent = [math]::Round(($used / $limit) * 100, 1)
        Status = if (($used / $limit) -ge 0.90) { "DANGER" } elseif (($used / $limit) -ge 0.80) { "WARN" } else { "OK" }
    } | Format-List | Out-String | Write-Output
}
foreach ($entry in $values.GetEnumerator()) {
    if ($entry.Key -like '*available mbytes' -or $entry.Key -like '*paging file*') {
        "$($entry.Key) = $([math]::Round($entry.Value, 2))"
    }
}

Write-Section "Top Private Memory Processes"
Get-Process |
    Sort-Object PrivateMemorySize64 -Descending |
    Select-Object -First 15 Id, ProcessName, @{Name='PrivateGB';Expression={Convert-BytesToGB $_.PrivateMemorySize64}}, @{Name='WorkingGB';Expression={Convert-BytesToGB $_.WorkingSet64}}, CPU |
    Format-Table -AutoSize |
    Out-String |
    Write-Output

Write-Section "Recent Streamlabs / OBS Crashes"
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$since} -ErrorAction SilentlyContinue |
    Where-Object { $_.ProviderName -in @('Application Error','Windows Error Reporting') -and $_.Message -match 'Streamlabs|slobs|obs64|obs.dll' } |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 10 TimeCreated, ProviderName, Id, @{Name='Message';Expression={($_.Message -replace "`r?`n",' | ')}} |
    Format-List |
    Out-String |
    Write-Output

Write-Section "Recent Resource Exhaustion"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Resource-Exhaustion-Detector'; Id=2004; StartTime=$since} -ErrorAction SilentlyContinue |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 10 TimeCreated, Id, @{Name='Message';Expression={($_.Message -replace "`r?`n",' | ')}} |
    Format-List |
    Out-String |
    Write-Output

Write-Section "Recent GPU / WHEA Events"
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$since} -ErrorAction SilentlyContinue |
    Where-Object { $_.ProviderName -match 'WHEA|Display|nvlddmkm|DxgKrnl|Dwm' -or $_.Message -match 'nvlddmkm|Display driver|NVIDIA|PCI Express|dwm' } |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 20 TimeCreated, ProviderName, Id, LevelDisplayName, @{Name='Message';Expression={($_.Message -replace "`r?`n",' | ')}} |
    Format-List |
    Out-String |
    Write-Output

Write-Section "Streamlabs Config Flags"
if (Test-Path -LiteralPath $SlobsRoot) {
    foreach ($file in "global.ini","basic.ini","streamEncoder.json","recordEncoder.json") {
        $path = Join-Path $SlobsRoot $file
        "--- $file"
        if (Test-Path -LiteralPath $path) {
            Select-String -Path $path -Pattern 'BrowserHWAccel|fileCaching|ForceGPUAsRenderDevice|lookahead|adaptive_quantization|bf|obs_nvenc|Encoder|RecEncoder' -CaseSensitive:$false |
                ForEach-Object { "$($_.LineNumber): $($_.Line.Trim())" }
        } else {
            "MISSING"
        }
    }
} else {
    "Missing Streamlabs root: $SlobsRoot"
}

Write-Section "Scene Risk Summary"
$sceneDir = Join-Path $SlobsRoot "SceneCollections"
$scene = Get-ChildItem -LiteralPath $sceneDir -File -Filter "*.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne "manifest.json" -and $_.Name -notlike "*.bak" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($scene) {
    $text = Get-Content -Raw -LiteralPath $scene.FullName
    [pscustomobject]@{
        Scene = $scene.FullName
        SceneMB = [math]::Round($scene.Length / 1MB, 2)
        BrowserSourceMentions = [regex]::Matches($text, 'browser_source_').Count
        FFmpegSourceMentions = [regex]::Matches($text, 'ffmpeg_source_').Count
        EmptyUrlMentions = [regex]::Matches($text, '"url"\s*:\s*""').Count
    } | Format-List | Out-String | Write-Output

    try {
        $convertFromJson = Get-Command ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($convertFromJson -and $convertFromJson.Parameters.ContainsKey("Depth")) {
            $json = $text | ConvertFrom-Json -Depth 100
        } else {
            $json = $text | ConvertFrom-Json
        }
        $script:sources = @()
        function Walk-SceneNode {
            param($Node)
            if ($null -eq $Node) { return }
            if ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
                foreach ($child in $Node) { Walk-SceneNode $child }
                return
            }
            if ($Node.PSObject -and $Node.PSObject.Properties['type'] -and $Node.PSObject.Properties['settings']) {
                $settings = $Node.settings
                if ($Node.type -eq 'ffmpeg_source') {
                    $script:sources += [pscustomobject]@{
                        Name = $Node.name
                        Id = $Node.id
                        File = $settings.local_file
                        Caching = $settings.caching
                        HardwareDecode = $settings.hw_decode
                    }
                }
            }
            if ($Node.PSObject) {
                foreach ($property in $Node.PSObject.Properties) {
                    if ($property.Name -ne 'settings') {
                        Walk-SceneNode $property.Value
                    }
                }
            }
        }
        Walk-SceneNode $json
        $script:sources |
            ForEach-Object {
                $item = if ($_.File) { Get-Item -LiteralPath $_.File -ErrorAction SilentlyContinue } else { $null }
                [pscustomobject]@{
                    Name = $_.Name
                    Exists = [bool]$item
                    MB = if ($item) { [math]::Round($item.Length / 1MB, 1) } else { $null }
                    Caching = $_.Caching
                    HardwareDecode = $_.HardwareDecode
                    File = $_.File
                }
            } |
            Sort-Object Exists, MB -Descending |
            Select-Object -First 20 |
            Format-Table -AutoSize |
            Out-String |
            Write-Output
    } catch {
        "Scene parse failed: $($_.Exception.Message)"
    }
} else {
    "No scene JSON found under $sceneDir"
}

Write-Section "Latest OBS Backend Warnings"
$obsLogDir = Join-Path $SlobsRoot "node-obs\logs"
$latestObsLog = Get-ChildItem -LiteralPath $obsLogDir -File -Filter "*.txt" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($latestObsLog) {
    "Latest OBS log: $($latestObsLog.FullName)"
    Select-String -Path $latestObsLog.FullName -Pattern 'Failed while trying to allocate|errno 12|audio is lagging|Max audio buffering|lookahead|b-frames|aq:|obs64|crash|nvenc|dropped|lagged' -CaseSensitive:$false |
        Select-Object -Last 80 |
        ForEach-Object { "$($_.LineNumber): $($_.Line.Trim())" }
} else {
    "No OBS backend log found under $obsLogDir"
}
