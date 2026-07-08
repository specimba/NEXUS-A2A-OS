# Start 1–2h zero-cost A2A browser experiment (background-friendly).
param(
    [int]$Port = 9224,
    [int]$DurationMin = 90,
    [int]$CycleMin = 12,
    [switch]$SendPings
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

$logRoot = "C:\Users\speci.000\Downloads\NEXUSlogs\a2a_experiment"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runnerLog = Join-Path $logRoot "runner_$stamp.log"

$nodeArgs = @(
    "$Repo\tools\browser_ai_supervisor\a2a_long_run_experiment.mjs",
    "--port", $Port,
    "--duration-min", $DurationMin,
    "--cycle-min", $CycleMin
)
if ($SendPings) { $nodeArgs += "--send" }

Write-Host "A2A experiment: ${DurationMin}min cycles=${CycleMin}min SendPings=$SendPings"
Write-Host "Runner log: $runnerLog"

$proc = Start-Process -FilePath "node" -ArgumentList $nodeArgs `
    -WorkingDirectory $Repo -RedirectStandardOutput $runnerLog -RedirectStandardError "$runnerLog.err" `
    -PassThru -WindowStyle Hidden

@{
    status = "A2A_EXPERIMENT_STARTED"
    pid = $proc.Id
    durationMin = $DurationMin
    cycleMin = $CycleMin
    sendPings = [bool]$SendPings
    runnerLog = $runnerLog
    tail = "Get-Content '$runnerLog' -Wait -Tail 20"
} | ConvertTo-Json