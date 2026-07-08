param(
    [int]$Top = 20
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

"# GPU Workflow Probe"
"Runtime: $(Get-Date -Format o)"
"Policy: read-only; never stops OBS, Chrome, browser tabs, or streaming tools."

Write-Section "NVIDIA Snapshot"
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    & nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw --format=csv
    ""
    "GPU processes reported by nvidia-smi:"
    & nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
} else {
    "nvidia-smi not found."
}

Write-Section "Protected Streaming / Browser Processes"
Get-Process -Name "obs64","Streamlabs OBS","chrome","msedgewebview2","dwm","zo","Antigravity","Codex","ChatGPT" -ErrorAction SilentlyContinue |
    Select-Object Id, ProcessName, @{Name='PrivateGB';Expression={Convert-BytesToGB $_.PrivateMemorySize64}}, @{Name='WorkingGB';Expression={Convert-BytesToGB $_.WorkingSet64}}, CPU, StartTime |
    Sort-Object ProcessName, Id |
    Format-Table -AutoSize |
    Out-String |
    Write-Output

Write-Section "Memory Commit"
$counter = Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit','\Memory\Available MBytes' -ErrorAction SilentlyContinue
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

Write-Section "Top Private Memory Processes"
Get-Process |
    Sort-Object PrivateMemorySize64 -Descending |
    Select-Object -First $Top Id, ProcessName, @{Name='PrivateGB';Expression={Convert-BytesToGB $_.PrivateMemorySize64}}, @{Name='WorkingGB';Expression={Convert-BytesToGB $_.WorkingSet64}}, CPU |
    Format-Table -AutoSize |
    Out-String |
    Write-Output

Write-Section "Windows Visual / GPU Scheduler Flags"
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\DWM' -ErrorAction SilentlyContinue |
    Select-Object EnableAeroPeek, ColorizationGlassAttribute |
    Format-List |
    Out-String |
    Write-Output
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' -ErrorAction SilentlyContinue |
    Select-Object EnableTransparency |
    Format-List |
    Out-String |
    Write-Output
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers' -ErrorAction SilentlyContinue |
    Select-Object HwSchMode |
    Format-List |
    Out-String |
    Write-Output

Write-Section "Protected Workload Gate"
$gate = Join-Path $PSScriptRoot "protected_workload_gate.py"
if (Test-Path -LiteralPath $gate) {
    python $gate
} else {
    "Missing protected_workload_gate.py"
}

Write-Section "Operator Guidance"
"If OBS or Chrome are listed above, do not use Stop-Process/taskkill as a GPU fix."
"Prefer manual OBS scene/encoder tuning, lower refresh-rate alignment, and pausing local model jobs while streaming."
