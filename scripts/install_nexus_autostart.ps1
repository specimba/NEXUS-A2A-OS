# Registers a Windows Scheduled Task that auto-revives all NEXUS relay/dashboard
# services at user logon (and every 10 min) - so a PC restart no longer leaves the
# ModelRelay routing system dead, which previously broke Hermes/cli model sync.
#
# Task: "NexusServiceAutoRevive"  Trigger: AtLogon + 15-min repetition
# Action: wscript //B scripts\revive_relay_silent.vbs   (ZERO console window)
#
# uninstall:  Unregister-ScheduledTask -TaskName NexusServiceAutoRevive -Confirm:$false
#
# NOTE: calls the *ScheduledTask cmdlets DIRECTLY (no nested powershell -Command) so
# there is no quoting fragility and no interactive "Action[0]:" prompt.
param(
    [string]$NexusRoot = "C:\Users\speci.000\Documents\NEXUS"
)

$ReviveScript = Join-Path $NexusRoot "scripts\revive_relay_ports.ps1"
if (-not (Test-Path $ReviveScript)) { throw "revive_relay_ports.ps1 not found at $ReviveScript" }

# Silent launcher: WScript has no console, and the powershell it spawns runs
# -WindowStyle Hidden => ZERO visible window. This is why the scheduled task
# never flashes a console during its periodic runs.
$VbsLauncher = Join-Path $NexusRoot "scripts\revive_relay_silent.vbs"
if (-not (Test-Path $VbsLauncher)) { throw "revive_relay_silent.vbs not found at $VbsLauncher" }
$WScript = "$env:WINDIR\System32\wscript.exe"

$TaskName = 'NexusServiceAutoRevive'

# remove a prior registration so -Force semantics hold
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Where-Object { $_.State -ne $null } |
    ForEach-Object { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue }

# Action = wscript + silent VBS launcher (no console window ever)
$action = New-ScheduledTaskAction -Execute $WScript -Argument "//B `"$VbsLauncher`""

$trigLogon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"

# repetition trigger: starts now, repeats every 15 min for 365 days (silent via VBS)
$repDur = New-TimeSpan -Days 365
$repInt = New-TimeSpan -Minutes 15
$trigRecur = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval $repInt -RepetitionDuration $repDur

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName `
    -Action $action -Trigger @($trigLogon, $trigRecur) `
    -Settings $settings -Principal $principal `
    -Description 'Auto-revive NEXUS ModelRelay/dashboard/GodMode after restart' -Force | Out-Null

Write-Host "Registered '$TaskName'."
Write-Host "Verify:  Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
Write-Host "Run now: Start-ScheduledTask -TaskName $TaskName"
Write-Host "Remove:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
exit 0
