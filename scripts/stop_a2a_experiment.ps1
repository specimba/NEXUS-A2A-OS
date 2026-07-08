# Stop background A2A long-run experiment (node a2a_long_run_experiment.mjs).
# Note: do not use param name Pid — conflicts with PowerShell automatic $PID.
param([int]$TargetProcessId = 0)

$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {
    $_.CommandLine -match "a2a_long_run_experiment\.mjs"
}
if ($TargetProcessId -gt 0) {
    $procs = $procs | Where-Object { $_.ProcessId -eq $TargetProcessId }
}
$ids = @($procs | Select-Object -ExpandProperty ProcessId -Unique)
foreach ($id in $ids) {
    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
}
@{
    status = "A2A_EXPERIMENT_STOPPED"
    pids = $ids
} | ConvertTo-Json