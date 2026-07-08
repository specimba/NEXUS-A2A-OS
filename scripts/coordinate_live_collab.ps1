# Live collab: stop rogue pings, lock Grok/GPT/Zo, run observe-only telemetry.
param([int]$Port = 9224, [int]$StopProcessId = 0)

$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

& "$Repo\scripts\stop_a2a_experiment.ps1" -TargetProcessId $StopProcessId | Out-Null
& "$Repo\scripts\collab_lane_lock.ps1" -Mode on -Note "operator live tri-lane; Hermes coordinates read-only"

$statusDir = "C:\Users\speci.000\Downloads\NEXUSlogs\a2a_experiment"
New-Item -ItemType Directory -Force -Path $statusDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$snap = Join-Path $statusDir "collab_snapshot_$stamp.json"

$lanes = @("grok", "zo", "chatgpt_gpt55")
$rows = @()
foreach ($lane in $lanes) {
    $raw = node "$Repo\tools\browser_ai_supervisor\lane_registry_probe.mjs" --port $Port --lane $lane 2>&1 | Out-String
    try { $rows += ($raw | ConvertFrom-Json) } catch { $rows += @{ lane = $lane; parseError = $true; raw = $raw.Substring(0, [Math]::Min(500, $raw.Length)) } }
}
@{ snapshotAt = (Get-Date).ToUniversalTime().ToString("o"); lanes = $rows } | ConvertTo-Json -Depth 8 | Set-Content $snap -Encoding UTF8

& "$Repo\scripts\start_a2a_long_run_experiment.ps1" -Port $Port -DurationMin 120 -CycleMin 15

@{
    status = "LIVE_COLLAB_COORDINATED"
    collabLock = "on"
    stoppedProcessId = $StopProcessId
    snapshot = $snap
    mode = "observe_only_no_cdp_send_to_grok_gpt_zo"
} | ConvertTo-Json