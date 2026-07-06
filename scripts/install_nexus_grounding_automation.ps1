param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$groundingTask = 'NexusGroundingSupervisor'
$browserTask = 'NexusBrowserAISupervisor'
$python = (Get-Command python.exe).Source
$wscript = Join-Path $env:SystemRoot 'System32\wscript.exe'
$groundingScript = Join-Path $RepoRoot 'tools\grounding\run_grounding_supervisor.py'
$browserLauncher = Join-Path $RepoRoot 'tools\browser_ai_supervisor\run_browser_ai_supervisor_hidden.vbs'
$groundingRoot = Join-Path $env:LOCALAPPDATA 'NEXUS\grounding'

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650)

$groundingAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$groundingScript`" --root `"$groundingRoot`" --poll-seconds 30 --reconcile-seconds 3600" `
    -WorkingDirectory $RepoRoot
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask `
    -TaskName $groundingTask `
    -Action $groundingAction `
    -Trigger $logon `
    -Settings $settings `
    -Description 'NEXUS incremental evidence grounding supervisor' `
    -Force | Out-Null

$browserAction = New-ScheduledTaskAction `
    -Execute $wscript `
    -Argument "`"$browserLauncher`""
$browserLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$browserRecurring = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask `
    -TaskName $browserTask `
    -Action $browserAction `
    -Trigger @($browserLogon, $browserRecurring) `
    -Settings $settings `
    -Description 'NEXUS isolated Grok CDP and Browser-AI supervisor' `
    -Force | Out-Null

Get-ScheduledTask -TaskName $groundingTask, $browserTask |
    Select-Object TaskName, State
