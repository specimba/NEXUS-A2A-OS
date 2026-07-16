<#
.SYNOPSIS
    NEXUS CDP lane window watchdog - keeps multi-lane Chrome visible.
.DESCRIPTION
    Uses the proven show-only pattern from Grok automation:
    - Does NOT kill chrome, restart CDP, reset Preferences, or open/close tabs
    - Only fixes when window is actually broken (offscreen, tiny, minimized)
    - Safe to run during A800 training
.PARAMETER IntervalSeconds
    Seconds between checks. Default: 60.
.PARAMETER Port
    CDP port. Default: 9224.
.PARAMETER LogPath
    Log file path.
.EXAMPLE
    Start-Job { & "C:\Users\speci.000\Documents\NEXUS\scripts\watch_lane_stack.ps1" }
#>

param(
    [int]$IntervalSeconds = 60,
    [int]$Port = 9224,
    [string]$LogPath = (Join-Path $PSScriptRoot "watch_lane_stack.log")
)

$ErrorActionPreference = "SilentlyContinue"
$repo = "C:\Users\speci.000\Documents\NEXUS"
$showScript = "C:\Users\speci.000\Downloads\cdp_agent_scratch\intern_cdp\_show_cdp_chrome.ps1"

# Single-instance file lock
$lockFile = "C:\Users\speci.000\Downloads\NEXUSlogs\watch_lane_stack.lock"
try {
    $lockDir = Split-Path $lockFile
    if (-not (Test-Path $lockDir)) { New-Item -ItemType Directory -Force -Path $lockDir | Out-Null }
    $lockStream = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
} catch {
    Write-Output "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [WARN] watch_lane_stack is already running (failed to acquire lock). Exiting."
    exit 0
}

if (-not (Test-Path $showScript)) {
    Write-Output "ERROR: show script not found at $showScript"
    exit 1
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[" + $ts + "] [" + $Level + "] " + $Message
    Write-Output $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

Write-Log ("=== Lane Watchdog Started (interval=" + $IntervalSeconds + "s, port=" + $Port + ") ===") "START"

$fixCount = 0
$checkCount = 0

while ($true) {
    try {
        $checkCount++
        $output = & $showScript -Port $Port 2>&1
        $joined = ($output | Out-String)

        if ($joined -match "STATUS=SHOWN") {
            $fixCount++
            Write-Log ("CHECK #" + $checkCount + ": window was broken, restored (fix #" + $fixCount + ")") "FIX"
        }
        elseif ($joined -match "STATUS=ALREADY_VISIBLE") {
            if ($checkCount % 10 -eq 0) {
                Write-Log ("CHECK #" + $checkCount + ": window OK (fixes so far: " + $fixCount + ")") "HEARTBEAT"
            }
        }
        elseif ($joined -match "CDP_DOWN") {
            Write-Log ("CHECK #" + $checkCount + ": CDP port " + $Port + " is DOWN") "ERROR"
        }
        elseif ($joined -match "NO_HWND") {
            Write-Log ("CHECK #" + $checkCount + ": no Chrome window found") "WARN"
        }
    }
    catch {
        Write-Log ("Loop error: " + $_.Exception.Message) "ERROR"
    }

    Start-Sleep -Seconds $IntervalSeconds
}
