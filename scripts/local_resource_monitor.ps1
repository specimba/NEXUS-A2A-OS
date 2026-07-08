param(
    [int]$DurationMinutes = 20,
    [int]$IntervalSeconds = 2,
    [string]$OutputRoot = "logs/resource-monitor"
)

$ErrorActionPreference = "SilentlyContinue"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $repoRoot (Join-Path $OutputRoot $runId)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$samplesPath = Join-Path $outDir "samples.csv"
$procPath = Join-Path $outDir "process_top.csv"
$ollamaPath = Join-Path $outDir "ollama_churn.csv"
$tcpPath = Join-Path $outDir "tcp_connections.csv"
$eventsPath = Join-Path $outDir "events_after.jsonl"
$summaryPath = Join-Path $outDir "summary.json"
$metaPath = Join-Path $outDir "metadata.json"

$start = Get-Date
$end = $start.AddMinutes($DurationMinutes)
$ollamaAppLog = Join-Path $env:LOCALAPPDATA "Ollama/app.log"
$ollamaServerLog = Join-Path $env:LOCALAPPDATA "Ollama/server.log"
$startupLink = Join-Path $env:APPDATA "Microsoft/Windows/Start Menu/Programs/Startup/Ollama.lnk"
$totalPhysicalRamMb = 0.0
try {
    $computerInfo = Get-CimInstance Win32_ComputerSystem
    if ($computerInfo.TotalPhysicalMemory) {
        $totalPhysicalRamMb = [math]::Round($computerInfo.TotalPhysicalMemory / 1MB, 1)
    }
} catch {
    try {
        Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
        $computerInfo = [Microsoft.VisualBasic.Devices.ComputerInfo]::new()
        if ($computerInfo.TotalPhysicalMemory) {
            $totalPhysicalRamMb = [math]::Round($computerInfo.TotalPhysicalMemory / 1MB, 1)
        }
    } catch {
        $totalPhysicalRamMb = 0.0
    }
}

function Get-FileLength($path) {
    if (Test-Path $path) {
        return (Get-Item $path).Length
    }
    return 0
}

function Get-CounterValue($path) {
    try {
        return [double]((Get-Counter $path -MaxSamples 1).CounterSamples[0].CookedValue)
    } catch {
        return $null
    }
}

function Get-NetstatLines {
    try {
        return (netstat -ano | Select-String ":11435|:49152" | ForEach-Object { $_.Line })
    } catch {
        return @()
    }
}

function Get-NetworkTotalBps {
    try {
        $samples = (Get-Counter "\Network Interface(*)\Bytes Total/sec" -MaxSamples 1).CounterSamples |
            Where-Object { $_.InstanceName -notmatch "loopback|isatap|teredo|bluetooth" }
        return [double](($samples | Measure-Object -Property CookedValue -Sum).Sum)
    } catch {
        return $null
    }
}

$metadata = [ordered]@{
    run_id = $runId
    started_at = $start.ToString("o")
    duration_minutes = $DurationMinutes
    interval_seconds = $IntervalSeconds
    repo_root = $repoRoot.Path
    output_dir = $outDir
    ollama_host = [Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
    ollama_keep_alive = [Environment]::GetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "User")
    ollama_startup_link_exists = Test-Path $startupLink
    ollama_startup_link_disabled_exists = Test-Path "$startupLink.disabled"
    initial_app_log_len = Get-FileLength $ollamaAppLog
    initial_server_log_len = Get-FileLength $ollamaServerLog
    initial_netstat = @(Get-NetstatLines)
}
$metadata | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $metaPath

"timestamp,total_ram_mb,free_ram_mb,used_ram_pct,commit_pct,cpu_total_pct,disk_read_bps,disk_write_bps,disk_queue,network_total_bps,ollama_count,python_count,top_ws_pid,top_ws_name,top_ws_mb,top_cpu_pid,top_cpu_name,top_cpu_delta,app_log_delta,server_log_delta,netstat_49152_count,netstat_11435_count" | Set-Content -Encoding UTF8 $samplesPath
"timestamp,pid,name,ws_mb,private_mb,cpu_total,cpu_delta,path" | Set-Content -Encoding UTF8 $procPath
"timestamp,pid,name,ws_mb,cpu_total,start_time,path,command_line" | Set-Content -Encoding UTF8 $ollamaPath
"timestamp,pid,name,local_address,local_port,remote_address,remote_port,state" | Set-Content -Encoding UTF8 $tcpPath

$cpuPrev = @{}
$seenOllama = @{}
$lastAppLen = $metadata.initial_app_log_len
$lastServerLen = $metadata.initial_server_log_len
$sampleCount = 0
$spikeCount = 0
$highDiskQueueCount = 0
$ollamaChurnEvents = 0
$maxUsedRamPct = 0.0
$maxDiskQueue = 0.0
$maxWriteBps = 0.0
$maxReadBps = 0.0
$maxNetworkTotalBps = 0.0

while ((Get-Date) -lt $end) {
    $now = Get-Date
    $ts = $now.ToString("o")
    $totalRamMb = $totalPhysicalRamMb
    $availableRamMb = Get-CounterValue "\Memory\Available MBytes"
    if ($null -eq $availableRamMb) {
        try {
            Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
            $computerInfo = [Microsoft.VisualBasic.Devices.ComputerInfo]::new()
            $availableRamMb = [double]($computerInfo.AvailablePhysicalMemory / 1MB)
        } catch {
            $availableRamMb = $null
        }
    }
    $freeRamMb = if ($null -ne $availableRamMb) { [math]::Round($availableRamMb, 1) } else { 0 }
    $usedRamPct = if ($totalRamMb -gt 0) { [math]::Round((($totalRamMb - $freeRamMb) / $totalRamMb) * 100, 2) } else { 0 }
    $commitPct = Get-CounterValue "\Memory\% Committed Bytes In Use"
    $cpuTotalPct = Get-CounterValue "\Processor(_Total)\% Processor Time"
    $diskReadBps = Get-CounterValue "\PhysicalDisk(_Total)\Disk Read Bytes/sec"
    $diskWriteBps = Get-CounterValue "\PhysicalDisk(_Total)\Disk Write Bytes/sec"
    $diskQueue = Get-CounterValue "\PhysicalDisk(_Total)\Avg. Disk Queue Length"
    $networkTotalBps = Get-NetworkTotalBps

    $procs = Get-Process | Where-Object { $_.Id -ne $PID }
    $rows = foreach ($p in $procs) {
        $prev = if ($cpuPrev.ContainsKey($p.Id)) { $cpuPrev[$p.Id] } else { $p.CPU }
        $cpuDelta = if ($null -ne $p.CPU -and $null -ne $prev) { [math]::Round($p.CPU - $prev, 3) } else { 0 }
        $cpuPrev[$p.Id] = $p.CPU
        [pscustomobject]@{
            Id = $p.Id
            Name = $p.ProcessName
            WS = $p.WorkingSet64
            Private = $p.PrivateMemorySize64
            CPU = $p.CPU
            CpuDelta = $cpuDelta
            Path = $p.Path
        }
    }

    $topWs = $rows | Sort-Object WS -Descending | Select-Object -First 1
    $topCpu = $rows | Sort-Object CpuDelta -Descending | Select-Object -First 1
    $interest = $rows | Where-Object {
        $_.Name -match "ollama|python|streamlabs|obs|chrome|msedge|code|codex|node|powershell|pwsh|devenv|antigravity|gemini" -or
        $_.WS -gt 500MB -or
        $_.CpuDelta -gt 1
    } | Sort-Object WS -Descending | Select-Object -First 30

    foreach ($p in $interest) {
        '"{0}",{1},"{2}",{3},{4},{5},{6},"{7}"' -f $ts, $p.Id, $p.Name, [math]::Round($p.WS/1MB,1), [math]::Round($p.Private/1MB,1), $p.CPU, $p.CpuDelta, (($p.Path -replace '"','""')) | Add-Content -Encoding UTF8 $procPath
    }

    $interestingPids = @($interest | Where-Object {
        $_.Name -match "grok|ollama|python|streamlabs|obs|chrome|msedge|code|codex|node|powershell|pwsh|antigravity|zo|devin|opencode|kilo|gemini"
    } | Select-Object -ExpandProperty Id -Unique)
    if ($interestingPids.Count -gt 0) {
        $tcpRows = Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $interestingPids -contains $_.OwningProcess }
        foreach ($tcp in $tcpRows) {
            $procName = ($rows | Where-Object { $_.Id -eq $tcp.OwningProcess } | Select-Object -First 1).Name
            '"{0}",{1},"{2}","{3}",{4},"{5}",{6},"{7}"' -f $ts, $tcp.OwningProcess, $procName, $tcp.LocalAddress, $tcp.LocalPort, $tcp.RemoteAddress, $tcp.RemotePort, $tcp.State | Add-Content -Encoding UTF8 $tcpPath
        }
    }

    $ollamaProcs = @($rows | Where-Object { $_.Name -like "ollama*" })
    foreach ($op in $ollamaProcs) {
        $startTime = ""
        try {
            $liveProc = Get-Process -Id $op.Id
            if ($liveProc.StartTime) {
                $startTime = $liveProc.StartTime.ToString("o")
            }
        } catch {
            $startTime = ""
        }
        $key = "$($op.Id)-$startTime"
        if (-not $seenOllama.ContainsKey($key)) {
            $seenOllama[$key] = $true
            $ollamaChurnEvents++
        }
        '"{0}",{1},"{2}",{3},{4},"{5}","{6}","{7}"' -f $ts, $op.Id, $op.Name, [math]::Round($op.WS/1MB,1), $op.CPU, $startTime, (($op.Path -replace '"','""')), "" | Add-Content -Encoding UTF8 $ollamaPath
    }

    $appLen = Get-FileLength $ollamaAppLog
    $serverLen = Get-FileLength $ollamaServerLog
    $appDelta = $appLen - $lastAppLen
    $serverDelta = $serverLen - $lastServerLen
    $lastAppLen = $appLen
    $lastServerLen = $serverLen
    $netLines = @(Get-NetstatLines)
    $net49152 = @($netLines | Where-Object { $_ -match ":49152" }).Count
    $net11435 = @($netLines | Where-Object { $_ -match ":11435" }).Count

    $maxUsedRamPct = [math]::Max($maxUsedRamPct, $usedRamPct)
    if ($null -ne $diskQueue) { $maxDiskQueue = [math]::Max($maxDiskQueue, $diskQueue) }
    if ($null -ne $diskWriteBps) { $maxWriteBps = [math]::Max($maxWriteBps, $diskWriteBps) }
    if ($null -ne $diskReadBps) { $maxReadBps = [math]::Max($maxReadBps, $diskReadBps) }
    if ($null -ne $networkTotalBps) { $maxNetworkTotalBps = [math]::Max($maxNetworkTotalBps, $networkTotalBps) }
    if ($usedRamPct -ge 90 -or ($diskQueue -ne $null -and $diskQueue -ge 2) -or $appDelta -gt 0 -or $serverDelta -gt 0 -or $net49152 -gt 0) {
        $spikeCount++
    }
    if ($diskQueue -ne $null -and $diskQueue -ge 2) {
        $highDiskQueueCount++
    }

    '"{0}",{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},"{13}",{14},{15},"{16}",{17},{18},{19},{20},{21}' -f $ts,$totalRamMb,$freeRamMb,$usedRamPct,$commitPct,$cpuTotalPct,$diskReadBps,$diskWriteBps,$diskQueue,$networkTotalBps,@($ollamaProcs).Count,@($procs | Where-Object ProcessName -like "python*").Count,$topWs.Id,$topWs.Name,[math]::Round($topWs.WS/1MB,1),$topCpu.Id,$topCpu.Name,$topCpu.CpuDelta,$appDelta,$serverDelta,$net49152,$net11435 | Add-Content -Encoding UTF8 $samplesPath

    $sampleCount++
    Start-Sleep -Seconds $IntervalSeconds
}

$eventStart = $start.AddMinutes(-2)
$events = Get-WinEvent -FilterHashtable @{LogName=@("System","Application"); StartTime=$eventStart} |
    Where-Object { $_.ProviderName -match "Display|nvlddmkm|WHEA|Kernel-Power|Application Error|Windows Error Reporting|Disk|stornvme|storahci|Ntfs|Resource-Exhaustion|Audio" -or $_.LevelDisplayName -in @("Critical","Error","Warning") } |
    Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,Message
foreach ($e in $events) {
    $e | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 $eventsPath
}

$summary = [ordered]@{
    run_id = $runId
    started_at = $start.ToString("o")
    ended_at = (Get-Date).ToString("o")
    samples = $sampleCount
    spike_samples = $spikeCount
    high_disk_queue_samples = $highDiskQueueCount
    max_used_ram_pct = [math]::Round($maxUsedRamPct, 2)
    max_disk_queue = [math]::Round($maxDiskQueue, 3)
    max_disk_write_mb_s = [math]::Round($maxWriteBps / 1MB, 2)
    max_disk_read_mb_s = [math]::Round($maxReadBps / 1MB, 2)
    max_network_total_mbps = [math]::Round(($maxNetworkTotalBps * 8) / 1MB, 2)
    ollama_unique_process_starts = $seenOllama.Count
    output_dir = $outDir
    files = @{
        samples = $samplesPath
        process_top = $procPath
        ollama_churn = $ollamaPath
        tcp_connections = $tcpPath
        events = $eventsPath
        metadata = $metaPath
    }
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $summaryPath
Write-Output ($summary | ConvertTo-Json -Depth 6)
