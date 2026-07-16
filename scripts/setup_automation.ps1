<#
.SYNOPSIS
    NEXUS full-automation ONE-TIME setup.
.DESCRIPTION
    Registers Windows Scheduled Tasks so the operator never needs to type
    console commands again. After running this once, everything runs on schedule:
    
    - A800 training monitor (every 30 min)
    - Chrome lane window watchdog (runs at login, persistent)
    - Daily preflight health report (7:00 AM every day)
    - Weekly guard stress test (every Monday 9:00 AM)

    Requires: Run as Administrator (for ScheduledTask registration).
.EXAMPLE
    # Right-click PowerShell → Run as Administrator, then:
    cd C:\Users\speci.000\Documents\NEXUS
    .\scripts\setup_automation.ps1
    
    # After setup, reboot or log out/in to start the watchdog.
    # Verify with: Get-ScheduledTask | Where-Object TaskName -like "NEXUS_*"
#>

param(
    [string]$Repo = "C:\Users\speci.000\Documents\NEXUS",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Error "Run as Administrator: right-click PowerShell → Run as Administrator"
}

$ps = "powershell.exe"
$tasks = @()

# --- Task 1: A800 Training Monitor (every 30 min) ---
$action1 = New-ScheduledTaskAction -Execute $ps -Argument @"
-NoProfile -WindowStyle Hidden -Command "Set-Location '$Repo'; & '.\scripts\monitor\a800_lightweight_monitor.ps1' -LogPath 'C:\Users\speci.000\Downloads\NEXUSlogs\a800_monitor_scheduled.log'"
"@
$trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 24)
$tasks += @{ Name = "NEXUS_A800Monitor"; Action = $action1; Trigger = $trigger1; Settings = $settings1; Desc = "A800 training tick monitor — every 30 min, no AI context burn." }

# --- Task 2: Lane Window Watchdog (at login, persistent) ---
$action2 = New-ScheduledTaskAction -Execute $ps -Argument @"
-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Set-Location '$Repo'; & '.\scripts\watch_lane_stack.ps1' -IntervalSeconds 15 -Port 9224 -LogPath 'C:\Users\speci.000\Downloads\NEXUSlogs\lane_watch.log'"
"@
$trigger2 = New-ScheduledTaskTrigger -AtLogOn
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
$settings2.ExecutionTimeLimit = [TimeSpan]::Zero  # Run forever
$tasks += @{ Name = "NEXUS_LaneWatchdog"; Action = $action2; Trigger = $trigger2; Settings = $settings2; Desc = "Chrome lane window watchdog — auto-restore minimized CDP Chrome." }

# --- Task 3: Daily Preflight Health Report ---
$action3 = New-ScheduledTaskAction -Execute $ps -Argument @"
-NoProfile -WindowStyle Hidden -Command "Set-Location '$Repo'; $ts=Get-Date -Format 'yyyyMMdd'; & '.\scripts\preflight_health_check.ps1' -LogPath 'C:\Users\speci.000\Downloads\NEXUSlogs\preflight_$ts.log'"
"@
$trigger3 = New-ScheduledTaskTrigger -Daily -At "07:00AM"
$settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$tasks += @{ Name = "NEXUS_Preflight"; Action = $action3; Trigger = $trigger3; Settings = $settings3; Desc = "Daily preflight: ports, guard stack, relay, calm loop health." }

# --- Task 4: Weekly Guard Stress Test ---
$action4 = New-ScheduledTaskAction -Execute $ps -Argument @"
-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Set-Location '$Repo'; $ts=Get-Date -Format 'yyyyMMddTHHmmss'; python '.\scripts\stress\nexus_guard_stress_test.py' --mode full --limit 500 --output '.\reports\stress\$ts\_stress_report.json'"
"@
$trigger4 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "09:00AM"
$settings4 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$tasks += @{ Name = "NEXUS_GuardStress"; Action = $action4; Trigger = $trigger4; Settings = $settings4; Desc = "Weekly full guard stress test against adversarial corpus." }

# --- Create preflight helper if missing ---
$preflightPath = Join-Path $Repo "scripts\preflight_health_check.ps1"
if (-not (Test-Path $preflightPath) -or $Force) {
    $preflight = @'
param([string]$LogPath = "C:\Users\speci.000\Downloads\NEXUSlogs\preflight_$(Get-Date -Format 'yyyyMMdd').log")
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
function Write-Log { param([string]$M) $l="$(Get-Date -Format 'HH:mm:ss') $M"; Write-Output $l; Add-Content $LogPath $l }
Write-Log "=== NEXUS Preflight Health Check ==="
# Port check
foreach ($p in 7350,7352,7354,7355,7356,7357,9224) {
    try { $r=Invoke-WebRequest -Uri "http://127.0.0.1:$p/health" -TimeoutSec 3 -UseBasicParsing; Write-Log "port $p : OK" } catch { Write-Log "port $p : FAIL ($($_.Exception.Message))" }
}
# GitHub tick check
try {
    $t=(gh auth token).Trim()
    $j=Invoke-RestMethod -Uri "https://api.github.com/repos/specimba/NEXUS_discovery_GPU/contents/reports/session4/a800/LATEST.json" -Headers @{"Authorization"="Bearer $t";"Accept"="application/vnd.github.raw";"User-Agent"="neflight"}
    Write-Log "A800: tick=$($j.tick) stamp=$($j.stamp) mode=$($j.mode)"
} catch { Write-Log "A800 check: FAIL ($($_.Exception.Message))" }
# Calm process check
$calm=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "_a800_calm" }).Count
Write-Log "calm processes: $calm"
Write-Log "=== Preflight Complete ==="
'@
    Set-Content $preflightPath $preflight -Encoding UTF8
    Write-Host "CREATED: $preflightPath"
}

# --- Register / update each task ---
foreach ($t in $tasks) {
    $existing = Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
    if ($existing -and -not $Force) {
        Write-Host "EXISTS (skip - use -Force to overwrite): $($t.Name)"
        continue
    }
    if ($existing) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
    }
    try {
        Register-ScheduledTask -TaskName $t.Name -Action $t.Action -Trigger $t.Trigger -Settings $t.Settings -Description $t.Desc -RunLevel Highest -Force | Out-Null
        Write-Host "REGISTERED: $($t.Name) — $($t.Desc)"
    }
    catch {
        Write-Host "FAILED $($t.Name): $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- Summary ---
Write-Host ""
Write-Host "=== NEXUS Automation Setup Complete ==="
Write-Host ""
Write-Host "Scheduled Tasks:"
Get-ScheduledTask | Where-Object TaskName -like "NEXUS_*" | ForEach-Object {
    $state = $_.State
    Write-Host "  - $($_.TaskName): $state"
}
Write-Host ""
Write-Host "To verify running tasks:"
Write-Host "  Get-ScheduledTask | Where-Object TaskName -like 'NEXUS_*' | Format-Table TaskName,State,Description"
Write-Host ""
Write-Host "To start the watchdog immediately (no reboot needed):"
Write-Host "  Start-ScheduledTask -TaskName 'NEXUS_LaneWatchdog'"
Write-Host ""
Write-Host "To view any log:"
Write-Host "  notepad C:\Users\speci.000\Downloads\NEXUSlogs\a800_monitor_scheduled.log"
Write-Host "  notepad C:\Users\speci.000\Downloads\NEXUSlogs\lane_watch.log"
